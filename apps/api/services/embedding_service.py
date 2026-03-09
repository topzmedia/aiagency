"""Embedding service using sentence-transformers.

Provides text embedding generation, cosine similarity computation, and
integration with pgvector for storage / retrieval.  The model is loaded
lazily as a singleton to avoid startup overhead.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton model holder
# ---------------------------------------------------------------------------

_model_instance = None
_model_name: str | None = None


def _get_model(model_name: str = "all-MiniLM-L6-v2"):
    """Lazy-load the sentence-transformers model (singleton)."""
    global _model_instance, _model_name
    if _model_instance is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]
            _model_instance = SentenceTransformer(model_name)
            _model_name = model_name
            logger.info("Loaded embedding model: %s", model_name)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is required for the embedding service. "
                "Install with: pip install sentence-transformers"
            )
    return _model_instance


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


def embed_text(text: str, model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    """Embed a single text string.

    Returns a numpy array of shape ``(384,)`` for the default model.
    """
    model = _get_model(model_name)
    vec = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
    return np.asarray(vec, dtype=np.float32)


def embed_texts(texts: list[str], model_name: str = "all-MiniLM-L6-v2") -> list[np.ndarray]:
    """Embed multiple texts in a batch.

    Returns a list of numpy arrays, one per input text.
    """
    if not texts:
        return []
    model = _get_model(model_name)
    vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
    return [np.asarray(v, dtype=np.float32) for v in vecs]


def compute_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors."""
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


# ---------------------------------------------------------------------------
# Async DB helpers (pgvector integration)
# ---------------------------------------------------------------------------

async def store_embedding(
    session: Any,
    candidate_video_id: Any,
    embedding_type: str,
    vector: np.ndarray,
    source_text: str | None = None,
) -> None:
    """Store an embedding vector in the content_embeddings table.

    Parameters
    ----------
    session:
        An async SQLAlchemy session.
    candidate_video_id:
        UUID of the candidate video.
    embedding_type:
        Type label (e.g. ``caption``, ``transcript``, ``ocr``).
    vector:
        The embedding numpy array.
    source_text:
        The original text that was embedded (stored for debugging).
    """
    from sqlalchemy import text as sa_text

    vec_list = vector.tolist()
    await session.execute(
        sa_text(
            "INSERT INTO content_embeddings "
            "(candidate_video_id, embedding_type, embedding, source_text) "
            "VALUES (:vid, :etype, :emb, :src) "
            "ON CONFLICT (candidate_video_id, embedding_type) "
            "DO UPDATE SET embedding = EXCLUDED.embedding, source_text = EXCLUDED.source_text"
        ),
        {
            "vid": str(candidate_video_id),
            "etype": embedding_type,
            "emb": str(vec_list),
            "src": source_text,
        },
    )
    logger.debug("Stored %s embedding for %s", embedding_type, candidate_video_id)


async def find_similar(
    session: Any,
    query_vector: np.ndarray,
    embedding_type: str | None = None,
    limit: int = 50,
    min_similarity: float = 0.3,
) -> list[dict[str, Any]]:
    """Find candidate videos with similar embeddings using pgvector.

    Parameters
    ----------
    session:
        An async SQLAlchemy session.
    query_vector:
        The query embedding vector.
    embedding_type:
        Optional filter to a specific embedding type.
    limit:
        Maximum number of results.
    min_similarity:
        Minimum cosine similarity threshold.

    Returns
    -------
    List of dicts with ``candidate_video_id`` and ``similarity``.
    """
    from sqlalchemy import text as sa_text

    vec_str = str(query_vector.tolist())

    type_clause = ""
    params: dict[str, Any] = {
        "vec": vec_str,
        "limit": limit,
        "min_sim": min_similarity,
    }

    if embedding_type:
        type_clause = "AND embedding_type = :etype"
        params["etype"] = embedding_type

    query = sa_text(f"""
        SELECT candidate_video_id,
               1 - (embedding <=> :vec::vector) AS similarity
        FROM content_embeddings
        WHERE 1 = 1 {type_clause}
        ORDER BY embedding <=> :vec::vector
        LIMIT :limit
    """)

    result = await session.execute(query, params)
    rows = result.fetchall()

    return [
        {"candidate_video_id": row[0], "similarity": round(float(row[1]), 6)}
        for row in rows
        if float(row[1]) >= min_similarity
    ]
