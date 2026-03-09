"""Duplicate and near-duplicate detection / grouping service.

Candidates are compared across multiple signals to identify exact duplicates,
near-duplicates, and same-event footage.  Groups are persisted as
DuplicateGroup records in the database.
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-loaded optional dependency: imagehash + PIL
# ---------------------------------------------------------------------------
_imagehash = None
_Image = None


def _load_imagehash():
    global _imagehash, _Image
    if _imagehash is None:
        try:
            import imagehash  # type: ignore[import-untyped]
            from PIL import Image  # type: ignore[import-untyped]
            _imagehash = imagehash
            _Image = Image
        except ImportError:
            logger.warning("imagehash / Pillow not installed – perceptual hashing disabled")
    return _imagehash, _Image


# ---------------------------------------------------------------------------
# Enums / dataclasses
# ---------------------------------------------------------------------------

class DuplicateType(str, Enum):
    exact_duplicate = "exact_duplicate"
    near_duplicate = "near_duplicate"
    same_event = "same_event"


@dataclass
class DuplicatePair:
    video_id_a: uuid.UUID
    video_id_b: uuid.UUID
    duplicate_type: DuplicateType
    similarity_score: float
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicateGroup:
    group_id: uuid.UUID
    duplicate_type: DuplicateType
    member_ids: list[uuid.UUID] = field(default_factory=list)
    canonical_id: uuid.UUID | None = None


# ---------------------------------------------------------------------------
# Signal computations
# ---------------------------------------------------------------------------

def file_checksum(path: str | Path, algorithm: str = "sha256") -> str:
    """Compute a hex-digest checksum of the file at *path*."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        while chunk := fh.read(1 << 20):  # 1 MiB
            h.update(chunk)
    return h.hexdigest()


def perceptual_hash(thumbnail_path: str | Path) -> str | None:
    """Compute a perceptual hash string for a thumbnail image.

    Returns ``None`` if imagehash/Pillow are not available.
    """
    ih, Img = _load_imagehash()
    if ih is None or Img is None:
        return None
    try:
        img = Img.open(thumbnail_path)
        return str(ih.phash(img))
    except Exception:
        logger.exception("Perceptual hash failed for %s", thumbnail_path)
        return None


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """Hamming distance between two hex-encoded hashes of equal length."""
    if len(hash_a) != len(hash_b):
        return max(len(hash_a), len(hash_b)) * 4  # large penalty
    int_a = int(hash_a, 16)
    int_b = int(hash_b, 16)
    return bin(int_a ^ int_b).count("1")


def duration_similar(dur_a: float | None, dur_b: float | None, tolerance: float = 2.0) -> bool:
    """Return True if durations are within *tolerance* seconds."""
    if dur_a is None or dur_b is None:
        return False
    return abs(dur_a - dur_b) <= tolerance


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Jaccard index between two sets of strings."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def text_overlap(text_a: str | None, text_b: str | None) -> float:
    """Jaccard overlap on whitespace-tokenized text."""
    if not text_a or not text_b:
        return 0.0
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    return jaccard_similarity(tokens_a, tokens_b)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

@dataclass
class _CandidateSignals:
    """Internal structure holding all comparison signals for a candidate."""
    video_id: uuid.UUID
    checksum: str | None = None
    phash: str | None = None
    duration_sec: float | None = None
    embedding: np.ndarray | None = None
    ocr_text: str | None = None
    transcript_text: str | None = None


