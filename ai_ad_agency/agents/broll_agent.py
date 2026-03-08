"""
B-Roll Agent — generates cinematic video clips using a video provider.
Supports batched generation, theme rotation, and graceful failure handling.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from ..models.enums import AssetStatus
from ..models.schemas import BRollClip, OfferConfig
from ..providers.video_provider import BaseVideoProvider
from ..utils.config import AppConfig
from ..utils.io import ensure_dir, get_file_size, read_json, write_models_json
from ..utils.logging_utils import get_module_logger
from ..utils.prompt_templates import BROLL_PROMPT_TEMPLATE, BROLL_SCENE_TEMPLATES

logger = get_module_logger("broll_agent")

# ---------------------------------------------------------------------------
# Variation pools for prompt diversity
# ---------------------------------------------------------------------------

_MOODS = ["calm", "energetic", "warm", "professional"]
_LIGHTINGS = ["natural", "golden hour", "soft indoor", "bright daylight"]
_CAMERA_STYLES = ["handheld", "static", "slow pan", "gentle zoom"]

_BROLL_METADATA_FILE = "broll_clips.json"


class BRollAgent:
    """Generates B-roll video clips for ad creatives."""

    def __init__(self, config: AppConfig, provider: BaseVideoProvider) -> None:
        self.config = config
        self.provider = provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        offer: OfferConfig,
        count: int = 40,
        output_dir: str = "",
    ) -> List[BRollClip]:
        """
        Generate `count` B-roll clips using offer.broll_themes.

        Iterates through themes and scene templates, varying mood/lighting/
        camera style on each clip. Saves each clip as broll_{broll_id}.mp4.
        Skips and continues on individual failures.
        """
        out_dir = Path(output_dir) if output_dir else Path(self.config.base_output_dir) / "broll"
        ensure_dir(out_dir)

        themes = list(offer.broll_themes) if offer.broll_themes else list(BROLL_SCENE_TEMPLATES.keys())
        if not themes:
            themes = list(BROLL_SCENE_TEMPLATES.keys())

        scene_keys = list(BROLL_SCENE_TEMPLATES.keys())

        clips: List[BRollClip] = []
        generated = 0

        logger.info(
            "BRollAgent: generating %d clips for offer=%s using %d themes",
            count,
            offer.offer_name,
            len(themes),
        )

        for i in range(count):
            # Cycle through themes, scene templates, and variation params
            theme = themes[i % len(themes)]
            scene_key = scene_keys[i % len(scene_keys)]
            mood = _MOODS[i % len(_MOODS)]
            lighting = _LIGHTINGS[i % len(_LIGHTINGS)]
            camera = _CAMERA_STYLES[i % len(_CAMERA_STYLES)]

            prompt = self.build_prompt(theme=theme, mood=mood, lighting=lighting, camera=camera)

            # Create a temporary clip object to get a stable ID for the filename
            clip_placeholder = BRollClip(
                theme=theme,
                prompt=prompt,
                file_path="",
                duration_sec=5.0,
                width=1080,
                height=1920,
                tags=[theme, mood, lighting, camera],
            )

            output_path = str(out_dir / f"broll_{clip_placeholder.broll_id}.mp4")

            if (i + 1) % 5 == 0 or i == 0:
                logger.info(
                    "BRollAgent: generating clip %d/%d — theme=%s mood=%s",
                    i + 1,
                    count,
                    theme,
                    mood,
                )

            try:
                ok = self.provider.generate_clip(
                    prompt=prompt,
                    output_path=output_path,
                    duration_sec=5.0,
                    width=1080,
                    height=1920,
                )
            except Exception as exc:
                logger.warning(
                    "BRollAgent: clip %d/%d failed with exception: %s — skipping",
                    i + 1,
                    count,
                    exc,
                )
                ok = False

            if not ok or not Path(output_path).exists():
                logger.warning(
                    "BRollAgent: clip %d/%d could not be generated — skipping",
                    i + 1,
                    count,
                )
                continue

            file_size = get_file_size(output_path)
            clip = BRollClip(
                broll_id=clip_placeholder.broll_id,
                theme=theme,
                prompt=prompt,
                file_path=output_path,
                duration_sec=5.0,
                width=1080,
                height=1920,
                file_size_bytes=file_size,
                provider=self.config.providers.video.provider,
                tags=[theme, mood, lighting, camera],
                status=AssetStatus.COMPLETED,
            )
            clips.append(clip)
            generated += 1

        logger.info(
            "BRollAgent: generated %d/%d clips successfully",
            generated,
            count,
        )

        self.save_metadata(clips, str(out_dir))
        return clips

    def build_prompt(
        self,
        theme: str,
        mood: str,
        lighting: str,
        camera: str,
    ) -> str:
        """
        Build a video generation prompt from theme + variation parameters.
        Uses BROLL_SCENE_TEMPLATES for the scene description; falls back to
        the theme string itself if not found in the template dict.
        """
        scene_description = BROLL_SCENE_TEMPLATES.get(theme, theme)
        return BROLL_PROMPT_TEMPLATE.format(
            scene_description=scene_description,
            mood=mood,
            lighting=lighting,
            camera_style=camera,
        )

    def save_metadata(self, clips: List[BRollClip], output_dir: str) -> None:
        """Persist clip metadata to broll_clips.json inside output_dir."""
        out_dir = Path(output_dir)
        ensure_dir(out_dir)
        meta_path = out_dir / _BROLL_METADATA_FILE
        write_models_json(clips, meta_path)
        logger.debug("BRollAgent: saved metadata for %d clips → %s", len(clips), meta_path)

    def load_existing(self, output_dir: str) -> List[BRollClip]:
        """
        Load previously generated B-roll clips from broll_clips.json if it exists.
        Returns an empty list if the file is absent or unreadable.
        """
        meta_path = Path(output_dir) / _BROLL_METADATA_FILE
        if not meta_path.exists():
            logger.debug("BRollAgent.load_existing: no metadata file at %s", meta_path)
            return []

        try:
            raw = read_json(meta_path)
            clips = [BRollClip(**item) for item in raw]
            logger.info("BRollAgent.load_existing: loaded %d clips from %s", len(clips), meta_path)
            return clips
        except Exception as exc:
            logger.warning("BRollAgent.load_existing: failed to load %s: %s", meta_path, exc)
            return []
