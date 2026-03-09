from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class Collection(TimestampMixin, Base):
    __tablename__ = "collections"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="collections")  # noqa: F821
    items: Mapped[list["CollectionItem"]] = relationship(
        back_populates="collection", lazy="selectin", cascade="all, delete-orphan",
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(),
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_videos.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())

    collection: Mapped["Collection"] = relationship(back_populates="items")
