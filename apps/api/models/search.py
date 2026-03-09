from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class SearchStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Search(TimestampMixin, Base):
    __tablename__ = "searches"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    raw_query: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_query_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    platforms: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    include_filters_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    exclude_filters_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    date_from: Mapped[Optional[date]] = mapped_column(nullable=True)
    date_to: Mapped[Optional[date]] = mapped_column(nullable=True)
    max_results: Mapped[int] = mapped_column(Integer, default=50, server_default="50")
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.3, server_default="0.3")
    status: Mapped[SearchStatus] = mapped_column(
        Enum(SearchStatus, name="search_status"),
        default=SearchStatus.queued,
        server_default="queued",
        index=True,
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_candidates: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_analyzed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_results: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="searches")  # noqa: F821
    result_rankings: Mapped[list["ResultRanking"]] = relationship(back_populates="search", lazy="selectin")  # noqa: F821
