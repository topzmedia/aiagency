from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VideoAnalysis(TimestampMixin, Base):
    __tablename__ = "video_analyses"

    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        default=AnalysisStatus.pending,
        server_default="pending",
    )
    scene_segments_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    objects_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    scenes_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    actions_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    ocr_text_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    transcript_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript_chunks_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    audio_events_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    embeddings_json_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    quality_flags_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    candidate_video: Mapped["CandidateVideo"] = relationship(back_populates="analysis")  # noqa: F821
