"""
Avatar pipeline — syncs catalog, selects avatars, renders talking-actor clips.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.schemas import AvatarMetadata, Script, ScriptVariant, TalkingActorJob
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("avatar_pipeline")


class AvatarPipeline:
    def __init__(
        self,
        config: AppConfig,
        avatar_provider: object,
        voice_provider: object,
    ):
        from ..agents.avatar_catalog_agent import AvatarCatalogAgent
        from ..agents.talking_actor_agent import TalkingActorAgent
        from ..agents.voice_agent import VoiceAgent

        self.config = config
        self.catalog_agent = AvatarCatalogAgent(config, avatar_provider)  # type: ignore
        self.actor_agent = TalkingActorAgent(config, avatar_provider, self.catalog_agent)  # type: ignore
        self.voice_agent = VoiceAgent(config, voice_provider)  # type: ignore

    def sync_catalog(self) -> int:
        """Sync avatar catalog from provider. Returns number of new avatars found."""
        return self.catalog_agent.sync_from_provider()

    def select_avatars(
        self,
        count: int,
        quotas: Optional[Dict] = None,
    ) -> List[AvatarMetadata]:
        """Select a diverse batch of avatars."""
        return self.catalog_agent.select_balanced_batch(count, quotas)

    def run(
        self,
        scripts: List[Union[Script, ScriptVariant]],
        avatars: List[AvatarMetadata],
        output_dir: str,
        voice_mapping: Optional[Dict[str, str]] = None,
    ) -> List[TalkingActorJob]:
        """
        Create and render talking actor jobs for all script+avatar combos.
        Returns completed (or attempted) TalkingActorJob list.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        logger.info(
            "Starting avatar pipeline: scripts=%d avatars=%d",
            len(scripts),
            len(avatars),
        )

        # Build voice mapping if not provided
        if voice_mapping is None:
            voice_profiles = self.voice_agent.sync_voices()
            voice_mapping = {}
            for avatar in avatars:
                profile = self.voice_agent.select_voice_for_avatar(avatar, voice_profiles)
                if profile:
                    voice_mapping[avatar.avatar_id] = profile.voice_id

        # Create jobs
        jobs = self.actor_agent.create_jobs_from_scripts(
            scripts=scripts,
            avatar_ids=[a.avatar_id for a in avatars],
            voice_mapping=voice_mapping,
        )
        logger.info("Created %d talking actor jobs", len(jobs))

        # Render
        completed_jobs = self.actor_agent.generate_batch(
            jobs=jobs,
            output_dir=output_dir,
            max_concurrent=self.config.max_concurrent_renders,
        )

        done = sum(1 for j in completed_jobs if j.render_status.value == "completed")
        failed = sum(1 for j in completed_jobs if j.render_status.value == "failed")
        logger.info("Avatar pipeline done: completed=%d failed=%d", done, failed)

        return completed_jobs
