"""
Export pipeline — runs QA, scoring, and exports accepted creatives.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..models.enums import AssetStatus
from ..models.schemas import (
    CreativeVariant,
    Hook,
    ImageCreative,
    RunManifest,
    Script,
)
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger, log_batch_summary

logger = get_module_logger("export_pipeline")


class ExportPipeline:
    def __init__(self, config: AppConfig):
        from ..agents.export_agent import ExportAgent
        from ..agents.qa_agent import QAAgent
        from ..agents.scoring_agent import ScoringAgent

        self.config = config
        self.qa_agent = QAAgent(config)
        self.scoring_agent = ScoringAgent(config)
        self.export_agent = ExportAgent(config)

    def run(
        self,
        run_id: str,
        manifest: RunManifest,
        creatives: List[CreativeVariant],
        images: List[ImageCreative],
        hooks: List[Hook],
        scripts: List[Script],
        export_dir: str,
        scoring_lookup: Dict[str, Any] = None,
    ) -> Tuple[List[CreativeVariant], str]:
        """
        Full export pipeline:
        1. QA all creatives
        2. Score accepted creatives
        3. Export to clean folder
        Returns (accepted_creatives, export_directory_path)
        """
        Path(export_dir).mkdir(parents=True, exist_ok=True)
        logger.info("Starting export pipeline: run_id=%s creatives=%d", run_id, len(creatives))

        # QA
        passed_results, failed_results = self.qa_agent.run_batch(
            creatives=creatives,
            images=images,
        )
        accepted = [c for c in creatives if c.status == AssetStatus.ACCEPTED]
        rejected = [c for c in creatives if c.status == AssetStatus.REJECTED]

        log_batch_summary(
            logger,
            "QA",
            total=len(creatives),
            accepted=len(accepted),
            rejected=len(rejected),
        )

        # Save QA results
        self.qa_agent.save_results(passed_results + failed_results, export_dir)

        # Score
        if scoring_lookup:
            accepted = self.scoring_agent.score_batch(accepted, scoring_lookup)
        else:
            # Build basic lookup from hooks and scripts lists
            lookup = {
                "hooks": {h.hook_id: h for h in hooks},
                "scripts": {s.script_id: s for s in scripts},
                "avatars": {},
            }
            accepted = self.scoring_agent.score_batch(accepted, lookup)

        log_batch_summary(
            logger,
            "SCORING",
            total=len(accepted),
            accepted=len(accepted),
            rejected=0,
        )

        # Export
        export_path = self.export_agent.export_run(
            run_id=run_id,
            manifest=manifest,
            accepted_creatives=accepted,
            rejected_creatives=rejected,
            images=images,
            hooks=hooks,
            scripts=scripts,
            output_dir=export_dir,
        )

        logger.info("Export complete: %s", export_path)
        return accepted, export_path
