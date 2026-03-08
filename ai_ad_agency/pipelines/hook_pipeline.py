"""
Hook generation pipeline — orchestrates hook_agent + rotating_hook_agent.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from ..models.schemas import Hook, OfferConfig, RotatedHook
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("hook_pipeline")


class HookPipeline:
    def __init__(self, config: AppConfig, llm_provider: object):
        from ..agents.hook_agent import HookAgent
        from ..agents.rotating_hook_agent import RotatingHookAgent
        from ..providers.llm_provider import BaseLLMProvider

        self.config = config
        self.hook_agent = HookAgent(config, llm_provider)  # type: ignore
        self.rotating_agent = RotatingHookAgent(config, llm_provider)  # type: ignore

    def run(
        self,
        offer: OfferConfig,
        count: int = 200,
        output_dir: str = "ai_ad_agency/outputs/hooks",
        rotations_per_hook: int = 4,
        run_id: str = "",
    ) -> Tuple[List[Hook], List[RotatedHook]]:
        """
        Full hook pipeline:
        1. Generate hooks
        2. Generate rotated hook variants

        Returns (hooks, rotated_hooks)
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        logger.info("Starting hook pipeline: count=%d offer=%s", count, offer.offer_name)

        # Generate hooks
        hooks = self.hook_agent.generate(
            offer=offer,
            total_count=count,
            output_dir=output_dir,
        )
        logger.info("Generated %d hooks", len(hooks))

        # Generate rotated variants for each hook
        rotated = self.rotating_agent.generate_variants(
            hooks=hooks,
            variants_per_hook=rotations_per_hook,
            output_dir=output_dir,
        )
        logger.info("Generated %d rotated hook variants", len(rotated))

        return hooks, rotated
