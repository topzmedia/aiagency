from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class ResultRanking(TimestampMixin, Base):
    __tablename__ = "result_rankings"

    search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_videos.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_position: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    reason_codes_json: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    score_breakdown_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    matched_segments_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    duplicate_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("duplicate_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    search: Mapped["Search"] = relationship(back_populates="result_rankings")  # noqa: F821
    candidate_video: Mapped["CandidateVideo"] = relationship(back_populates="result_rankings")  # noqa: F821
    duplicate_group: Mapped[Optional["DuplicateGroup"]] = relationship()  # noqa: F821
