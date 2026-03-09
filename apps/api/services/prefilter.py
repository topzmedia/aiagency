"""Cheap prefilter stage.

Performs fast, low-cost filtering and ranking of candidate videos before
expensive deep analysis.  Uses metadata filters, keyword matching, and
optionally embedding similarity.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import numpy as np

from apps.api.services.query_interpreter import ParsedQuery

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PrefilterCandidate:
    """A candidate video with metadata for prefiltering."""
    id: Any  # UUID
    platform: str | None = None
    region_hint: str | None = None
    language: str | None = None
    publish_date: date | datetime | None = None
    duration_sec: float | None = None
    caption_text: str | None = None
    hashtags: list[str] | None = None
    embedding: np.ndarray | None = None


@dataclass
class PrefilterResult:
    """Result of the prefilter stage."""
    candidate_id: Any
    cheap_score: float
    match_reasons: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

def _matches_platform(candidate: PrefilterCandidate, platforms: list[str] | None) -> bool:
    if not platforms:
        return True
    if not candidate.platform:
        return True  # allow unknown platforms through
    return candidate.platform.lower() in [p.lower() for p in platforms]


def _matches_region(candidate: PrefilterCandidate, region: str | None) -> bool:
    if not region:
        return True
    if not candidate.region_hint:
        return True
    return candidate.region_hint.lower() == region.lower()


def _matches_language(candidate: PrefilterCandidate, language: str | None) -> bool:
    if not language:
        return True
    if not candidate.language:
        return True
    return candidate.language.lower().startswith(language.lower())


def _matches_date_range(
    candidate: PrefilterCandidate,
    date_from: date | None,
    date_to: date | None,
) -> bool:
    if not date_from and not date_to:
        return True
    if not candidate.publish_date:
        return True  # let it through if no date info

    pub = candidate.publish_date
    if isinstance(pub, datetime):
        pub = pub.date()

    if date_from and pub < date_from:
        return False
    if date_to and pub > date_to:
        return False
    return True


def _matches_duration(
    candidate: PrefilterCandidate,
    min_dur: float | None = None,
    max_dur: float | None = None,
) -> bool:
    if min_dur is None and max_dur is None:
        return True
    if candidate.duration_sec is None:
        return True
    if min_dur is not None and candidate.duration_sec < min_dur:
        return False
    if max_dur is not None and candidate.duration_sec > max_dur:
        return False
    return True


# ---------------------------------------------------------------------------
# Keyword scoring
# ---------------------------------------------------------------------------

def _keyword_score(
    candidate: PrefilterCandidate,
    parsed_query: ParsedQuery,
) -> tuple[float, list[str]]:
    """Score a candidate based on keyword overlap with caption and hashtags.

    Returns (score, reasons).
    """
    score = 0.0
    reasons: list[str] = []

    search_terms = set(parsed_query.entities + parsed_query.actions + parsed_query.synonyms)
    if not search_terms:
        # Fall back to raw query tokens
        search_terms = set(re.findall(r"[a-z0-9]+", parsed_query.raw_query.lower()))

    # Caption matching
    if candidate.caption_text:
        caption_lower = candidate.caption_text.lower()
        caption_hits = [t for t in search_terms if t in caption_lower]
        if caption_hits:
            caption_score = min(1.0, len(caption_hits) / max(len(search_terms), 1))
            score += caption_score * 0.5
            reasons.append(f"caption_match({len(caption_hits)} terms)")

    # Hashtag matching
    if candidate.hashtags:
        hashtag_set = {h.lower().lstrip("#") for h in candidate.hashtags}
        hashtag_hits = search_terms & hashtag_set
        if hashtag_hits:
            hashtag_score = min(1.0, len(hashtag_hits) / max(len(search_terms), 1))
            score += hashtag_score * 0.3
            reasons.append(f"hashtag_match({len(hashtag_hits)} tags)")

    # Exclude penalty
    if parsed_query.exclude and candidate.caption_text:
        caption_lower = candidate.caption_text.lower()
        exclude_hits = [t for t in parsed_query.exclude if t.lower() in caption_lower]
        if exclude_hits:
            score -= 0.3 * len(exclude_hits)
            reasons.append(f"exclude_penalty({exclude_hits})")

    return max(0.0, min(1.0, score)), reasons


# ---------------------------------------------------------------------------
# Embedding scoring
# ---------------------------------------------------------------------------

def _embedding_score(
    candidate: PrefilterCandidate,
    query_embedding: np.ndarray | None,
) -> tuple[float, list[str]]:
    """Score based on embedding cosine similarity."""
    if query_embedding is None or candidate.embedding is None:
        return 0.0, []

    from apps.api.services.embedding_service import compute_similarity
    sim = compute_similarity(query_embedding, candidate.embedding)
    if sim > 0.3:
        return sim * 0.2, [f"embedding_sim({sim:.3f})"]
    return 0.0, []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prefilter(
    parsed_query: ParsedQuery,
    candidates: list[PrefilterCandidate],
    platforms: list[str] | None = None,
    region: str | None = None,
    language: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_duration: float | None = None,
    max_duration: float | None = None,
    query_embedding: np.ndarray | None = None,
    top_n: int = 200,
) -> list[PrefilterResult]:
    """Run cheap prefiltering on a candidate pool.

    Parameters
    ----------
    parsed_query:
        The structured parsed query.
    candidates:
        List of candidate video metadata.
    platforms / region / language / date_from / date_to:
        Metadata filters.
    min_duration / max_duration:
        Duration range filter in seconds.
    query_embedding:
        Optional precomputed query embedding for similarity scoring.
    top_n:
        Maximum number of candidates to return.

    Returns
    -------
    Filtered and ranked list of :class:`PrefilterResult`, limited to *top_n*.
    """
    results: list[PrefilterResult] = []

    for cand in candidates:
        # Hard filters
        if not _matches_platform(cand, platforms):
            continue
        if not _matches_region(cand, region):
            continue
        if not _matches_language(cand, language):
            continue
        if not _matches_date_range(cand, date_from, date_to):
            continue
        if not _matches_duration(cand, min_duration, max_duration):
            continue

        # Cheap scoring
        kw_score, kw_reasons = _keyword_score(cand, parsed_query)
        emb_score, emb_reasons = _embedding_score(cand, query_embedding)

        total_score = kw_score + emb_score
        reasons = kw_reasons + emb_reasons

        results.append(PrefilterResult(
            candidate_id=cand.id,
            cheap_score=round(total_score, 6),
            match_reasons=reasons,
        ))

    # Sort by score descending, take top N
    results.sort(key=lambda r: r.cheap_score, reverse=True)
    results = results[:top_n]

    logger.info(
        "Prefilter: %d candidates -> %d after filters (top %d)",
        len(candidates), len(results), top_n,
    )
    return results
