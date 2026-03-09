from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class CandidateVideo(TimestampMixin, Base):
    __tablename__ = "candidate_videos"

    external_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    creator_handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    creator_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    caption_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hashtags_json: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    publish_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    region_hint: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_media_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
    ingestion_source: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    assets: Mapped[list["VideoAsset"]] = relationship(back_populates="candidate_video", lazy="selectin")  # noqa: F821
    analysis: Mapped[Optional["VideoAnalysis"]] = relationship(back_populates="candidate_video", uselist=False, lazy="selectin")  # noqa: F821
    result_rankings: Mapped[list["ResultRanking"]] = relationship(back_populates="candidate_video", lazy="selectin")  # noqa: F821
    embeddings: Mapped[list["ContentEmbedding"]] = relationship(back_populates="candidate_video", lazy="selectin")  # noqa: F821