def classify_pair(a: _CandidateSignals, b: _CandidateSignals) -> DuplicatePair | None:
    """Compare two candidates and return a :class:`DuplicatePair` if they are
    duplicates of any type; otherwise return ``None``."""
    evidence: dict[str, Any] = {}

    # 1. Exact checksum match
    if a.checksum and b.checksum and a.checksum == b.checksum:
        evidence["checksum_match"] = True
        return DuplicatePair(
            video_id_a=a.video_id,
            video_id_b=b.video_id,
            duplicate_type=DuplicateType.exact_duplicate,
            similarity_score=1.0,
            evidence=evidence,
        )

    score_components: list[float] = []

    # 2. Perceptual hash
    if a.phash and b.phash:
        dist = hamming_distance(a.phash, b.phash)
        phash_sim = max(0.0, 1.0 - dist / 64.0)
        evidence["phash_similarity"] = round(phash_sim, 4)
        score_components.append(phash_sim)

    # 3. Duration similarity
    if a.duration_sec is not None and b.duration_sec is not None:
        dur_sim = 1.0 if duration_similar(a.duration_sec, b.duration_sec) else 0.0
        evidence["duration_similar"] = bool(dur_sim)
        score_components.append(dur_sim)

    # 4. Embedding cosine similarity
    if a.embedding is not None and b.embedding is not None:
        emb_sim = cosine_similarity(a.embedding, b.embedding)
        evidence["embedding_similarity"] = round(emb_sim, 4)
        score_components.append(emb_sim)

    # 5. OCR text overlap
    ocr_sim = text_overlap(a.ocr_text, b.ocr_text)
    if ocr_sim > 0:
        evidence["ocr_overlap"] = round(ocr_sim, 4)
    score_components.append(ocr_sim)

    # 6. Transcript overlap
    trans_sim = text_overlap(a.transcript_text, b.transcript_text)
    if trans_sim > 0:
        evidence["transcript_overlap"] = round(trans_sim, 4)
    score_components.append(trans_sim)

    if not score_components:
        return None

    avg_sim = sum(score_components) / len(score_components)

    if avg_sim >= 0.90:
        dup_type = DuplicateType.near_duplicate
    elif avg_sim >= 0.65:
        dup_type = DuplicateType.same_event
    else:
        return None

    return DuplicatePair(
        video_id_a=a.video_id,
        video_id_b=b.video_id,
        duplicate_type=dup_type,
        similarity_score=round(avg_sim, 4),
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------

def build_groups(pairs: list[DuplicatePair]) -> list[DuplicateGroup]:
    """Union-find grouping of duplicate pairs into :class:`DuplicateGroup` sets."""
    parent: dict[uuid.UUID, uuid.UUID] = {}

    def find(x: uuid.UUID) -> uuid.UUID:
        while parent.get(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: uuid.UUID, y: uuid.UUID) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # Track the strictest duplicate type per group root
    group_types: dict[uuid.UUID, DuplicateType] = {}
    type_rank = {DuplicateType.exact_duplicate: 0, DuplicateType.near_duplicate: 1, DuplicateType.same_event: 2}

    for pair in pairs:
        parent.setdefault(pair.video_id_a, pair.video_id_a)
        parent.setdefault(pair.video_id_b, pair.video_id_b)
        union(pair.video_id_a, pair.video_id_b)

    # Collect members per root
    clusters: dict[uuid.UUID, set[uuid.UUID]] = {}
    for vid in parent:
        root = find(vid)
        clusters.setdefault(root, set()).add(vid)

    # Determine group type from pairs
    for pair in pairs:
        root = find(pair.video_id_a)
        existing = group_types.get(root)
        if existing is None or type_rank[pair.duplicate_type] < type_rank[existing]:
            group_types[root] = pair.duplicate_type

    groups: list[DuplicateGroup] = []
    for root, members in clusters.items():
        groups.append(DuplicateGroup(
            group_id=uuid.uuid4(),
            duplicate_type=group_types.get(root, DuplicateType.same_event),
            member_ids=sorted(members, key=str),
            canonical_id=root,
        ))

    return groups


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def find_duplicates(
    candidates: Sequence[dict[str, Any]],
) -> list[DuplicateGroup]:
    """Detect duplicates among a list of candidate dicts.

    Each dict should contain keys: ``id``, and optionally ``checksum``,
    ``phash``, ``duration_sec``, ``embedding`` (numpy array), ``ocr_text``,
    ``transcript_text``.
    """
    signals = []
    for c in candidates:
        sig = _CandidateSignals(
            video_id=c["id"],
            checksum=c.get("checksum"),
            phash=c.get("phash"),
            duration_sec=c.get("duration_sec"),
            embedding=c.get("embedding"),
            ocr_text=c.get("ocr_text"),
            transcript_text=c.get("transcript_text"),
        )
        signals.append(sig)

    pairs: list[DuplicatePair] = []
    for i in range(len(signals)):
        for j in range(i + 1, len(signals)):
            pair = classify_pair(signals[i], signals[j])
            if pair is not None:
                pairs.append(pair)

    groups = build_groups(pairs)
    logger.info("Deduplication: %d candidates -> %d pairs -> %d groups",
                len(candidates), len(pairs), len(groups))
    return groups
