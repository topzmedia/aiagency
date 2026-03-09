"""Base adapter interface for ingestion sources.

All ingestion adapters inherit from :class:`AbstractIngestionAdapter` and
implement its four methods.  The base class provides a common ``run()``
orchestration flow.
"""
from __future__ import annotations

import abc
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RawRecord:
    """A raw record as read from the ingestion source, before normalisation."""
    source_ref: str  # unique reference within the source (filename, row ID, URL)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateVideoCreate:
    """Normalised record ready for insertion into the candidate_videos table."""
    external_id: str | None = None
    platform: str = "unknown"
    source_url: str = ""
    canonical_url: str | None = None
    creator_handle: str | None = None
    creator_name: str | None = None
    caption_text: str | None = None
    hashtags_json: list[str] | None = None
    publish_date: datetime | None = None
    duration_sec: float | None = None
    language: str | None = None
    region_hint: str | None = None
    thumbnail_path: str | None = None
    local_media_path: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    ingestion_source: str = ""


@dataclass
class IngestionFailure:
    """Details of a single failed record during ingestion."""
    source_ref: str
    error: str


@dataclass
class IngestionResult:
    """Summary of an ingestion run."""
    source_name: str
    total_records: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    failures: list[IngestionFailure] = field(default_factory=list)
    created_ids: list[uuid.UUID] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract adapter
# ---------------------------------------------------------------------------

class AbstractIngestionAdapter(abc.ABC):
    """Base class for all ingestion adapters."""

    @property
    @abc.abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this ingestion source."""
        ...

    @abc.abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate the adapter configuration.

        Should raise ``ValueError`` with a descriptive message on invalid
        config.
        """
        ...

    @abc.abstractmethod
    def enumerate_records(self, config: dict[str, Any]) -> Iterator[RawRecord]:
        """Yield raw records from the source."""
        ...

    @abc.abstractmethod
    def normalize_record(self, raw: RawRecord) -> CandidateVideoCreate:
        """Convert a raw record into a normalised :class:`CandidateVideoCreate`."""
        ...

    def run(self, config: dict[str, Any]) -> IngestionResult:
        """Execute the full ingestion flow.

        1. Validate config
        2. Enumerate records
        3. Normalise each record
        4. Collect results
        """
        self.validate_config(config)
        result = IngestionResult(source_name=self.source_name)

        for raw in self.enumerate_records(config):
            result.total_records += 1
            try:
                normalised = self.normalize_record(raw)
                # Attach to result for the caller to persist
                vid = uuid.uuid4()
                result.created_ids.append(vid)
                result.created += 1

                # Store normalised data on the raw record for downstream use
                raw.data["_normalised"] = normalised
                raw.data["_assigned_id"] = vid

            except Exception as exc:
                result.failed += 1
                result.failures.append(IngestionFailure(
                    source_ref=raw.source_ref,
                    error=str(exc),
                ))
                logger.warning("Failed to normalise record %s: %s", raw.source_ref, exc)

        logger.info(
            "Ingestion '%s' complete: %d total, %d created, %d failed",
            self.source_name, result.total_records, result.created, result.failed,
        )
        return result
