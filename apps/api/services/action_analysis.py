"""Action / event analysis service.

Combines temporal heuristics, transcript matching, OCR matching, and object
co-occurrence to identify actions and events in video segments.
"""
from __future__ import annotations

import abc
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from apps.api.services.scene_segmentation import SceneSegment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ActionEvent:
    """A detected action or event within a video."""
    label: str
    confidence: float
    start_sec: float | None = None
    end_sec: float | None = None
    evidence: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Label set and rules
# ---------------------------------------------------------------------------

ACTION_LABELS = [
    "collision",
    "smiling_together",
    "arguing",
    "roof_inspection",
    "dog_playing",
    "driving",
    "aftermath_only",
    "cooking",
    "walking",
    "sports",
    "celebration",
]

# Keyword patterns per action label
_ACTION_KEYWORD_RULES: dict[str, dict[str, Any]] = {
    "collision": {
        "transcript_keywords": ["crash", "hit", "accident", "collision", "wreck", "impact", "smash"],
        "ocr_keywords": ["crash", "accident", "collision", "impact", "dashcam"],
        "object_cooccurrence": [("car", "car"), ("car", "truck"), ("truck", "truck")],
        "object_singles": ["car", "truck"],
        "base_confidence": 0.2,
    },
    "smiling_together": {
        "transcript_keywords": ["smile", "happy", "laugh", "love", "together", "family"],
        "ocr_keywords": ["smile", "happy", "family", "love"],
        "object_cooccurrence": [("person", "person")],
        "object_singles": ["person"],
        "base_confidence": 0.15,
    },
    "arguing": {
        "transcript_keywords": ["argue", "fight", "yell", "scream", "shut up", "angry",
                                 "confrontation", "dispute"],
        "ocr_keywords": ["fight", "argument", "confrontation"],
        "object_cooccurrence": [("person", "person")],
        "object_singles": ["person"],
        "base_confidence": 0.15,
    },
    "roof_inspection": {
        "transcript_keywords": ["roof", "shingle", "damage", "repair", "inspect", "gutter",
                                 "leak", "hail"],
        "ocr_keywords": ["roof", "damage", "inspection", "repair", "shingle"],
        "object_cooccurrence": [],
        "object_singles": ["roof", "house"],
        "base_confidence": 0.15,
    },
    "dog_playing": {
        "transcript_keywords": ["dog", "puppy", "fetch", "play", "good boy", "good girl",
                                 "bark", "walk"],
        "ocr_keywords": ["dog", "puppy", "pet"],
        "object_cooccurrence": [],
        "object_singles": ["dog"],
        "base_confidence": 0.2,
    },
    "driving": {
        "transcript_keywords": ["drive", "driving", "road", "highway", "traffic", "lane",
                                 "speed"],
        "ocr_keywords": ["mph", "speed", "highway", "exit"],
        "object_cooccurrence": [("car", "road"), ("truck", "road")],
        "object_singles": ["car", "road"],
        "base_confidence": 0.2,
    },
    "aftermath_only": {
        "transcript_keywords": ["aftermath", "damage", "wreckage", "scene", "destroyed"],
        "ocr_keywords": ["damage", "aftermath", "destroyed"],
        "object_cooccurrence": [],
        "object_singles": ["car"],
        "base_confidence": 0.1,
    },
    "cooking": {
        "transcript_keywords": ["cook", "recipe", "stir", "bake", "fry", "chop", "ingredient",
                                 "kitchen"],
        "ocr_keywords": ["recipe", "cook", "kitchen", "chef", "ingredient"],
        "object_cooccurrence": [],
        "object_singles": ["kitchen", "table"],
        "base_confidence": 0.15,
    },
    "walking": {
        "transcript_keywords": ["walk", "hike", "stroll", "path", "trail"],
        "ocr_keywords": ["trail", "walk", "path"],
        "object_cooccurrence": [],
        "object_singles": ["person", "tree", "road"],
        "base_confidence": 0.1,
    },
    "sports": {
        "transcript_keywords": ["goal", "score", "team", "game", "play", "match", "win",
                                 "run", "throw", "catch"],
        "ocr_keywords": ["score", "team", "game", "goal"],
        "object_cooccurrence": [("person", "person")],
        "object_singles": ["person"],
        "base_confidence": 0.1,
    },
    "celebration": {
        "transcript_keywords": ["celebrate", "party", "cheer", "congratulations", "birthday",
                                 "wedding", "toast"],
        "ocr_keywords": ["congratulations", "celebrate", "happy birthday", "cheers"],
        "object_cooccurrence": [("person", "person")],
        "object_singles": ["person"],
        "base_confidence": 0.1,
    },
}


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class ActionAnalyzer(abc.ABC):
    """Abstract action analysis interface."""

    @abc.abstractmethod
    def analyze(
        self,
        scenes: list[SceneSegment],
        objects: list[str],
        transcript: str,
        ocr_text: str,
        audio_events: list[str] | None = None,
    ) -> list[ActionEvent]:
        """Analyze video content to detect actions/events."""
        ...


