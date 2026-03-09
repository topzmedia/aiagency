from __future__ import annotations

import enum
from typing import Any, Optional

from sqlalchemy import Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.models.base import Base, TimestampMixin


class IngestionStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class IngestionJob(TimestampMixin, Base):
    __tablename__ = "ingestion_jobs"

    source_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source_config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(IngestionStatus, name="ingestion_status"),
        default=IngestionStatus.queued,
        server_default="queued",
        index=True,
    )
    total_records: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    imported_records: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rejected_records: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    log_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
