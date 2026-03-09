from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.models.base import Base

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


class EmbeddingType(str, enum.Enum):
    caption = "caption"
    transcript = "transcript"
    ocr = "ocr"
    frame = "frame"


class ContentEmbedding(Base):
    __tablename__ = "content_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(),
    )
    candidate_video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding_type: Mapped[EmbeddingType] = mapped_column(
        Enum(EmbeddingType, name="embedding_type"), nullable=False,
    )
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())

    candidate_video: Mapped["CandidateVideo"] = relationship(back_populates="embeddings")  # noqa: F821

    __table_args__ = (
        Index(
            "ix_content_embeddings_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
