"""
Scoring Agent — heuristic scoring for ranking creative variants.

Scores are 0-10 and are designed as interpretable feature extractors.
See FUTURE_SCORING_INTERFACE_NOTE for the ML upgrade path.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.enums import VideoLength
from ..models.schemas import AvatarMetadata, CreativeVariant, Hook, Script, ScriptVariant
from ..utils.config import AppConfig
from ..utils.logging_utils import get_module_logger

logger = get_module_logger("scoring_agent")

# ---------------------------------------------------------------------------
# Ideal word counts per video length
# ---------------------------------------------------------------------------

_IDEAL_WORD_COUNTS: Dict[str, int] = {
    VideoLength.SHORT:  47,    # Midpoint of 40-55 words
    VideoLength.MEDIUM: 100,   # Midpoint of 80-120 words
    VideoLength.LONG:   140,   # Midpoint of 120-160 words
}
_DEFAULT_IDEAL_WORDS = 100

# ---------------------------------------------------------------------------
# ML upgrade note
# ---------------------------------------------------------------------------

FUTURE_SCORING_INTERFACE_NOTE = (
    "Implement ML-based CTR prediction by replacing score_creative() with a model "
    "that takes feature vectors. Current heuristics are designed as interpretable "
    "feature extractors."
)


class ScoringAgent:
    """Heuristic scoring and ranking for creative variants."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Single creative scorer
    # ------------------------------------------------------------------

    def score_creative(
        self,
        creative: CreativeVariant,
        hook: Optional[Hook] = None,
        script: Optional[Union[Script, ScriptVariant]] = None,
        avatar: Optional[AvatarMetadata] = None,
    ) -> float:
        """
        Score a single creative variant on a 0-10 scale.

        Scoring components
        ------------------
        a) hook_strength_score   hook.strength_score / 10 * 3.0   (max 3.0 pts)
        b) has_captions          +1.5 if caption_id is set
        c) avatar_realism        avatar.realism_score / 10 * 2.0  (max 2.0 pts)
        d) script_concision      +1.5 within 20% of ideal word count
                                 +1.0 within 40%
                                 +0.5 otherwise
        e) render_completeness   +1.0 if file exists, has_audio, correct dims, no QA issues
        f) has_broll             +0.5 if broll_ids not empty
        g) has_cta_overlay       +0.5 always (CTA card assumed present)

        Total is capped at 10.0.
        """
        score = 0.0

        # (a) Hook strength — up to 3.0 points
        if hook is not None:
            hook_score = max(0.0, min(10.0, float(hook.strength_score)))
            score += (hook_score / 10.0) * 3.0
        else:
            # Partial credit if no hook object available
            score += 1.5

        # (b) Captions — binary +1.5
        if creative.caption_id:
            score += 1.5

        # (c) Avatar realism — up to 2.0 points
        if avatar is not None:
            realism = max(0.0, min(10.0, float(avatar.realism_score)))
            score += (realism / 10.0) * 2.0
        else:
            # Partial credit when no avatar metadata available
            score += 1.0

        # (d) Script concision — up to 1.5 points
        word_count = _get_word_count(script, creative)
        ideal_words = _get_ideal_word_count(script)
        if word_count > 0 and ideal_words > 0:
            ratio = abs(word_count - ideal_words) / ideal_words
            if ratio <= 0.20:
                score += 1.5
            elif ratio <= 0.40:
                score += 1.0
            else:
                score += 0.5
        else:
            score += 0.5  # No script data; minimal credit

        # (e) Render completeness — up to 1.0 point
        render_score = 0.0
        if creative.file_path and Path(creative.file_path).exists():
            render_score += 0.4
        if creative.qa_passed:
            render_score += 0.3
        if not creative.qa_notes:
            render_score += 0.3
        score += render_score

        # (f) Has B-roll — +0.5
        if creative.broll_ids:
            score += 0.5

        # (g) CTA overlay — +0.5 always
        score += 0.5

        final = min(10.0, round(score, 3))
        return final

    # ------------------------------------------------------------------
    # Batch scorer
    # ------------------------------------------------------------------

    def score_batch(
        self,
        creatives: List[CreativeVariant],
        lookup: Dict,
    ) -> List[CreativeVariant]:
        """
        Score all creatives and return them sorted by score descending.

        Args:
            creatives: List of CreativeVariant to score.
            lookup: Dict with optional keys:
                - "hooks":   {hook_id: Hook}
                - "scripts": {script_id: Script or ScriptVariant}
                - "avatars": {avatar_id: AvatarMetadata}

        Updates creative.score in-place. Returns sorted list.
        """
        hooks_map: Dict[str, Hook] = lookup.get("hooks", {})
        scripts_map: Dict[str, Union[Script, ScriptVariant]] = lookup.get("scripts", {})
        avatars_map: Dict[str, AvatarMetadata] = lookup.get("avatars", {})

        for creative in creatives:
            hook = hooks_map.get(creative.hook_id) if creative.hook_id else None
            script = (
                scripts_map.get(creative.script_id)
                if creative.script_id else None
            )
            if script is None and creative.script_variant_id:
                script = scripts_map.get(creative.script_variant_id)
            avatar = avatars_map.get(creative.avatar_id) if creative.avatar_id else None

            creative.score = self.score_creative(
                creative=creative,
                hook=hook,
                script=script,
                avatar=avatar,
            )

        creatives.sort(key=lambda c: c.score, reverse=True)

        if creatives:
            logger.info(
                "ScoringAgent: scored %d creatives | top=%.2f mean=%.2f bottom=%.2f",
                len(creatives),
                creatives[0].score,
                sum(c.score for c in creatives) / len(creatives),
                creatives[-1].score,
            )

        return creatives

    # ------------------------------------------------------------------
    # Top-N selector
    # ------------------------------------------------------------------

    def get_top_n(
        self,
        creatives: List[CreativeVariant],
        n: int,
    ) -> List[CreativeVariant]:
        """Return top N creatives sorted by score descending."""
        if not creatives:
            return []
        sorted_creatives = sorted(creatives, key=lambda c: c.score, reverse=True)
        top = sorted_creatives[:n]
        logger.info(
            "ScoringAgent.get_top_n: returning %d/%d creatives",
            len(top),
            len(creatives),
        )
        return top


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_word_count(
    script: Optional[Union[Script, ScriptVariant]],
    creative: CreativeVariant,
) -> int:
    """Extract word count from the script object if available."""
    if script is None:
        return 0
    if hasattr(script, "word_count") and script.word_count:
        return int(script.word_count)
    if hasattr(script, "full_text") and script.full_text:
        return len(script.full_text.split())
    return 0


def _get_ideal_word_count(script: Optional[Union[Script, ScriptVariant]]) -> int:
    """Return the ideal word count for the script's VideoLength."""
    if script is None:
        return _DEFAULT_IDEAL_WORDS
    length = getattr(script, "length", None)
    if length is None:
        return _DEFAULT_IDEAL_WORDS
    length_val = length.value if hasattr(length, "value") else str(length)
    return _IDEAL_WORD_COUNTS.get(length_val, _DEFAULT_IDEAL_WORDS)
