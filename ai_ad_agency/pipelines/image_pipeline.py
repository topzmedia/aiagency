"""
Image generation pipeline — generates static creatives.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from ..models.schemas import Hook, ImageCreative, OfferConfig
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("image_pipeline")


class ImagePipeline:
    def __init__(
        self,
        config: AppConfig,
        image_provider: object,
        llm_provider: object,
    ):
        from ..agents.image_agent import ImageAgent

        self.config = config
        self.image_agent = ImageAgent(config, image_provider, llm_provider)  # type: ignore

    def run(
        self,
        offer: OfferConfig,
        count: int = 200,
        hooks: List[Hook] = None,
        output_dir: str = "ai_ad_agency/outputs/images",
    ) -> List[ImageCreative]:
        """Generate static image creatives."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Starting image pipeline: count=%d offer=%s", count, offer.offer_name)

        creatives = self.image_agent.generate_batch(
            offer=offer,
            count=count,
            output_dir=output_dir,
            hooks=hooks or [],
        )
        logger.info("Generated %d image creatives", len(creatives))
        return creatives
