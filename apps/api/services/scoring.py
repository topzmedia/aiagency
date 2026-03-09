"""Weighted scoring engine for candidate video ranking.

Each candidate is scored across multiple similarity / detection dimensions.
Scores are normalized to [0, 1], combined via configurable weights, and
accompanied by human-readable reason codes describing *why* the video matched.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default weights – MUST sum to 1.0
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "caption_similarity": 0.12,
    "hashtag_similarity": 0.08,
    "ocr_similarity": 0.12,
    "transcript_similarity": 0.15,
    "visual_object_score": 0.18,
    "visual_scene_score": 0.12,
    "action_event_score": 0.18,
    "audio_event_score": 0.05,
    "quality_score": 0.05,
}

# Sanity check
assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

# ---------------------------------------------------------------------------
# Reason code templates
# ---------------------------------------------------------------------------

_REASON_TEMPLATES: dict[str, str] = {
    "caption_similarity": "matched_caption_text",
    "hashtag_similarity": "matched_hashtag",
    "ocr_similarity": "matched_ocr_text",
    "transcript_similarity": "matched_transcript_text",
    "visual_object_score": "matched_{label}_visual",
    "visual_scene_score": "matched_{label}_scene",
    "action_event_score": "matched_{label}_action",
    "audio_event_score": "matched_{label}_audio",
    "quality_score": "quality_acceptable",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MatchedSegment:
    """Describes a temporal segment of the video that contributed to a score."""
    start_sec: float
    end_sec: float
    dimension: str
    label: str
    score: float


@dataclass
class ScoreBreakdown:
    """Per-dimension score detail."""
    dimension: str
    raw_score: float
    weight: float
    weighted_score: float


@dataclass
class ScoreResult:
    """Final scoring outcome for a single candidate video."""
    final_score: float
    accepted: bool
    breakdown: list[ScoreBreakdown] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    matched_segments: list[MatchedSegment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_score": round(self.final_score, 6),
            "accepted": self.accepted,
            "breakdown": [
                {
                    "dimension": b.dimension,
                    "raw_score": round(b.raw_score, 6),
                    "weight": b.weight,
                    "weighted_score": round(b.weighted_score, 6),
                }
                for b in self.breakdown
            ],
            "reason_codes": self.reason_codes,
            "matched_segments": [
                {
                    "start_sec": s.start_sec,
                    "end_sec": s.end_sec,
                    "dimension": s.dimension,
                    "label": s.label,
                    "score": round(s.score, 6),
                }
                for s in self.matched_segments
            ],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _generate_reason_codes(
    dimension: str,
    raw_score: float,
    labels: list[str] | None = None,
    threshold: float = 0.15,
) -> list[str]:
    """Produce human-readable reason codes for a dimension if its score
    exceeds *threshold*."""
    if raw_score < threshold:
        return []
    template = _REASON_TEMPLATES.get(dimension, dimension)
    if "{label}" in template and labels:
        return [template.format(label=lbl) for lbl in labels]
    if "{label}" not in template:
        return [template]
    return [dimension]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_score(
    scores: dict[str, float],
    penalties: float = 0.0,
    confidence_threshold: float = 0.30,
    weights: dict[str, float] | None = None,
    labels: dict[str, list[str]] | None = None,
    segments: list[MatchedSegment] | None = None,
) -> ScoreResult:
    """Compute a weighted aggregate score for one candidate video.

    Parameters
    ----------
    scores:
        Mapping of dimension name to a raw score in [0, 1].
    penalties:
        An optional penalty subtracted from the final score (e.g. for
        duplicates or policy violations).  Value should be >= 0.
    confidence_threshold:
        Minimum final score for the candidate to be accepted.
    weights:
        Override the default weight map.  Keys must match *scores*.
    labels:
        Optional mapping of dimension -> list of matched labels (used for
        generating richer reason codes, e.g. ``{"visual_object_score": ["car", "truck"]}``).
    segments:
        Pre-computed matched segments to attach to the result.
    """
    w = weights or DEFAULT_WEIGHTS
    labels = labels or {}
    segments = segments or []

    breakdown: list[ScoreBreakdown] = []
    reason_codes: list[str] = []
    weighted_sum = 0.0

    for dim, weight in w.items():
        raw = _clamp(scores.get(dim, 0.0))
        ws = raw * weight
        weighted_sum += ws
        breakdown.append(ScoreBreakdown(
            dimension=dim,
            raw_score=raw,
            weight=weight,
            weighted_score=ws,
        ))
        codes = _generate_reason_codes(dim, raw, labels.get(dim))
        reason_codes.extend(codes)

    final = _clamp(weighted_sum - _clamp(penalties, 0.0, 1.0))
    accepted = final >= confidence_threshold

    result = ScoreResult(
        final_score=final,
        accepted=accepted,
        breakdown=breakdown,
        reason_codes=sorted(set(reason_codes)),
        matched_segments=segments,
    )

    logger.debug("Score=%.4f accepted=%s reasons=%s", final, accepted, result.reason_codes)
    return result
