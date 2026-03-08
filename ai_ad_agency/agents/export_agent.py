"""
Export Agent — packages accepted creatives into a clean deliverable folder structure.

Creates:
    outputs/exports/{run_id}/
        videos/           — accepted video files
        images/           — accepted image files
        metadata/
            metadata.json
            metadata.csv
            accepted_list.json
            rejected_list.json
            hooks.json
            scripts.json
            creative_manifest.json
        run_summary.txt
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.schemas import (
    CreativeVariant,
    ExportRecord,
    Hook,
    ImageCreative,
    RunManifest,
    Script,
)
from ..models.enums import AssetStatus, CreativeType
from ..utils.config import AppConfig
from ..utils.io import (
    copy_file,
    ensure_dir,
    get_file_size,
    models_to_csv,
    write_json,
    write_models_json,
)
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("export_agent")


class ExportAgent:
    """Exports accepted creatives into a structured delivery folder."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Main export entry point
    # ------------------------------------------------------------------

    def export_run(
        self,
        run_id: str,
        manifest: RunManifest,
        accepted_creatives: List[CreativeVariant],
        rejected_creatives: List[CreativeVariant],
        images: List[ImageCreative],
        hooks: List[Hook],
        scripts: List[Script],
        output_dir: str,
    ) -> str:
        """
        Export all accepted assets for a run into a structured folder.

        Creates:
          {output_dir}/exports/{run_id}/
            videos/
            images/
            metadata/
              metadata.json
              metadata.csv
              accepted_list.json
              rejected_list.json
              hooks.json
              scripts.json
              creative_manifest.json
            run_summary.txt

        Updates manifest.export_dir.
        Returns the export directory path.
        """
        # Build export root
        export_root = Path(output_dir) / "exports" / run_id
        videos_dir = export_root / "videos"
        images_dir = export_root / "images"
        metadata_dir = export_root / "metadata"

        for d in (export_root, videos_dir, images_dir, metadata_dir):
            ensure_dir(d)

        logger.info(
            "ExportAgent: exporting run_id=%s | accepted=%d rejected=%d images=%d",
            run_id,
            len(accepted_creatives),
            len(rejected_creatives),
            len(images),
        )

        # Build lookup dicts for hooks and scripts
        hooks_dict: Dict[str, Hook] = {h.hook_id: h for h in hooks}
        scripts_dict: Dict[str, Script] = {s.script_id: s for s in scripts}

        # --- Copy accepted video files ---
        video_count = 0
        for creative in accepted_creatives:
            if not creative.file_path:
                continue
            src = Path(creative.file_path)
            if not src.exists():
                logger.warning(
                    "ExportAgent: accepted creative %s has missing file: %s",
                    creative.creative_id,
                    creative.file_path,
                )
                continue
            dest = videos_dir / src.name
            # Avoid filename collisions: prefix with short creative_id
            if dest.exists():
                dest = videos_dir / f"{creative.creative_id[:8]}_{src.name}"
            try:
                copy_file(src, dest)
                creative.export_path = str(dest)
                creative.exported_at = datetime.utcnow()
                video_count += 1
            except Exception as exc:
                logger.error(
                    "ExportAgent: failed to copy %s → %s: %s",
                    src,
                    dest,
                    exc,
                )

        # --- Copy accepted image files ---
        accepted_image_ids = {c.image_id for c in accepted_creatives if c.image_id}
        image_count = 0
        for image in images:
            if image.status not in (AssetStatus.ACCEPTED,) and image.image_id not in accepted_image_ids:
                continue
            if not image.file_path:
                continue
            src = Path(image.file_path)
            if not src.exists():
                logger.warning(
                    "ExportAgent: image %s has missing file: %s",
                    image.image_id,
                    image.file_path,
                )
                continue
            dest = images_dir / src.name
            if dest.exists():
                dest = images_dir / f"{image.image_id[:8]}_{src.name}"
            try:
                copy_file(src, dest)
                image_count += 1
            except Exception as exc:
                logger.error("ExportAgent: failed to copy image %s: %s", src, exc)

        # --- Build export records ---
        export_records = self.build_export_records(
            accepted_creatives, hooks_dict, scripts_dict
        )

        # --- Write metadata files ---
        # Full metadata JSON + CSV
        write_models_json(
            accepted_creatives + rejected_creatives,
            metadata_dir / "metadata.json",
        )
        models_to_csv(
            accepted_creatives + rejected_creatives,
            metadata_dir / "metadata.csv",
        )

        # Accepted and rejected lists
        write_models_json(accepted_creatives, metadata_dir / "accepted_list.json")
        write_models_json(rejected_creatives, metadata_dir / "rejected_list.json")

        # Hooks and scripts
        write_models_json(hooks, metadata_dir / "hooks.json")
        write_models_json(scripts, metadata_dir / "scripts.json")

        # Creative manifest (summary of export records)
        manifest_data = {
            "run_id": run_id,
            "exported_at": datetime.utcnow().isoformat(),
            "total_accepted": len(accepted_creatives),
            "total_rejected": len(rejected_creatives),
            "videos_exported": video_count,
            "images_exported": image_count,
            "export_records": [r.model_dump(mode="json") for r in export_records],
        }
        write_json(manifest_data, metadata_dir / "creative_manifest.json")

        # --- Run summary text ---
        self._write_run_summary(
            manifest=manifest,
            accepted=len(accepted_creatives),
            rejected=len(rejected_creatives),
            export_dir=str(export_root),
        )

        # --- Update manifest ---
        manifest.export_dir = str(export_root)

        logger.info(
            "ExportAgent: export complete → %s | videos=%d images=%d",
            export_root,
            video_count,
            image_count,
        )
        return str(export_root)

    # ------------------------------------------------------------------
    # Export records builder
    # ------------------------------------------------------------------

    def build_export_records(
        self,
        creatives: List[CreativeVariant],
        hooks: Dict,
        scripts: Dict,
    ) -> List[ExportRecord]:
        """
        Build ExportRecord objects from accepted creative variants.

        Args:
            creatives: List of CreativeVariant (typically accepted ones).
            hooks:     Dict mapping hook_id → Hook.
            scripts:   Dict mapping script_id → Script.
        """
        records: List[ExportRecord] = []
        for creative in creatives:
            hook = hooks.get(creative.hook_id) if creative.hook_id else None
            script = scripts.get(creative.script_id) if creative.script_id else None

            record = ExportRecord(
                run_id=creative.run_id,
                creative_id=creative.creative_id,
                source_path=creative.file_path or "",
                export_path=creative.export_path or "",
                creative_type=creative.creative_type,
                hook_text=hook.text if hook else creative.hook_text,
                script_id=creative.script_id,
                avatar_id=creative.avatar_id,
                voice_id=creative.voice_id,
                broll_ids=list(creative.broll_ids),
                duration_sec=creative.duration_sec,
                width=creative.width,
                height=creative.height,
                file_size_bytes=get_file_size(creative.export_path or creative.file_path or ""),
                score=creative.score,
                qa_notes=list(creative.qa_notes),
                exported_at=creative.exported_at or datetime.utcnow(),
                status=AssetStatus.ACCEPTED,
            )
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Run summary text file
    # ------------------------------------------------------------------

    def _write_run_summary(
        self,
        manifest: RunManifest,
        accepted: int,
        rejected: int,
        export_dir: str,
    ) -> None:
        """
        Write a human-readable run summary text file to {export_dir}/run_summary.txt.
        """
        export_path = Path(export_dir)
        ensure_dir(export_path)
        summary_path = export_path / "run_summary.txt"

        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        started_str = (
            manifest.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if manifest.started_at else "N/A"
        )
        completed_str = (
            manifest.completed_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if manifest.completed_at else "N/A"
        )

        # Count actual video and image files
        videos_dir = export_path / "videos"
        images_dir = export_path / "images"
        video_files = list(videos_dir.glob("*.mp4")) if videos_dir.exists() else []
        image_files = (
            [f for f in images_dir.iterdir() if f.is_file()]
            if images_dir.exists() else []
        )

        lines = [
            "=" * 60,
            "AI AD AGENCY — RUN EXPORT SUMMARY",
            "=" * 60,
            f"Run ID:              {manifest.run_id}",
            f"Offer:               {manifest.offer_name}",
            f"Export Generated:    {now_str}",
            f"Run Started:         {started_str}",
            f"Run Completed:       {completed_str}",
            "",
            "--- ASSET GENERATION ---",
            f"Hooks Generated:     {manifest.hooks_generated}",
            f"Rotated Hooks:       {manifest.rotated_hooks_generated}",
            f"Scripts Generated:   {manifest.scripts_generated}",
            f"Script Variants:     {manifest.script_variants_generated}",
            f"Images Generated:    {manifest.images_generated}",
            f"B-Roll Clips:        {manifest.broll_clips_generated}",
            f"Actor Jobs:          {manifest.talking_actor_jobs}",
            "",
            "--- VARIANTS ---",
            f"Variants Planned:    {manifest.variants_planned}",
            f"Variants Rendered:   {manifest.variants_rendered}",
            f"Variants Accepted:   {manifest.variants_accepted}",
            f"Variants Rejected:   {manifest.variants_rejected}",
            "",
            "--- EXPORT ---",
            f"Accepted Creatives:  {accepted}",
            f"Rejected Creatives:  {rejected}",
            f"Video Files Exported:{len(video_files)}",
            f"Image Files Exported:{len(image_files)}",
            f"Export Directory:    {export_dir}",
            "",
            "--- STATUS ---",
            f"Run Status:          {manifest.status}",
        ]
        if manifest.error:
            lines.append(f"Error:               {manifest.error}")
        lines.append("=" * 60)

        summary_text = "\n".join(lines) + "\n"
        try:
            summary_path.write_text(summary_text, encoding="utf-8")
            logger.info("ExportAgent: wrote run summary → %s", summary_path)
        except Exception as exc:
            logger.error("ExportAgent: failed to write run summary: %s", exc)
