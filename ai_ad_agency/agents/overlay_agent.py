"""
Overlay Agent — creates hook cards, CTA end cards, and lower-third graphics.
All cards are rendered as short video clips using FFmpeg via ffmpeg_utils.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models.schemas import Hook, Overlay
from ..utils.config import AppConfig
from ..utils.ffmpeg_utils import check_ffmpeg, create_text_card
from ..utils.io import ensure_dir
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("overlay_agent")

# ---------------------------------------------------------------------------
# Style palette
# ---------------------------------------------------------------------------

_STYLE_COLORS: Dict[str, Dict[str, str]] = {
    "dark":    {"bg": "#0d0d0d",   "fg": "white"},
    "brand":   {"bg": "#1B4F72",   "fg": "white"},
    "urgent":  {"bg": "#C0392B",   "fg": "white"},
    "default": {"bg": "#000000",   "fg": "white"},
}


class OverlayAgent:
    """Creates pre-rendered overlay card video clips."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._ffmpeg_available: Optional[bool] = None

    # ------------------------------------------------------------------
    # FFmpeg guard
    # ------------------------------------------------------------------

    def _check_ffmpeg(self) -> bool:
        if self._ffmpeg_available is None:
            self._ffmpeg_available = check_ffmpeg()
            if not self._ffmpeg_available:
                logger.warning("OverlayAgent: FFmpeg not found — overlay cards cannot be rendered")
        return self._ffmpeg_available

    # ------------------------------------------------------------------
    # Hook card
    # ------------------------------------------------------------------

    def create_hook_card(
        self,
        text: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        style: str = "default",
    ) -> Optional[Overlay]:
        """
        Create a full-frame hook text card video clip.

        Styles: "dark", "brand", "urgent", "default"
        Duration comes from config.render.hook_card_duration_sec (default 2.5s).
        Returns an Overlay model or None on failure.
        """
        if not self._check_ffmpeg():
            return None

        colors = _STYLE_COLORS.get(style, _STYLE_COLORS["default"])
        duration = getattr(self.config.render, "hook_card_duration_sec", 2.5)

        ensure_dir(Path(output_path).parent)
        ok = create_text_card(
            text=text,
            output_path=output_path,
            width=width,
            height=height,
            duration_sec=duration,
            bg_color=colors["bg"],
            font_color=colors["fg"],
            font_size=self.config.render.overlay_font_size,
        )
        if not ok:
            logger.error("OverlayAgent.create_hook_card: FFmpeg failed for path=%s", output_path)
            return None

        overlay = Overlay(
            overlay_type="hook_card",
            text=text,
            file_path=output_path,
            duration_sec=duration,
            position="center",
            font_size=self.config.render.overlay_font_size,
            font_color=colors["fg"],
            bg_color=colors["bg"],
        )
        logger.debug("OverlayAgent: created hook card → %s", output_path)
        return overlay

    # ------------------------------------------------------------------
    # CTA end card
    # ------------------------------------------------------------------

    def create_cta_card(
        self,
        cta_text: str,
        landing_page: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
    ) -> Optional[Overlay]:
        """
        Create a CTA end card with CTA text and a simplified URL.

        Duration comes from config.render.cta_card_duration_sec (default 3.0s).
        Background is always the brand blue #1B4F72.
        Returns an Overlay model or None on failure.
        """
        if not self._check_ffmpeg():
            return None

        duration = getattr(self.config.render, "cta_card_duration_sec", 3.0)
        bg_color = "#1B4F72"
        font_color = "white"

        # Simplify URL to domain only for cleaner display
        display_url = _simplify_url(landing_page)
        combined_text = f"{cta_text}\n{display_url}" if display_url else cta_text

        ensure_dir(Path(output_path).parent)
        ok = create_text_card(
            text=combined_text,
            output_path=output_path,
            width=width,
            height=height,
            duration_sec=duration,
            bg_color=bg_color,
            font_color=font_color,
            font_size=self.config.render.overlay_font_size,
        )
        if not ok:
            logger.error("OverlayAgent.create_cta_card: FFmpeg failed for path=%s", output_path)
            return None

        overlay = Overlay(
            overlay_type="cta_end",
            text=combined_text,
            file_path=output_path,
            duration_sec=duration,
            position="center",
            font_size=self.config.render.overlay_font_size,
            font_color=font_color,
            bg_color=bg_color,
        )
        logger.debug("OverlayAgent: created CTA card → %s", output_path)
        return overlay

    # ------------------------------------------------------------------
    # Lower third
    # ------------------------------------------------------------------

    def create_lower_third(
        self,
        name: str,
        title: str,
        output_path: str,
        width: int = 1080,
        height: int = 400,
    ) -> Optional[Overlay]:
        """
        Create a lower-third graphic as a short video clip.

        Uses a semi-transparent dark background (#00000088).
        Duration is 3.0 seconds.
        Returns an Overlay model or None on failure.
        """
        if not self._check_ffmpeg():
            return None

        bg_color = "#00000088"
        font_color = "white"
        duration = 3.0
        text = f"{name}\n{title}" if title else name

        ensure_dir(Path(output_path).parent)
        ok = create_text_card(
            text=text,
            output_path=output_path,
            width=width,
            height=height,
            duration_sec=duration,
            bg_color=bg_color,
            font_color=font_color,
            font_size=max(32, self.config.render.overlay_font_size - 10),
        )
        if not ok:
            logger.error("OverlayAgent.create_lower_third: FFmpeg failed for path=%s", output_path)
            return None

        overlay = Overlay(
            overlay_type="lower_third",
            text=text,
            file_path=output_path,
            duration_sec=duration,
            position="bottom",
            font_size=max(32, self.config.render.overlay_font_size - 10),
            font_color=font_color,
            bg_color=bg_color,
        )
        logger.debug("OverlayAgent: created lower-third → %s", output_path)
        return overlay

    # ------------------------------------------------------------------
    # Batch generation
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        hooks: List[Hook],
        cta_text: str,
        landing_page: str,
        output_dir: str,
    ) -> Dict[str, List[Overlay]]:
        """
        Generate hook cards and CTA cards for a list of hooks.

        Returns:
            {
                "hook_cards": [Overlay, ...],
                "cta_cards":  [Overlay, ...],
            }
        Hook cards use "dark" style.
        CTA cards are deduplicated — one per unique (cta_text, landing_page).
        """
        out_dir = Path(output_dir)
        ensure_dir(out_dir)

        hook_cards: List[Overlay] = []
        cta_cards: List[Overlay] = []

        # Generate one hook card per hook
        for hook in hooks:
            safe_id = hook.hook_id.replace("-", "")[:16]
            card_path = str(out_dir / f"hook_card_{safe_id}.mp4")

            card = self.create_hook_card(
                text=hook.text,
                output_path=card_path,
                style="dark",
            )
            if card is not None:
                hook_cards.append(card)

        # Generate a single shared CTA card (one is sufficient for batch)
        if cta_text:
            cta_path = str(out_dir / "cta_card_main.mp4")
            cta_card = self.create_cta_card(
                cta_text=cta_text,
                landing_page=landing_page,
                output_path=cta_path,
            )
            if cta_card is not None:
                cta_cards.append(cta_card)

        logger.info(
            "OverlayAgent batch: %d hook cards, %d CTA cards generated",
            len(hook_cards),
            len(cta_cards),
        )
        return {"hook_cards": hook_cards, "cta_cards": cta_cards}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simplify_url(url: str) -> str:
    """Extract and return just the domain from a URL, or the full URL if parsing fails."""
    if not url:
        return ""
    # Strip protocol
    url = url.strip()
    clean = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    # Strip path — take only up to first slash
    domain = clean.split("/")[0]
    return domain if domain else url
