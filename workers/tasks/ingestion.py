"""Ingestion task: imports candidate videos from various data sources."""
from __future__ import annotations

import csv
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from workers.celery_app import app
from workers.db import get_sync_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapters registry
# ---------------------------------------------------------------------------

def _csv_adapter(source_config: dict[str, Any], session: Any) -> tuple[int, int, list[dict]]:
    """Import candidate videos from a CSV file.

    Returns (imported, rejected, log_entries).
    """
    from apps.api.models.candidate_video import CandidateVideo

    csv_path = source_config.get("file_path", "")
    if not csv_path or not Path(csv_path).exists():
        return 0, 0, [{"error": f"CSV file not found: {csv_path}"}]

    imported = 0
    rejected = 0
    log_entries: list[dict] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=1):
            try:
                source_url = row.get("source_url", "").strip()
                if not source_url:
                    rejected += 1
                    log_entries.append({"row": row_num, "error": "missing source_url"})
                    continue

                platform = row.get("platform", "unknown").strip()

                # Parse publish_date
                publish_date = None
                pd_str = row.get("publish_date", "").strip()
                if pd_str:
                    try:
                        publish_date = datetime.fromisoformat(pd_str)
                    except ValueError:
                        publish_date = None

                # Parse duration
                duration_sec = None
                dur_str = row.get("duration_sec", "").strip()
                if dur_str:
                    try:
                        duration_sec = float(dur_str)
                    except ValueError:
                        duration_sec = None

                # Parse hashtags
                hashtags_raw = row.get("hashtags", "").strip()
                hashtags = [h.strip() for h in hashtags_raw.split(",") if h.strip()] if hashtags_raw else []

                candidate = CandidateVideo(
                    id=uuid.uuid4(),
                    external_id=row.get("external_id", "").strip() or None,
                    platform=platform,
                    source_url=source_url,
                    canonical_url=row.get("canonical_url", "").strip() or None,
                    creator_handle=row.get("creator_handle", "").strip() or None,
                    creator_name=row.get("creator_name", "").strip() or None,
                    caption_text=row.get("caption_text", "").strip() or None,
                    hashtags_json=hashtags if hashtags else None,
                    publish_date=publish_date,
                    duration_sec=duration_sec,
                    language=row.get("language", "").strip() or None,
                    region_hint=row.get("region_hint", "").strip() or None,
                    ingestion_source="csv_import",
                    metadata_json={},
                )
                session.add(candidate)
                imported += 1
                log_entries.append({"row": row_num, "status": "imported", "source_url": source_url})

            except Exception as exc:
                rejected += 1
                log_entries.append({"row": row_num, "error": str(exc)})

    session.flush()
    return imported, rejected, log_entries


def _demo_seed_adapter(source_config: dict[str, Any], session: Any) -> tuple[int, int, list[dict]]:
    """Generate demo candidate videos from built-in seed data."""
    from apps.api.models.candidate_video import CandidateVideo

    seed_records = source_config.get("records", [])
    imported = 0
    rejected = 0
    log_entries: list[dict] = []

    for i, rec in enumerate(seed_records):
        try:
            candidate = CandidateVideo(
                id=uuid.uuid4(),
                external_id=rec.get("external_id"),
                platform=rec.get("platform", "unknown"),
                source_url=rec.get("source_url", f"https://example.com/video/{i}"),
                creator_handle=rec.get("creator_handle"),
                caption_text=rec.get("caption_text"),
                hashtags_json=rec.get("hashtags"),
                publish_date=datetime.fromisoformat(rec["publish_date"]) if rec.get("publish_date") else None,
                duration_sec=rec.get("duration_sec"),
                language=rec.get("language", "en"),
                region_hint=rec.get("region_hint", "US"),
                ingestion_source="demo_seed",
                metadata_json=rec.get("metadata", {}),
            )
            session.add(candidate)
            imported += 1
            log_entries.append({"index": i, "status": "imported"})
        except Exception as exc:
            rejected += 1
            log_entries.append({"index": i, "error": str(exc)})

    session.flush()
    return imported, rejected, log_entries


_ADAPTERS: dict[str, Any] = {
    "csv": _csv_adapter,
    "demo_seed": _demo_seed_adapter,
}


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@app.task(name="workers.tasks.ingestion.run_ingestion_job", bind=True, max_retries=2)
def run_ingestion_job(self, job_id: str) -> dict:
    """Load an IngestionJob from the DB, run the matching adapter, and update
    the job record with import counts and status."""
    from apps.api.models.ingestion_job import IngestionJob, IngestionStatus

    session = get_sync_session()
    try:
        job = session.get(IngestionJob, uuid.UUID(job_id))
        if job is None:
            logger.error("IngestionJob %s not found", job_id)
            return {"error": "job_not_found"}

        # Mark as processing
        job.status = IngestionStatus.processing
        session.commit()

        adapter_fn = _ADAPTERS.get(job.source_type)
        if adapter_fn is None:
            job.status = IngestionStatus.failed
            job.log_json = [{"error": f"Unknown source_type: {job.source_type}"}]
            session.commit()
            return {"error": f"unknown_source_type: {job.source_type}"}

        imported, rejected, log_entries = adapter_fn(job.source_config_json, session)

        job.imported_records = imported
        job.rejected_records = rejected
        job.total_records = imported + rejected
        job.log_json = log_entries
        job.status = IngestionStatus.completed
        session.commit()

        logger.info(
            "IngestionJob %s completed: %d imported, %d rejected",
            job_id, imported, rejected,
        )
        return {
            "job_id": job_id,
            "imported": imported,
            "rejected": rejected,
            "status": "completed",
        }

    except Exception as exc:
        session.rollback()
        logger.exception("IngestionJob %s failed: %s", job_id, exc)
        try:
            job = session.get(IngestionJob, uuid.UUID(job_id))
            if job:
                job.status = IngestionStatus.failed
                job.log_json = [{"error": str(exc)}]
                session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()
