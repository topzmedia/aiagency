from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base


class FeedbackLabel(str, enum.Enum):
    very_relevant = "very_relevant"
    somewhat_relevant = "somewhat_relevant"
    irrelevant = "irrelevant"


class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    search_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("searches.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidate_videos.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    label: Mapped[FeedbackLabel] = mapped_column(Enum(FeedbackLabel, name="feedback_label"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="feedbacks")  # noqa: F821
