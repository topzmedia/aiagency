"""CSV import ingestion adapter.

Reads a CSV file with candidate video metadata and creates candidate_video
records.  Each row is validated and normalised; failures are logged and
reported in the ingestion result.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from apps.api.services.ingestion.base import (
    AbstractIngestionAdapter,
    CandidateVideoCreate,
    RawRecord,
)

logger = logging.getLogger(__name__)

# Expected / supported CSV columns
EXPECTED_COLUMNS = {
    "source_url",
    "platform",
    "creator_handle",
    "creator_name",
    "caption_text",
    "hashtags",
    "local_media_path",
    "publish_date",
    "language",
    "region_hint",
    "duration_sec",
}


class CSVImportAdapter(AbstractIngestionAdapter):
    """Ingest candidate videos from a CSV file."""

    @property
    def source_name(self) -> str:
        return "csv_import"

    def validate_config(self, config: dict[str, Any]) -> bool:
        csv_path = config.get("csv_path")
        if not csv_path:
            raise ValueError("Config must include 'csv_path'")
        p = Path(csv_path)
        if not p.exists():
            raise ValueError(f"CSV file does not exist: {csv_path}")
        if not p.is_file():
            raise ValueError(f"Path is not a file: {csv_path}")
        if p.suffix.lower() not in (".csv", ".tsv"):
            raise ValueError(f"Expected .csv or .tsv file, got: {p.suffix}")
        return True

    def enumerate_records(self, config: dict[str, Any]) -> Iterator[RawRecord]:
        csv_path = Path(config["csv_path"])
        encoding = config.get("encoding", "utf-8")
        delimiter = config.get("delimiter", ",")

        with open(csv_path, newline="", encoding=encoding) as f:
            reader = csv.DictReader(f, delimiter=delimiter)

            if reader.fieldnames is None:
                raise ValueError("CSV file has no header row")

            # Warn about unknown columns
            known = EXPECTED_COLUMNS
            actual = set(reader.fieldnames)
            unknown = actual - known
            if unknown:
                logger.warning("CSV contains unknown columns (will be stored in metadata): %s", unknown)
            missing = known - actual
            if missing:
                logger.info("CSV missing optional columns: %s", missing)

            for row_idx, row in enumerate(reader, start=2):  # start=2 (header is row 1)
                yield RawRecord(
                    source_ref=f"{csv_path.name}:row_{row_idx}",
                    data=dict(row),
                )

    def normalize_record(self, raw: RawRecord) -> CandidateVideoCreate:
        data = raw.data

        source_url = data.get("source_url", "").strip()
        if not source_url:
            local = data.get("local_media_path", "").strip()
            if local:
                source_url = f"file://{local}"
            else:
                raise ValueError(f"Row {raw.source_ref}: source_url or local_media_path required")

        # Parse hashtags (comma or space separated, or JSON-like list)
        hashtags_raw = data.get("hashtags", "").strip()
        hashtags = _parse_hashtags(hashtags_raw) if hashtags_raw else None

        # Parse publish date
        publish_date = _parse_date(data.get("publish_date", "").strip())

        # Parse duration
        duration_sec = _parse_float(data.get("duration_sec", "").strip())

        # Collect extra columns as metadata
        extra_keys = set(data.keys()) - EXPECTED_COLUMNS
        metadata = {k: data[k] for k in extra_keys if data.get(k)}

        return CandidateVideoCreate(
            external_id=None,
            platform=data.get("platform", "unknown").strip() or "unknown",
            source_url=source_url,
            creator_handle=data.get("creator_handle", "").strip() or None,
            creator_name=data.get("creator_name", "").strip() or None,
            caption_text=data.get("caption_text", "").strip() or None,
            hashtags_json=hashtags,
            publish_date=publish_date,
            duration_sec=duration_sec,
            language=data.get("language", "").strip() or None,
            region_hint=data.get("region_hint", "").strip() or None,
            local_media_path=data.get("local_media_path", "").strip() or None,
            metadata_json=metadata,
            ingestion_source="csv_import",
        )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_hashtags(raw: str) -> list[str]:
    """Parse a hashtag string into a list."""
    # Handle JSON-style lists
    if raw.startswith("["):
        import json
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

    # Comma or space separated
    tags: list[str] = []
    for token in raw.replace(",", " ").split():
        token = token.strip()
        if token:
            if not token.startswith("#"):
                token = f"#{token}"
            tags.append(token)
    return tags


def _parse_date(raw: str) -> datetime | None:
    """Try common date formats."""
    if not raw:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    logger.warning("Could not parse date: %s", raw)
    return None


def _parse_float(raw: str) -> float | None:
    """Parse a float value, returning None on failure."""
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        logger.warning("Could not parse float: %s", raw)
        return None
