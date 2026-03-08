"""
Image generation provider adapter.
Supports OpenAI DALL-E, Stability AI, and Mock.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.enums import ImageProvider
from ..utils.config import ImageProviderConfig
from ..utils.io import download_file, get_file_size
from ..utils.logging_utils import log_provider_call, log_provider_response
from ..utils.rate_limits import get_limiter
from ..utils.retries import ProviderRateLimitError, ProviderTimeoutError, TransientError

logger = logging.getLogger("ai_ad_agency.providers.image")


class BaseImageProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: str,
        negative_prompt: str = "",
    ) -> bool:
        """Generate an image and save to output_path. Returns True on success."""


class OpenAIImageProvider(BaseImageProvider):
    """
    OpenAI DALL-E 3 image generation.
    """
    # DALL-E 3 supported sizes
    _SUPPORTED_SIZES = {"1024x1024", "1024x1792", "1792x1024"}

    def __init__(self, config: ImageProviderConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._limiter = get_limiter("openai_image", config.requests_per_minute)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError("openai package not installed.")
            self._client = OpenAI(api_key=self.config.api_key)
        return self._client

    def _nearest_size(self, width: int, height: int) -> str:
        """Map requested dimensions to closest DALL-E 3 supported size."""
        aspect = width / height if height else 1
        if aspect > 1.2:
            return "1792x1024"
        elif aspect < 0.8:
            return "1024x1792"
        return "1024x1024"

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: str,
        negative_prompt: str = "",
    ) -> bool:
        self._limiter.acquire()
        size = self._nearest_size(width, height)
        client = self._get_client()

        log_provider_call(
            logger, "openai_image", "images.generate",
            f"model={self.config.model} size={size} prompt_len={len(prompt)}"
        )

        try:
            response = client.images.generate(
                model=self.config.model,
                prompt=prompt[:4000],
                size=size,  # type: ignore[arg-type]
                quality="standard",
                n=1,
            )
            img_url = response.data[0].url
            if not img_url:
                logger.error("No URL in DALL-E response")
                return False

            log_provider_response(logger, "openai_image", "images.generate", "200")

            # Download image
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            download_file(img_url, output_path, timeout=60)

            # Resize/crop to exact requested dimensions if needed
            if (width, height) != tuple(int(x) for x in size.split("x")):
                self._resize(output_path, width, height)

            return True

        except Exception as e:
            err = str(e).lower()
            if "rate limit" in err or "429" in err:
                raise ProviderRateLimitError(f"DALL-E rate limit: {e}") from e
            if "timeout" in err:
                raise ProviderTimeoutError(f"DALL-E timeout: {e}") from e
            if "billing" in err or "quota" in err:
                logger.error("DALL-E billing/quota error: %s", e)
                return False
            logger.error("DALL-E generation failed: %s", e)
            return False

    def _resize(self, path: str, width: int, height: int) -> None:
        """Resize image to exact dimensions using Pillow."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                resized = img.resize((width, height), Image.LANCZOS)
                resized.save(path, optimize=True)
        except ImportError:
            logger.debug("Pillow not available; skipping resize")
        except Exception as e:
            logger.warning("Image resize failed: %s", e)


class StabilityProvider(BaseImageProvider):
    """
    Stability AI image generation (stable-diffusion-xl).
    """
    BASE_URL = "https://api.stability.ai"

    def __init__(self, config: ImageProviderConfig):
        self.config = config
        self._limiter = get_limiter("stability", config.requests_per_minute)

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: str,
        negative_prompt: str = "",
    ) -> bool:
        import json
        import urllib.request

        self._limiter.acquire()
        # Round to multiples of 64
        w = (width // 64) * 64 or 1024
        h = (height // 64) * 64 or 1024

        engine = "stable-diffusion-xl-1024-v1-0"
        url = f"{self.BASE_URL}/v1/generation/{engine}/text-to-image"

        payload = {
            "text_prompts": [{"text": prompt[:2000], "weight": 1.0}],
            "width": w,
            "height": h,
            "samples": 1,
            "steps": 30,
        }
        if negative_prompt:
            payload["text_prompts"].append({"text": negative_prompt, "weight": -1.0})

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        log_provider_call(logger, "stability", url, f"size={w}x{h}")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                artifacts = data.get("artifacts", [])
                if not artifacts:
                    logger.error("No artifacts in Stability response")
                    return False

                import base64
                img_bytes = base64.b64decode(artifacts[0]["base64"])
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                log_provider_response(logger, "stability", url, "200")
                return True
        except Exception as e:
            err = str(e).lower()
            if "429" in err:
                raise ProviderRateLimitError(f"Stability rate limit: {e}") from e
            logger.error("Stability generation failed: %s", e)
            return False


class MockImageProvider(BaseImageProvider):
    """Mock image provider — creates solid-color placeholder images."""

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        output_path: str,
        negative_prompt: str = "",
    ) -> bool:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageDraw, ImageFont
            # Create a solid-color image with the prompt text overlaid
            import hashlib
            h = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
            r, g, b = (h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF
            img = Image.new("RGB", (width, height), color=(r, g, b))
            draw = ImageDraw.Draw(img)
            draw.text(
                (width // 2, height // 2),
                f"MOCK\n{prompt[:60]}",
                fill="white",
                anchor="mm",
            )
            img.save(output_path)
            logger.debug("[MOCK IMAGE] Created %dx%d → %s", width, height, Path(output_path).name)
            return True
        except ImportError:
            # No Pillow: write a tiny valid JPEG
            with open(output_path, "wb") as f:
                # Minimal valid JPEG bytes
                f.write(bytes([
                    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00,
                    0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9
                ]))
            return True


def build_image_provider(config: ImageProviderConfig) -> BaseImageProvider:
    if config.provider == ImageProvider.OPENAI_DALLE:
        if not config.api_key:
            logger.warning("No OpenAI API key — using MockImageProvider")
            return MockImageProvider()
        return OpenAIImageProvider(config)
    elif config.provider == ImageProvider.STABILITY:
        if not config.api_key:
            logger.warning("No Stability API key — using MockImageProvider")
            return MockImageProvider()
        return StabilityProvider(config)
    elif config.provider == ImageProvider.MOCK:
        return MockImageProvider()
    else:
        logger.warning("Unknown image provider %s — using MockImageProvider", config.provider)
        return MockImageProvider()
