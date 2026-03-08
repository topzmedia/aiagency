"""
Script generation pipeline — orchestrates script_agent + script_variant_agent.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple

from ..models.schemas import Hook, OfferConfig, Script, ScriptVariant
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("script_pipeline")


class ScriptPipeline:
    def __init__(self, config: AppConfig, llm_provider: object):
        from ..agents.script_agent import ScriptAgent
        from ..agents.script_variant_agent import ScriptVariantAgent

        self.config = config
        self.script_agent = ScriptAgent(config, llm_provider)  # type: ignore
        self.variant_agent = ScriptVariantAgent(config, llm_provider)  # type: ignore

    def run(
        self,
        offer: OfferConfig,
        hooks: List[Hook],
        scripts_per_hook: int = 3,
        variants_per_script: int = 2,
        output_dir: str = "ai_ad_agency/outputs/scripts",
    ) -> Tuple[List[Script], List[ScriptVariant]]:
        """
        Full script pipeline:
        1. Generate scripts from hooks
        2. Generate script variants
        Returns (scripts, variants)
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting script pipeline: hooks=%d scripts_per_hook=%d",
            len(hooks),
            scripts_per_hook,
        )

        scripts = self.script_agent.generate(
            offer=offer,
            hooks=hooks,
            scripts_per_hook=scripts_per_hook,
            output_dir=output_dir,
        )
        logger.info("Generated %d scripts", len(scripts))

        variants = self.variant_agent.generate(
            scripts=scripts,
            variants_per_script=variants_per_script,
            output_dir=output_dir,
        )
        logger.info("Generated %d script variants", len(variants))

        return scripts, variants
