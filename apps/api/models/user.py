from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, unique=True, index=True)

    searches: Mapped[list["Search"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    feedbacks: Mapped[list["UserFeedback"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    collections: Mapped[list["Collection"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
