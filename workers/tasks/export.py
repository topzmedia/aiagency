"""Export task: generate CSV or JSON export files for search results."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from workers.celery_app import app
from workers.db import get_sync_session

logger = logging.getLogger(__name__)

EXPORTS_DIR = os.getenv("EXPORTS_DIR", "/data/exports")


@app.task(name="workers.tasks.export.build_export", bind=True, max_retries=2)
def build_export(self, search_id: str, format: str = "csv") -> dict:
    """Generate an export file (CSV or JSON) for the results of a search.

    The file is written to the exports directory and the path is returned.
    """
    from apps.api.models.search import Search
    from apps.api.models.result_ranking import ResultRanking
    from apps.api.models.candidate_video import CandidateVideo

    session = get_sync_session()
    try:
        search = session.get(Search, uuid.UUID(search_id))
        if search is None:
            return {"error": "search_not_found"}

        # Fetch rankings with candidate info
        rankings = session.execute(
            select(ResultRanking)
            .where(ResultRanking.search_id == uuid.UUID(search_id))
            .order_by(ResultRanking.rank_position)
        ).scalars().all()

        if not rankings:
            return {"search_id": search_id, "status": "no_results", "path": None}

        # Build export rows
        rows = []
        for r in rankings:
            candidate = session.get(CandidateVideo, r.candidate_video_id)
            row = {
                "rank": r.rank_position,
                "score": r.final_score,
                "accepted": r.accepted,
                "platform": candidate.platform if candidate else "",
                "source_url": candidate.source_url if candidate else "",
                "creator_handle": candidate.creator_handle if candidate else "",
                "caption_text": candidate.caption_text if candidate else "",
                "duration_sec": candidate.duration_sec if candidate else "",
                "language": candidate.language if candidate else "",
                "publish_date": str(candidate.publish_date) if candidate and candidate.publish_date else "",
                "reason_codes": ",".join(r.reason_codes_json or []),
                "duplicate_group_id": str(r.duplicate_group_id) if r.duplicate_group_id else "",
            }
            rows.append(row)

        # Ensure exports directory exists
        Path(EXPORTS_DIR).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"search_{search_id[:8]}_{timestamp}.{format}"
        filepath = os.path.join(EXPORTS_DIR, filename)

        if format == "json":
            export_data = {
                "search_id": search_id,
                "query": search.raw_query,
                "exported_at": datetime.utcnow().isoformat(),
                "total_results": len(rows),
                "results": rows,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str)
        else:
            # CSV
            if rows:
                fieldnames = list(rows[0].keys())
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

        logger.info("Export written to %s (%d results)", filepath, len(rows))
        return {
            "search_id": search_id,
            "status": "completed",
            "format": format,
            "path": filepath,
            "total_results": len(rows),
        }

    except Exception as exc:
        session.rollback()
        logger.exception("Export failed for search %s: %s", search_id, exc)
        raise self.retry(exc=exc, countdown=10)
    finally:
        session.close()
