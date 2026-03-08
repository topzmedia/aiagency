"""
Avatar video provider adapter.
Supports HeyGen, Tavus, D-ID, and a Mock provider.
All providers generate lip-synced talking-actor videos.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.enums import AvatarProvider, RenderStatus
from ..models.schemas import AvatarMetadata, TalkingActorJob
from ..utils.config import AvatarProviderConfig
from ..utils.io import download_file, get_file_size
from ..utils.logging_utils import log_provider_call, log_provider_response
from ..utils.rate_limits import get_limiter
from ..utils.retries import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    TransientError,
    poll_until_complete,
)

logger = logging.getLogger("ai_ad_agency.providers.avatar")


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseAvatarProvider(ABC):
    """All avatar providers must implement this interface."""

    @abstractmethod
    def list_avatars(self) -> List[Dict[str, Any]]:
        """Fetch available avatars from the provider. Returns raw provider dicts."""

    @abstractmethod
    def submit_render(self, job: TalkingActorJob) -> str:
        """
        Submit a talking-actor render job.
        Returns a provider-specific job ID.
        """

    @abstractmethod
    def get_render_status(self, provider_job_id: str) -> Dict[str, Any]:
        """
        Poll render status.
        Returns dict with at minimum: status (str), download_url (optional str).
        """

    @abstractmethod
    def is_render_done(self, status_response: Dict[str, Any]) -> bool:
        """Return True when render is complete and download URL is available."""

    @abstractmethod
    def is_render_failed(self, status_response: Dict[str, Any]) -> bool:
        """Return True when render has permanently failed."""

    @abstractmethod
    def extract_download_url(self, status_response: Dict[str, Any]) -> Optional[str]:
        """Extract the video download URL from a completed status response."""

    def render_and_download(
        self,
        job: TalkingActorJob,
        output_dir: str,
        poll_interval: int = 10,
        max_polls: int = 60,
    ) -> TalkingActorJob:
        """
        End-to-end: submit → poll → download.
        Updates the job object in place and returns it.
        """
        # Submit
        logger.info(
            "Submitting avatar render: avatar=%s script_len=%d",
            job.avatar_id,
            len(job.voice_safe_text),
        )
        provider_job_id = self.submit_render(job)
        job.provider_job_id = provider_job_id
        job.render_status = RenderStatus.PROCESSING
        job.attempts += 1

        # Poll
        try:
            final_status = poll_until_complete(
                poll_fn=lambda: self.get_render_status(provider_job_id),
                is_done_fn=self.is_render_done,
                is_failed_fn=self.is_render_failed,
                interval_sec=poll_interval,
                max_attempts=max_polls,
                label=f"avatar_render:{provider_job_id}",
            )
        except ProviderTimeoutError as e:
            job.render_status = RenderStatus.TIMEOUT
            job.error_message = str(e)
            logger.error("Render timeout: %s", e)
            return job

        # Extract URL and download
        download_url = self.extract_download_url(final_status)
        if not download_url:
            job.render_status = RenderStatus.FAILED
            job.error_message = "No download URL in completed status"
            return job

        output_path = Path(output_dir) / f"avatar_{job.job_id}.mp4"
        try:
            download_file(download_url, output_path)
            job.file_path = str(output_path)
            job.file_size_bytes = get_file_size(output_path)
            job.render_status = RenderStatus.COMPLETED

            from ..utils.ffmpeg_utils import get_duration, get_dimensions
            duration = get_duration(output_path)
            if duration:
                job.duration_sec = duration
            dims = get_dimensions(output_path)
            if dims:
                job.width, job.height = dims

            from datetime import datetime
            job.completed_at = datetime.utcnow()
            logger.info(
                "Avatar render complete: %s (%.1fs, %.1f KB)",
                output_path.name,
                job.duration_sec or 0,
                job.file_size_bytes / 1024,
            )
        except Exception as e:
            job.render_status = RenderStatus.FAILED
            job.error_message = f"Download failed: {e}"
            logger.error("Download failed for job %s: %s", provider_job_id, e)

        return job


# ---------------------------------------------------------------------------
# HeyGen provider
# ---------------------------------------------------------------------------

class HeyGenProvider(BaseAvatarProvider):
    """
    HeyGen v2 API adapter.
    Docs: https://docs.heygen.com/reference/
    """

    BASE_URL = "https://api.heygen.com"

    def __init__(self, config: AvatarProviderConfig):
        self.config = config
        self._limiter = get_limiter("heygen", config.requests_per_minute)

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Api-Key": self.config.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str) -> Dict[str, Any]:
        import urllib.request
        import json
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        log_provider_call(logger, "heygen", path, "GET")
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                log_provider_response(logger, "heygen", path, resp.status)
                return data
        except Exception as e:
            self._handle_error(e, path)
            raise

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.request
        import json as jsonlib
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        body = jsonlib.dumps(payload).encode("utf-8")
        log_provider_call(logger, "heygen", path, str(payload)[:200])
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = jsonlib.loads(resp.read())
                log_provider_response(logger, "heygen", path, resp.status)
                return data
        except Exception as e:
            self._handle_error(e, path)
            raise

    def _handle_error(self, e: Exception, path: str) -> None:
        err = str(e).lower()
        if "429" in err or "rate" in err:
            raise ProviderRateLimitError(f"HeyGen rate limit on {path}: {e}")
        if "timeout" in err:
            raise ProviderTimeoutError(f"HeyGen timeout on {path}: {e}")
        if any(x in err for x in ["502", "503", "connection"]):
            raise TransientError(f"HeyGen transient error on {path}: {e}")

    def list_avatars(self) -> List[Dict[str, Any]]:
        try:
            resp = self._get("/v2/avatars")
            return resp.get("data", {}).get("avatars", [])
        except Exception as e:
            logger.error("HeyGen list_avatars failed: %s", e)
            return []

    def submit_render(self, job: TalkingActorJob) -> str:
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": job.avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "text",
                        "input_text": job.voice_safe_text,
                        "voice_id": job.voice_id or "",
                    },
                }
            ],
            "dimension": {
                "width": job.width,
                "height": job.height,
            },
            "aspect_ratio": None,
        }
        resp = self._post("/v2/video/generate", payload)
        video_id = resp.get("data", {}).get("video_id")
        if not video_id:
            raise ValueError(f"HeyGen submit_render: no video_id in response: {resp}")
        return video_id

    def get_render_status(self, provider_job_id: str) -> Dict[str, Any]:
        try:
            return self._get(f"/v1/video_status.get?video_id={provider_job_id}")
        except Exception as e:
            logger.warning("HeyGen status poll error: %s", e)
            return {"data": {"status": "processing"}}

    def is_render_done(self, status_response: Dict[str, Any]) -> bool:
        status = status_response.get("data", {}).get("status", "")
        return status == "completed"

    def is_render_failed(self, status_response: Dict[str, Any]) -> bool:
        status = status_response.get("data", {}).get("status", "")
        return status in ("failed", "error")

    def extract_download_url(self, status_response: Dict[str, Any]) -> Optional[str]:
        return status_response.get("data", {}).get("video_url")


# ---------------------------------------------------------------------------
# Tavus provider
# ---------------------------------------------------------------------------

class TavusProvider(BaseAvatarProvider):
    """
    Tavus API adapter.
    Docs: https://docs.tavus.io/
    """

    BASE_URL = "https://tavusapi.com"

    def __init__(self, config: AvatarProviderConfig):
        self.config = config
        self._limiter = get_limiter("tavus", config.requests_per_minute)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        import urllib.request
        import json as jsonlib
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        body = jsonlib.dumps(payload).encode("utf-8") if payload else None
        log_provider_call(logger, "tavus", path, str(payload or {})[:200])
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = jsonlib.loads(resp.read())
                log_provider_response(logger, "tavus", path, resp.status)
                return data
        except Exception as e:
            err = str(e).lower()
            if "429" in err:
                raise ProviderRateLimitError(f"Tavus rate limit: {e}")
            if "timeout" in err:
                raise ProviderTimeoutError(f"Tavus timeout: {e}")
            raise TransientError(f"Tavus error: {e}") from e

    def list_avatars(self) -> List[Dict[str, Any]]:
        try:
            resp = self._request("GET", "/v2/replicas")
            return resp.get("data", [])
        except Exception as e:
            logger.error("Tavus list_avatars failed: %s", e)
            return []

    def submit_render(self, job: TalkingActorJob) -> str:
        payload = {
            "replica_id": job.avatar_id,
            "script": job.voice_safe_text,
            "video_name": f"ad_{job.job_id}",
        }
        resp = self._request("POST", "/v2/videos", payload)
        video_id = resp.get("video_id") or resp.get("data", {}).get("video_id")
        if not video_id:
            raise ValueError(f"Tavus submit_render: no video_id. Response: {resp}")
        return video_id

    def get_render_status(self, provider_job_id: str) -> Dict[str, Any]:
        try:
            return self._request("GET", f"/v2/videos/{provider_job_id}")
        except Exception as e:
            logger.warning("Tavus status poll error: %s", e)
            return {"status": "queued"}

    def is_render_done(self, status_response: Dict[str, Any]) -> bool:
        return status_response.get("status") == "ready"

    def is_render_failed(self, status_response: Dict[str, Any]) -> bool:
        return status_response.get("status") in ("error", "failed")

    def extract_download_url(self, status_response: Dict[str, Any]) -> Optional[str]:
        return status_response.get("download_url") or status_response.get("stream_url")


# ---------------------------------------------------------------------------
# D-ID provider
# ---------------------------------------------------------------------------

class DIDProvider(BaseAvatarProvider):
    """
    D-ID API adapter (talks/presenters).
    Docs: https://docs.d-id.com/
    """

    BASE_URL = "https://api.d-id.com"

    def __init__(self, config: AvatarProviderConfig):
        self.config = config
        self._limiter = get_limiter("did", config.requests_per_minute)

    def _headers(self) -> Dict[str, str]:
        import base64
        auth = base64.b64encode(f"{self.config.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        import urllib.request
        import json as jsonlib
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        body = jsonlib.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = jsonlib.loads(resp.read())
                return data
        except Exception as e:
            raise TransientError(f"D-ID error: {e}") from e

    def list_avatars(self) -> List[Dict[str, Any]]:
        """D-ID uses pre-set presenter images; return empty list and use catalog."""
        return []

    def submit_render(self, job: TalkingActorJob) -> str:
        payload = {
            "source_url": job.avatar_id,  # D-ID uses image URL as avatar
            "script": {
                "type": "text",
                "input": job.voice_safe_text,
                "provider": {
                    "type": "microsoft",
                    "voice_id": job.voice_id or "en-US-JennyNeural",
                },
            },
            "config": {"fluent": True},
        }
        resp = self._request("POST", "/talks", payload)
        talk_id = resp.get("id")
        if not talk_id:
            raise ValueError(f"D-ID no talk id in response: {resp}")
        return talk_id

    def get_render_status(self, provider_job_id: str) -> Dict[str, Any]:
        try:
            return self._request("GET", f"/talks/{provider_job_id}")
        except Exception:
            return {"status": "started"}

    def is_render_done(self, status_response: Dict[str, Any]) -> bool:
        return status_response.get("status") == "done"

    def is_render_failed(self, status_response: Dict[str, Any]) -> bool:
        return status_response.get("status") in ("error", "failed")

    def extract_download_url(self, status_response: Dict[str, Any]) -> Optional[str]:
        return status_response.get("result_url")


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

class MockAvatarProvider(BaseAvatarProvider):
    """Mock provider for testing. Creates placeholder video files."""

    _MOCK_AVATARS = [
        {"avatar_id": f"mock_avatar_{i:03d}", "avatar_name": f"MockAvatar_{i:03d}"}
        for i in range(1, 61)
    ]

    def list_avatars(self) -> List[Dict[str, Any]]:
        logger.debug("[MOCK AVATAR] list_avatars() → %d avatars", len(self._MOCK_AVATARS))
        return self._MOCK_AVATARS

    def submit_render(self, job: TalkingActorJob) -> str:
        job_id = f"mock_job_{job.job_id[:8]}"
        logger.debug("[MOCK AVATAR] submit_render() → %s", job_id)
        return job_id

    def get_render_status(self, provider_job_id: str) -> Dict[str, Any]:
        return {"status": "completed", "download_url": f"mock://{provider_job_id}"}

    def is_render_done(self, status_response: Dict[str, Any]) -> bool:
        return status_response.get("status") == "completed"

    def is_render_failed(self, status_response: Dict[str, Any]) -> bool:
        return False

    def extract_download_url(self, status_response: Dict[str, Any]) -> Optional[str]:
        return status_response.get("download_url")

    def render_and_download(
        self,
        job: TalkingActorJob,
        output_dir: str,
        poll_interval: int = 10,
        max_polls: int = 60,
    ) -> TalkingActorJob:
        """Mock: create a tiny placeholder video file using FFmpeg."""
        from datetime import datetime
        from ..utils.ffmpeg_utils import create_text_card, check_ffmpeg

        output_path = Path(output_dir) / f"avatar_{job.job_id}.mp4"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        job.provider_job_id = self.submit_render(job)
        job.render_status = RenderStatus.PROCESSING
        job.attempts += 1

        # Create a text card as placeholder
        if check_ffmpeg():
            preview_text = job.voice_safe_text[:60] + "..." if len(job.voice_safe_text) > 60 else job.voice_safe_text
            success = create_text_card(
                text=preview_text,
                output_path=str(output_path),
                width=job.width,
                height=job.height,
                duration_sec=min(5.0, job.duration_sec or 5.0),
                bg_color="#1a1a2e",
                font_color="white",
                font_size=36,
            )
        else:
            # No FFmpeg: create empty file as placeholder
            output_path.touch()
            success = True

        if success or output_path.exists():
            job.file_path = str(output_path)
            job.file_size_bytes = get_file_size(output_path)
            job.render_status = RenderStatus.COMPLETED
            job.duration_sec = 5.0
            job.width = job.width
            job.height = job.height
            job.completed_at = datetime.utcnow()
            logger.debug("[MOCK AVATAR] Created placeholder: %s", output_path.name)
        else:
            job.render_status = RenderStatus.FAILED
            job.error_message = "Mock render failed (FFmpeg error)"

        return job


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_avatar_provider(config: AvatarProviderConfig) -> BaseAvatarProvider:
    if config.provider == AvatarProvider.HEYGEN:
        if not config.api_key:
            logger.warning("No HeyGen API key — using MockAvatarProvider")
            return MockAvatarProvider()
        return HeyGenProvider(config)
    elif config.provider == AvatarProvider.TAVUS:
        if not config.api_key:
            logger.warning("No Tavus API key — using MockAvatarProvider")
            return MockAvatarProvider()
        return TavusProvider(config)
    elif config.provider == AvatarProvider.DID:
        if not config.api_key:
            logger.warning("No D-ID API key — using MockAvatarProvider")
            return MockAvatarProvider()
        return DIDProvider(config)
    elif config.provider == AvatarProvider.MOCK:
        return MockAvatarProvider()
    else:
        logger.warning("Unknown avatar provider %s — using MockAvatarProvider", config.provider)
        return MockAvatarProvider()
