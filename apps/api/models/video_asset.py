from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base


class AssetType(str, enum.Enum):
    video = "video"
    thumbnail = "thumbnail"
    audio = "audio"


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(),
    )
    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_videos.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType, name="asset_type"), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())

    candidate_video: Mapped["CandidateVideo"] = relationship(back_populates="assets")  # noqa: F821
