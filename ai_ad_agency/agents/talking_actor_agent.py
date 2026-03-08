"""
Talking Actor Agent — generates lip-synced talking-actor videos using an avatar provider.
Handles batch rendering, retry logic, job tracking, and script-to-avatar pairing.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.enums import AvatarProvider, RenderStatus
from ..models.schemas import Script, ScriptVariant, TalkingActorJob
from ..providers.avatar_provider import BaseAvatarProvider
from ..utils.config import AppConfig
from ..utils.io import models_to_csv, write_models_json
from ..utils.logging_utils import get_module_logger
from ..utils.retries import TransientError, with_retries

logger = get_module_logger("talking_actor_agent")


class TalkingActorAgent:
    """
    Generates lip-synced talking-actor videos by pairing scripts with avatars.

    Supports batch rendering with sequential job processing (to respect provider
    rate limits), automatic skip of already-completed jobs, and configurable retry.
    """

    def __init__(
        self,
        config: AppConfig,
        provider: BaseAvatarProvider,
        avatar_catalog: "AvatarCatalogAgent",  # noqa: F821
    ) -> None:
        self.config = config
        self.provider = provider
        self.avatar_catalog = avatar_catalog
        self._max_retries = config.max_retries
        logger.debug(
            "TalkingActorAgent initialized. max_retries=%d poll_interval=%ds",
            self._max_retries,
            config.providers.avatar.poll_interval_sec,
        )

    # ------------------------------------------------------------------
    # Batch generation
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        jobs: List[TalkingActorJob],
        output_dir: str,
        max_concurrent: int = 5,
    ) -> List[TalkingActorJob]:
        """
        Process talking-actor render jobs sequentially, respecting provider rate limits.

        - Skips jobs already in COMPLETED status whose output file exists.
        - Retries failed jobs up to config.max_retries times.
        - Saves job metadata JSON after every job attempt.

        Args:
            jobs: List of TalkingActorJob objects to render.
            output_dir: Directory where rendered video files will be saved.
            max_concurrent: Accepted for API compatibility; rendering is sequential.

        Returns:
            Updated list of TalkingActorJob with render_status, file_path, etc.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        total = len(jobs)
        completed_count = 0
        skipped_count = 0
        failed_count = 0

        logger.info("Starting batch render: %d jobs → %s", total, output_dir)

        for idx, job in enumerate(jobs, start=1):
            # Skip already completed jobs whose output files exist on disk
            if job.render_status == RenderStatus.COMPLETED and job.file_path:
                if Path(job.file_path).exists():
                    logger.debug(
                        "Skipping completed job %d/%d: %s (file exists)",
                        idx, total, job.job_id,
                    )
                    skipped_count += 1
                    continue

            script_preview = (
                job.voice_safe_text[:60] + "..."
                if len(job.voice_safe_text) > 60
                else job.voice_safe_text
            )
            logger.info(
                "Rendering job %d/%d: avatar=%s script=%r",
                idx, total, job.avatar_id, script_preview,
            )

            # Attempt render with manual retry loop so we can reset status between tries
            success = False
            for attempt in range(1, self._max_retries + 2):
                try:
                    job = self.generate_single(job, output_dir)
                    if job.render_status == RenderStatus.COMPLETED:
                        success = True
                        break
                    # Provider returned a failure status without raising
                    if attempt <= self._max_retries:
                        logger.warning(
                            "Job %s attempt %d/%d returned status=%s — retrying",
                            job.job_id, attempt, self._max_retries + 1, job.render_status,
                        )
                        job.render_status = RenderStatus.QUEUED
                except (TransientError, Exception) as exc:
                    if attempt <= self._max_retries:
                        logger.warning(
                            "Job %s attempt %d/%d raised %s: %s — retrying",
                            job.job_id, attempt, self._max_retries + 1,
                            type(exc).__name__, exc,
                        )
                        job.render_status = RenderStatus.QUEUED
                    else:
                        logger.error(
                            "Job %s permanently failed after %d attempts: %s",
                            job.job_id, attempt, exc,
                        )
                        job.render_status = RenderStatus.FAILED
                        job.error_message = str(exc)
                        break

            if success:
                completed_count += 1
                logger.info(
                    "Job %d/%d completed: %s (%.1f KB)",
                    idx, total, job.job_id, job.file_size_bytes / 1024,
                )
            else:
                failed_count += 1
                logger.warning("Job %d/%d failed: %s", idx, total, job.job_id)

            # Persist job state after every attempt
            self.save_jobs(jobs, output_dir)

        logger.info(
            "[BATCH RENDER] Done: completed=%d skipped=%d failed=%d total=%d",
            completed_count, skipped_count, failed_count, total,
        )
        return jobs

    # ------------------------------------------------------------------
    # Single render
    # ------------------------------------------------------------------

    def generate_single(
        self,
        job: TalkingActorJob,
        output_dir: str,
    ) -> TalkingActorJob:
        """
        Render a single talking-actor video for the given job.

        Delegates to provider.render_and_download(), which handles
        submit → poll → download. Updates the job object in place and returns it.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Fast-path: already done and file exists
        if (
            job.render_status == RenderStatus.COMPLETED
            and job.file_path
            and Path(job.file_path).exists()
        ):
            logger.debug("generate_single: job %s already completed — skipping", job.job_id)
            return job

        def _do_render() -> TalkingActorJob:
            return self.provider.render_and_download(
                job=job,
                output_dir=output_dir,
                poll_interval=self.config.providers.avatar.poll_interval_sec,
                max_polls=self.config.providers.avatar.max_poll_attempts,
            )

        try:
            updated = with_retries(
                _do_render,
                max_attempts=self.config.max_retries,
                base_delay=self.config.retry_base_delay_sec,
                retryable_exceptions=(TransientError,),
            )
            return updated if updated is not None else job
        except Exception as exc:
            job.render_status = RenderStatus.FAILED
            job.error_message = str(exc)
            logger.error("generate_single: job %s failed: %s", job.job_id, exc)
            return job

    # ------------------------------------------------------------------
    # Job creation
    # ------------------------------------------------------------------

    def create_jobs_from_scripts(
        self,
        scripts: List[Union[Script, ScriptVariant]],
        avatar_ids: List[str],
        voice_mapping: Optional[Dict[str, str]] = None,
    ) -> List[TalkingActorJob]:
        """
        Pair scripts with avatars (round-robin) and create one TalkingActorJob per pair.

        Args:
            scripts: List of Script or ScriptVariant objects.
            avatar_ids: Provider avatar IDs to cycle through.
            voice_mapping: Maps avatar_id → voice_id override. When absent, the
                           avatar catalog's default voice_id is used.

        Returns:
            List of TalkingActorJob objects in QUEUED state.
        """
        if not avatar_ids:
            logger.warning("create_jobs_from_scripts: no avatar_ids — returning empty list")
            return []
        if not scripts:
            logger.warning("create_jobs_from_scripts: no scripts — returning empty list")
            return []

        voice_mapping = voice_mapping or {}
        jobs: List[TalkingActorJob] = []
        num_avatars = len(avatar_ids)

        for i, script in enumerate(scripts):
            avatar_id = avatar_ids[i % num_avatars]

            # Resolve voice_id: explicit mapping > catalog default
            voice_id: Optional[str] = voice_mapping.get(avatar_id)
            if voice_id is None:
                avatar_meta = self.avatar_catalog.get_by_id(avatar_id)
                if avatar_meta and avatar_meta.voice_id:
                    voice_id = avatar_meta.voice_id

            # Resolve script_id and text from either Schema type
            if isinstance(script, Script):
                script_id = script.script_id
                voice_safe_text = script.voice_safe_text
                duration_sec: Optional[float] = float(script.estimated_duration_sec)
            else:
                # ScriptVariant
                script_id = script.variant_id
                voice_safe_text = script.voice_safe_text
                duration_sec = float(script.estimated_duration_sec)

            # Determine avatar provider from catalog metadata
            avatar_meta = self.avatar_catalog.get_by_id(avatar_id)
            if avatar_meta:
                raw_provider = avatar_meta.provider
                if isinstance(raw_provider, str):
                    try:
                        avatar_provider = AvatarProvider(raw_provider)
                    except ValueError:
                        avatar_provider = self.config.providers.avatar.provider
                else:
                    avatar_provider = raw_provider
            else:
                avatar_provider = self.config.providers.avatar.provider

            job = TalkingActorJob(
                avatar_id=avatar_id,
                avatar_provider=avatar_provider,
                script_id=script_id,
                voice_safe_text=voice_safe_text,
                voice_id=voice_id,
                duration_sec=duration_sec,
                width=self.config.providers.avatar.render_width,
                height=self.config.providers.avatar.render_height,
            )
            jobs.append(job)

        logger.info(
            "Created %d TalkingActorJob(s): %d script(s) × %d avatar(s) (round-robin)",
            len(jobs), len(scripts), len(avatar_ids),
        )
        return jobs

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_jobs(
        self,
        jobs: List[TalkingActorJob],
        output_dir: str,
    ) -> None:
        """Save job list as JSON + CSV metadata files in output_dir."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        json_path = Path(output_dir) / "talking_actor_jobs.json"
        csv_path = Path(output_dir) / "talking_actor_jobs.csv"
        try:
            write_models_json(jobs, str(json_path))
            models_to_csv(jobs, str(csv_path))
            logger.debug("Saved %d job record(s) → %s", len(jobs), json_path)
        except Exception as exc:
            logger.warning("Failed to save job metadata to %s: %s", json_path, exc)

    def get_completion_stats(self, jobs: List[TalkingActorJob]) -> Dict[str, int]:
        """Return a summary count dict for job statuses."""
        stats: Dict[str, int] = {
            "total": len(jobs),
            "completed": 0,
            "failed": 0,
            "queued": 0,
            "processing": 0,
            "timeout": 0,
        }
        for job in jobs:
            status = (
                job.render_status.value
                if hasattr(job.render_status, "value")
                else str(job.render_status)
            )
            if status in stats:
                stats[status] += 1
        return stats


# Runtime resolution of the forward-reference annotation
from .avatar_catalog_agent import AvatarCatalogAgent  # noqa: E402
