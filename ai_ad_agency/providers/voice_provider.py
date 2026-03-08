"""
Voice generation provider adapter.
Supports ElevenLabs, OpenAI TTS, and Mock.
Used when avatar providers don't handle voice natively or when standalone audio is needed.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.enums import VoiceProvider, VoiceTone
from ..models.schemas import VoiceProfile
from ..utils.config import VoiceProviderConfig
from ..utils.io import get_file_size
from ..utils.logging_utils import log_provider_call, log_provider_response
from ..utils.rate_limits import get_limiter
from ..utils.retries import ProviderRateLimitError, TransientError

logger = logging.getLogger("ai_ad_agency.providers.voice")


class BaseVoiceProvider(ABC):
    @abstractmethod
    def list_voices(self) -> List[Dict[str, Any]]:
        """Return list of available voices as raw provider dicts."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tone: VoiceTone = VoiceTone.CONVERSATIONAL,
    ) -> bool:
        """Generate speech audio file. Returns True on success."""


class ElevenLabsProvider(BaseVoiceProvider):
    """
    ElevenLabs TTS API.
    Docs: https://elevenlabs.io/docs/api-reference/
    """
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, config: VoiceProviderConfig):
        self.config = config
        self._limiter = get_limiter("elevenlabs", config.requests_per_minute)

    def _headers(self) -> Dict[str, str]:
        return {
            "xi-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }

    def list_voices(self) -> List[Dict[str, Any]]:
        import json
        import urllib.request

        self._limiter.acquire()
        req = urllib.request.Request(
            f"{self.BASE_URL}/voices",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data.get("voices", [])
        except Exception as e:
            logger.error("ElevenLabs list_voices failed: %s", e)
            return []

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tone: VoiceTone = VoiceTone.CONVERSATIONAL,
    ) -> bool:
        import json
        import urllib.request

        self._limiter.acquire()

        # Map tone to stability/similarity settings
        tone_settings = {
            VoiceTone.CALM: {"stability": 0.8, "similarity_boost": 0.7},
            VoiceTone.AUTHORITATIVE: {"stability": 0.7, "similarity_boost": 0.8},
            VoiceTone.CONVERSATIONAL: {"stability": 0.5, "similarity_boost": 0.75},
            VoiceTone.TESTIMONIAL: {"stability": 0.4, "similarity_boost": 0.7},
            VoiceTone.ENERGETIC: {"stability": 0.3, "similarity_boost": 0.6},
            VoiceTone.WARM: {"stability": 0.6, "similarity_boost": 0.8},
        }
        settings = tone_settings.get(tone, {"stability": 0.5, "similarity_boost": 0.75})

        payload = {
            "text": text[:5000],
            "model_id": self.config.model_id,
            "voice_settings": settings,
        }
        url = f"{self.BASE_URL}/text-to-speech/{voice_id}"
        log_provider_call(logger, "elevenlabs", url, f"voice={voice_id} text_len={len(text)}")

        headers = {**self._headers(), "Accept": "audio/mpeg"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    import shutil
                    shutil.copyfileobj(resp, f)
                log_provider_response(logger, "elevenlabs", url, "200")
                return True
        except Exception as e:
            err = str(e).lower()
            if "429" in err:
                raise ProviderRateLimitError(f"ElevenLabs rate limit: {e}") from e
            logger.error("ElevenLabs synthesize failed: %s", e)
            return False


class OpenAITTSProvider(BaseVoiceProvider):
    """
    OpenAI TTS API (tts-1 and tts-1-hd).
    """
    # Map tone to OpenAI voice names
    _TONE_TO_VOICE = {
        VoiceTone.CALM: "nova",
        VoiceTone.AUTHORITATIVE: "onyx",
        VoiceTone.CONVERSATIONAL: "alloy",
        VoiceTone.TESTIMONIAL: "shimmer",
        VoiceTone.ENERGETIC: "fable",
        VoiceTone.WARM: "echo",
    }

    def __init__(self, config: VoiceProviderConfig):
        self.config = config
        self._limiter = get_limiter("openai_tts", config.requests_per_minute)
        self._client: Optional[Any] = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.api_key)
        return self._client

    def list_voices(self) -> List[Dict[str, Any]]:
        return [
            {"voice_id": v, "name": v.capitalize(), "tone": t.value}
            for t, v in self._TONE_TO_VOICE.items()
        ]

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tone: VoiceTone = VoiceTone.CONVERSATIONAL,
    ) -> bool:
        self._limiter.acquire()
        client = self._get_client()

        # Use voice_id if provided, otherwise map from tone
        voice = voice_id if voice_id else self._TONE_TO_VOICE.get(tone, "alloy")

        log_provider_call(logger, "openai_tts", "audio.speech.create", f"voice={voice}")
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,  # type: ignore[arg-type]
                input=text[:4096],
            )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(output_path)
            log_provider_response(logger, "openai_tts", "audio.speech.create", "200")
            return True
        except Exception as e:
            logger.error("OpenAI TTS synthesize failed: %s", e)
            return False


class MockVoiceProvider(BaseVoiceProvider):
    """Mock TTS — creates silent audio files using FFmpeg."""

    _MOCK_VOICES = [
        {"voice_id": f"mock_voice_{i:03d}", "name": f"MockVoice_{i:03d}"}
        for i in range(1, 21)
    ]

    def list_voices(self) -> List[Dict[str, Any]]:
        return self._MOCK_VOICES

    def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        tone: VoiceTone = VoiceTone.CONVERSATIONAL,
    ) -> bool:
        from ..utils.ffmpeg_utils import create_silent_audio, check_ffmpeg

        # Estimate duration from word count (avg 130 words/min)
        words = len(text.split())
        duration = max(2.0, words / 130.0 * 60.0)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if check_ffmpeg():
            return create_silent_audio(duration_sec=duration, output_path=output_path)
        else:
            # Create minimal MP3-like file
            Path(output_path).write_bytes(b"\x00" * 1024)
            return True


def build_voice_provider(config: VoiceProviderConfig) -> BaseVoiceProvider:
    if config.provider == VoiceProvider.ELEVENLABS:
        if not config.api_key:
            logger.warning("No ElevenLabs API key — using MockVoiceProvider")
            return MockVoiceProvider()
        return ElevenLabsProvider(config)
    elif config.provider == VoiceProvider.OPENAI_TTS:
        if not config.api_key:
            logger.warning("No OpenAI API key — using MockVoiceProvider")
            return MockVoiceProvider()
        return OpenAITTSProvider(config)
    elif config.provider == VoiceProvider.MOCK:
        return MockVoiceProvider()
    else:
        logger.warning("Unknown voice provider %s — using MockVoiceProvider", config.provider)
        return MockVoiceProvider()
