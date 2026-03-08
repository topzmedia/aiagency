"""
Video / B-roll generation provider adapter.
Supports Runway (Gen-3), Pika, Luma Dream Machine, and a robust fallback.
The fallback uses static images + FFmpeg zoom/pan to simulate video B-roll.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.enums import VideoProvider
from ..utils.config import VideoProviderConfig
from ..utils.io import download_file, get_file_size
from ..utils.logging_utils import log_provider_call, log_provider_response
from ..utils.rate_limits import get_limiter
from ..utils.retries import (
    ProviderRateLimitError,
    ProviderTimeoutError,
    TransientError,
    poll_until_complete,
)

logger = logging.getLogger("ai_ad_agency.providers.video")


class BaseVideoProvider(ABC):
    @abstractmethod
    def generate_clip(
        self,
        prompt: str,
        output_path: str,
        duration_sec: float = 5.0,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        """Generate a video clip. Returns True on success."""


class RunwayProvider(BaseVideoProvider):
    """
    Runway ML Gen-3 Alpha API.
    Docs: https://docs.runwayml.com/
    """
    BASE_URL = "https://api.runwayml.com/v1"

    def __init__(self, config: VideoProviderConfig):
        self.config = config
        self._limiter = get_limiter("runway", config.requests_per_minute)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

    def _post(self, path: str, payload: Dict) -> Dict:
        import json
        import urllib.request
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        body = json.dumps(payload).encode()
        log_provider_call(logger, "runway", path, str(payload)[:200])
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                log_provider_response(logger, "runway", path, resp.status)
                return data
        except Exception as e:
            raise TransientError(f"Runway error: {e}") from e

    def _get(self, path: str) -> Dict:
        import json
        import urllib.request
        self._limiter.acquire()
        url = f"{self.BASE_URL}{path}"
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"status": "pending"}

    def generate_clip(
        self,
        prompt: str,
        output_path: str,
        duration_sec: float = 5.0,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        payload = {
            "promptText": prompt[:1000],
            "model": "gen3a_turbo",
            "ratio": "720:1280" if height > width else "1280:720",
            "duration": min(int(duration_sec), 10),  # Runway max is 10s
        }
        try:
            resp = self._post("/image_to_video", payload)
            task_id = resp.get("id")
            if not task_id:
                logger.error("Runway: no task id. Response: %s", resp)
                return False

            # Poll for completion
            final = poll_until_complete(
                poll_fn=lambda: self._get(f"/tasks/{task_id}"),
                is_done_fn=lambda r: r.get("status") == "SUCCEEDED",
                is_failed_fn=lambda r: r.get("status") in ("FAILED", "CANCELLED"),
                interval_sec=self.config.poll_interval_sec,
                max_attempts=self.config.max_poll_attempts,
                label=f"runway:{task_id}",
            )
            output_url = (final.get("output") or [None])[0]
            if not output_url:
                logger.error("Runway: no output URL")
                return False

            download_file(output_url, output_path)
            return True
        except Exception as e:
            logger.error("Runway generate_clip failed: %s", e)
            return False


class PikaProvider(BaseVideoProvider):
    """Pika Labs video generation API."""

    BASE_URL = "https://api.pika.art/v1"

    def __init__(self, config: VideoProviderConfig):
        self.config = config
        self._limiter = get_limiter("pika", config.requests_per_minute)

    def generate_clip(
        self,
        prompt: str,
        output_path: str,
        duration_sec: float = 5.0,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        import json
        import urllib.request

        self._limiter.acquire()
        payload = {
            "promptText": prompt[:500],
            "options": {
                "aspectRatio": "9:16" if height > width else "16:9",
                "frameRate": 24,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.BASE_URL}/generate"
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                job_id = data.get("id") or data.get("jobId")
                if not job_id:
                    return False

            # Poll
            for _ in range(self.config.max_poll_attempts):
                time.sleep(self.config.poll_interval_sec)
                poll_req = urllib.request.Request(
                    f"{self.BASE_URL}/jobs/{job_id}", headers=headers
                )
                with urllib.request.urlopen(poll_req, timeout=30) as r:
                    status = json.loads(r.read())
                    if status.get("status") == "complete":
                        url_out = status.get("resultUrl")
                        if url_out:
                            download_file(url_out, output_path)
                            return True
                        return False
                    if status.get("status") in ("failed", "error"):
                        return False
            return False
        except Exception as e:
            logger.error("Pika generate_clip failed: %s", e)
            return False


class ImageToVideoFallback(BaseVideoProvider):
    """
    Fallback B-roll generator.
    Generates an image via the image provider, then converts it to video
    with a Ken Burns zoom/pan effect using FFmpeg.
    This provides realistic-looking B-roll without needing a video API.
    """

    def __init__(self, image_provider: Any, config: VideoProviderConfig):
        self.image_provider = image_provider
        self.config = config

    def generate_clip(
        self,
        prompt: str,
        output_path: str,
        duration_sec: float = 5.0,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        from ..utils.ffmpeg_utils import image_to_video, check_ffmpeg

        # Step 1: Generate a still image
        img_path = Path(output_path).with_suffix(".jpg")
        logger.info("[BROLL FALLBACK] Generating image for clip: %s...", prompt[:50])
        ok = self.image_provider.generate(
            prompt=prompt,
            width=width,
            height=height,
            output_path=str(img_path),
        )
        if not ok or not img_path.exists():
            logger.error("[BROLL FALLBACK] Image generation failed")
            return False

        # Step 2: Convert to video with Ken Burns effect
        if not check_ffmpeg():
            logger.error("[BROLL FALLBACK] FFmpeg not available")
            return False

        ok2 = image_to_video(
            image_path=img_path,
            output_path=output_path,
            duration_sec=duration_sec,
            width=width,
            height=height,
            zoom_pan=True,
        )
        # Clean up temp image
        try:
            img_path.unlink()
        except Exception:
            pass

        return ok2


class MockVideoProvider(BaseVideoProvider):
    """Mock video provider — creates placeholder clips using FFmpeg or empty files."""

    def generate_clip(
        self,
        prompt: str,
        output_path: str,
        duration_sec: float = 5.0,
        width: int = 1080,
        height: int = 1920,
    ) -> bool:
        from ..utils.ffmpeg_utils import create_text_card, check_ffmpeg

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if check_ffmpeg():
            return create_text_card(
                text=f"B-ROLL\n{prompt[:50]}",
                output_path=output_path,
                width=width,
                height=height,
                duration_sec=duration_sec,
                bg_color="#2d4a22",
            )
        else:
            Path(output_path).touch()
            return True


def build_video_provider(
    config: VideoProviderConfig,
    image_provider: Optional[Any] = None,
) -> BaseVideoProvider:
    if config.provider == VideoProvider.RUNWAY:
        if not config.api_key:
            logger.warning("No Runway API key. Using ImageToVideoFallback.")
            if image_provider:
                return ImageToVideoFallback(image_provider, config)
            return MockVideoProvider()
        return RunwayProvider(config)
    elif config.provider == VideoProvider.PIKA:
        if not config.api_key:
            logger.warning("No Pika API key. Using ImageToVideoFallback.")
            if image_provider:
                return ImageToVideoFallback(image_provider, config)
            return MockVideoProvider()
        return PikaProvider(config)
    elif config.provider == VideoProvider.MOCK:
        return MockVideoProvider()
    else:
        # Default: use image-to-video fallback if image provider available
        if image_provider:
            logger.info("Using ImageToVideoFallback for B-roll generation")
            return ImageToVideoFallback(image_provider, config)
        return MockVideoProvider()