# ---------------------------------------------------------------------------
# Rule-based MVP implementation
# ---------------------------------------------------------------------------

class RuleBasedActionAnalyzer(ActionAnalyzer):
    """Action analyser using keyword and co-occurrence rules."""

    def __init__(self, min_confidence: float = 0.20):
        self._min_confidence = min_confidence

    def analyze(
        self,
        scenes: list[SceneSegment],
        objects: list[str],
        transcript: str,
        ocr_text: str,
        audio_events: list[str] | None = None,
    ) -> list[ActionEvent]:
        transcript_lower = transcript.lower()
        ocr_lower = ocr_text.lower()
        object_set = {o.lower() for o in objects}
        audio_set = {a.lower() for a in (audio_events or [])}

        results: list[ActionEvent] = []

        for label, rule in _ACTION_KEYWORD_RULES.items():
            confidence = rule["base_confidence"]
            evidence: list[str] = []

            # Transcript keyword matches
            t_matches = [kw for kw in rule["transcript_keywords"]
                         if re.search(r'\b' + re.escape(kw) + r'\b', transcript_lower)]
            if t_matches:
                confidence += min(0.30, len(t_matches) * 0.08)
                evidence.append(f"transcript_keywords: {t_matches}")

            # OCR keyword matches
            o_matches = [kw for kw in rule["ocr_keywords"] if kw in ocr_lower]
            if o_matches:
                confidence += min(0.20, len(o_matches) * 0.07)
                evidence.append(f"ocr_keywords: {o_matches}")

            # Object co-occurrence
            for pair in rule.get("object_cooccurrence", []):
                if pair[0] in object_set and pair[1] in object_set:
                    confidence += 0.12
                    evidence.append(f"object_pair: {pair}")
                    break

            # Single object presence
            obj_hits = [o for o in rule.get("object_singles", []) if o in object_set]
            if obj_hits:
                confidence += min(0.15, len(obj_hits) * 0.06)
                evidence.append(f"objects: {obj_hits}")

            # Audio event boost
            audio_boosts = {
                "collision": ["impact", "screech"],
                "arguing": ["speech"],
                "dog_playing": ["bark"],
                "celebration": ["cheering", "music"],
            }
            if label in audio_boosts:
                matching_audio = audio_set & set(audio_boosts[label])
                if matching_audio:
                    confidence += 0.10
                    evidence.append(f"audio_events: {list(matching_audio)}")

            confidence = max(0.0, min(1.0, confidence))

            if confidence >= self._min_confidence:
                # Assign time span from scenes if available
                start = scenes[0].start_sec if scenes else None
                end = scenes[-1].end_sec if scenes else None

                results.append(ActionEvent(
                    label=label,
                    confidence=round(confidence, 3),
                    start_sec=start,
                    end_sec=end,
                    evidence=evidence,
                ))

        results.sort(key=lambda a: a.confidence, reverse=True)
        return results


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_action_analyzer(analyzer_name: str = "rule_based") -> ActionAnalyzer:
    """Factory to obtain an action analyzer by name."""
    if analyzer_name == "rule_based":
        return RuleBasedActionAnalyzer()
    raise ValueError(f"Unknown action analyzer: {analyzer_name}")
