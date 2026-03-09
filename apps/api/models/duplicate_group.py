from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.models.base import Base


class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(),
    )
    group_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    representative_candidate_video_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_videos.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
