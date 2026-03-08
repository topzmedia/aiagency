"""
Image Agent — generates static image creatives using an image provider.
Handles batch generation, prompt building with LLM, style cycling, and metadata persistence.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from ..models.enums import AssetStatus, ImageProvider, ImageStyle
from ..models.schemas import Hook, ImageCreative, OfferConfig
from ..providers.image_provider import BaseImageProvider
from ..utils.config import AppConfig
from ..utils.io import ensure_dir, get_file_size, read_json, write_models_json
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("image_agent")

_METADATA_FILE = "image_creatives.json"

# ---------------------------------------------------------------------------
# Prompt building — no LLM needed; built-in templates per style
# ---------------------------------------------------------------------------

_STYLE_PROMPT_TEMPLATES = {
    ImageStyle.LIFESTYLE: (
        "Lifestyle photo ad for {offer_name}. {target_audience} in a natural, relatable setting. "
        "Mood: {mood}. Brand colors: {brand_colors}. Photorealistic, high quality, 8K, "
        "warm lighting, aspirational but authentic. No text overlay."
    ),
    ImageStyle.TESTIMONIAL_STILL: (
        "Static testimonial image for {offer_name}. Happy {target_audience} with a genuine smile. "
        "Clean background. Photorealistic portrait. Subtle brand accent color: {brand_colors}. "
        "Room for text overlay at bottom. No text in image."
    ),
    ImageStyle.HEADLINE: (
        "Bold headline-style social media ad image for {offer_name}. "
        "Eye-catching graphic with strong contrast, brand colors: {brand_colors}. "
        "Minimal design with visual metaphor representing {benefit}. "
        "Leave space for large headline text overlay. No actual text in image."
    ),
    ImageStyle.QUOTE_CARD: (
        "Quote card background for {offer_name} social media ad. "
        "Soft gradient or blurred background. Colors: {brand_colors}. "
        "Clean, elegant, minimal. Leaves center space for quote text overlay."
    ),
    ImageStyle.INFOGRAPHIC: (
        "Infographic-style ad creative for {offer_name}. "
        "Clean icons and visual elements representing {benefit}. "
        "Brand palette: {brand_colors}. Flat design, clear visual hierarchy. "
        "Placeholders for stat numbers. No actual text."
    ),
    ImageStyle.BEFORE_AFTER: (
        "Before and after style ad image split-panel for {offer_name}. "
        "Left side: problem state for {target_audience}, muted tones. "
        "Right side: solution/improved state, vibrant brand colors: {brand_colors}. "
        "Photorealistic, high contrast between panels."
    ),
    ImageStyle.UGC_SCREENSHOT: (
        "User-generated content style image for {offer_name}. "
        "Authentic, slightly imperfect. Looks like a real photo taken on a phone. "
        "Shows {target_audience} naturally using or benefiting from the product. "
        "Candid, genuine, relatable. No professional lighting."
    ),
}

_MOODS = ["warm", "energetic", "calm", "hopeful", "confident", "friendly"]
_NEGATIVE_PROMPT = (
    "blurry, low quality, watermark, text, letters, words, signature, "
    "distorted faces, extra limbs, ugly, deformed"
)

# Standard ad dimensions (width x height)
_DIMENSIONS = [
    (1080, 1080),  # Square
    (1080, 1350),  # Portrait 4:5
    (1080, 1920),  # Story 9:16
    (1200, 628),   # Landscape 1.91:1
]


class ImageAgent:
    """
    Generates static image creatives for ad campaigns.

    Uses a template-based prompt system (optionally enhanced by an LLM)
    to produce diverse, style-varied images via the configured image provider.
    """

    def __init__(
        self,
        config: AppConfig,
        provider: BaseImageProvider,
        llm_provider: object = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.llm_provider = llm_provider  # Optional; used for prompt enrichment

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        offer: OfferConfig,
        count: int = 200,
        output_dir: str = "",
        hooks: Optional[List[Hook]] = None,
    ) -> List[ImageCreative]:
        """
        Generate `count` image creatives with style/dimension variety.

        - Cycles through ImageStyle values and standard ad dimensions.
        - Optionally pairs with hooks for headline-style images.
        - Skips already-completed creatives (idempotent reruns).
        - Saves metadata JSON after each successful generation.

        Args:
            offer: OfferConfig describing the product/audience.
            count: Total number of images to generate.
            output_dir: Directory to save images and metadata.
            hooks: Optional list of Hook objects for headline/quote images.

        Returns:
            List of completed ImageCreative objects.
        """
        out_dir = Path(output_dir) if output_dir else Path(self.config.base_output_dir) / "images"
        ensure_dir(out_dir)

        # Load any previously completed creatives to allow resumption
        existing = self.load_existing(str(out_dir))
        existing_paths = {c.file_path for c in existing if c.status == AssetStatus.COMPLETED}

        styles = list(offer.image_styles) if offer.image_styles else list(ImageStyle)
        hooks = hooks or []
        creatives: List[ImageCreative] = list(existing)
        generated = 0

        logger.info(
            "ImageAgent: generating %d images for offer=%s styles=%d",
            count,
            offer.offer_name,
            len(styles),
        )

        for i in range(count):
            style = styles[i % len(styles)]
            width, height = _DIMENSIONS[i % len(_DIMENSIONS)]
            mood = _MOODS[i % len(_MOODS)]
            hook = hooks[i % len(hooks)] if hooks else None
            benefit = offer.benefits[i % len(offer.benefits)] if offer.benefits else offer.offer_description[:80]

            # Build output path using a stable placeholder creative
            placeholder = ImageCreative(
                offer_name=offer.offer_name,
                style=style,
                prompt="",
                file_path="",
                width=width,
                height=height,
                provider=self.config.providers.image.provider,
            )
            output_path = str(out_dir / f"image_{placeholder.image_id}.jpg")

            # Skip if already generated on a prior run
            if output_path in existing_paths:
                logger.debug("ImageAgent: skipping existing creative %s", output_path)
                continue

            prompt = self.build_prompt(
                offer=offer,
                style=style,
                mood=mood,
                benefit=benefit,
                hook=hook,
            )

            if (i + 1) % 10 == 0 or i == 0:
                logger.info(
                    "ImageAgent: generating %d/%d — style=%s size=%dx%d",
                    i + 1, count, style.value, width, height,
                )

            try:
                ok = self.provider.generate(
                    prompt=prompt,
                    width=width,
                    height=height,
                    output_path=output_path,
                    negative_prompt=_NEGATIVE_PROMPT,
                )
            except Exception as exc:
                logger.warning(
                    "ImageAgent: image %d/%d raised exception: %s — skipping",
                    i + 1, count, exc,
                )
                ok = False

            if not ok or not Path(output_path).exists():
                logger.warning(
                    "ImageAgent: image %d/%d failed to generate — skipping",
                    i + 1, count,
                )
                continue

            creative = ImageCreative(
                image_id=placeholder.image_id,
                offer_name=offer.offer_name,
                style=style,
                prompt=prompt,
                file_path=output_path,
                width=width,
                height=height,
                file_size_bytes=get_file_size(output_path),
                provider=self.config.providers.image.provider,
                hook_id=hook.hook_id if hook else None,
                headline_text=hook.text if hook and style in (ImageStyle.HEADLINE, ImageStyle.QUOTE_CARD) else None,
                cta_text=offer.cta or "Learn More",
                status=AssetStatus.COMPLETED,
            )
            creatives.append(creative)
            generated += 1

            # Persist metadata incrementally
            if generated % 5 == 0:
                self.save_metadata(creatives, str(out_dir))

        # Final save
        self.save_metadata(creatives, str(out_dir))
        logger.info(
            "ImageAgent: generated %d/%d images successfully",
            generated, count,
        )
        return [c for c in creatives if c.status == AssetStatus.COMPLETED]

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        offer: OfferConfig,
        style: ImageStyle,
        mood: str = "warm",
        benefit: str = "",
        hook: Optional[Hook] = None,
    ) -> str:
        """
        Build an image generation prompt for the given style and offer.

        If an LLM provider is configured, enriches the template prompt.
        Otherwise returns the template-rendered prompt directly.
        """
        brand_colors = ", ".join(offer.brand_colors) if offer.brand_colors else "neutral professional"
        template = _STYLE_PROMPT_TEMPLATES.get(style, _STYLE_PROMPT_TEMPLATES[ImageStyle.LIFESTYLE])

        base_prompt = template.format(
            offer_name=offer.offer_name,
            target_audience=offer.target_audience,
            mood=mood,
            brand_colors=brand_colors,
            benefit=benefit or offer.offer_description[:80],
        )

        # Optionally append hook text for headline/quote styles
        if hook and style in (ImageStyle.HEADLINE, ImageStyle.QUOTE_CARD):
            base_prompt += f" Concept: {hook.text[:120]}"

        # LLM enrichment: expand the prompt if provider is available
        if self.llm_provider is not None:
            try:
                enriched = self._enrich_prompt_with_llm(base_prompt, offer, style)
                if enriched:
                    return enriched
            except Exception as exc:
                logger.debug("LLM prompt enrichment failed, using template: %s", exc)

        return base_prompt

    def _enrich_prompt_with_llm(
        self,
        base_prompt: str,
        offer: OfferConfig,
        style: ImageStyle,
    ) -> Optional[str]:
        """Ask LLM to refine the image generation prompt. Returns None on failure."""
        system = (
            "You are an expert at writing prompts for AI image generation tools like DALL-E and Stable Diffusion. "
            "Refine the given prompt to be more vivid, specific, and effective. "
            "Keep it under 400 characters. Return only the refined prompt, nothing else."
        )
        user = (
            f"Refine this image prompt for a {style.value} style ad:\n\n{base_prompt}\n\n"
            f"Offer: {offer.offer_name}. Target: {offer.target_audience}."
        )
        try:
            response = self.llm_provider.complete(system=system, user=user, max_tokens=200)
            if response and len(response.strip()) > 20:
                return response.strip()
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_metadata(self, creatives: List[ImageCreative], output_dir: str) -> None:
        """Persist creative metadata to image_creatives.json in output_dir."""
        out_dir = Path(output_dir)
        ensure_dir(out_dir)
        meta_path = out_dir / _METADATA_FILE
        write_models_json(creatives, str(meta_path))
        logger.debug(
            "ImageAgent: saved metadata for %d creatives → %s",
            len(creatives), meta_path,
        )

    def load_existing(self, output_dir: str) -> List[ImageCreative]:
        """Load previously generated creatives from metadata JSON. Returns [] on miss."""
        meta_path = Path(output_dir) / _METADATA_FILE
        if not meta_path.exists():
            return []
        try:
            raw = read_json(str(meta_path))
            creatives = [ImageCreative(**item) for item in raw]
            logger.info(
                "ImageAgent.load_existing: loaded %d creatives from %s",
                len(creatives), meta_path,
            )
            return creatives
        except Exception as exc:
            logger.warning("ImageAgent.load_existing: failed to load %s: %s", meta_path, exc)
            return []
