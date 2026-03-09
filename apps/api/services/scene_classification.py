"""Scene classification service.

Classifies video frames into semantic scene categories using a rule-based
approach that combines detected objects, OCR text, and basic image features.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SceneLabel:
    """A scene classification result."""
    label: str
    confidence: float


# ---------------------------------------------------------------------------
# Scene label definitions and rules
# ---------------------------------------------------------------------------

SCENE_LABELS = [
    "indoor_kitchen",
    "road_highway",
    "suburban_exterior",
    "office",
    "store",
    "restaurant",
    "snow_outdoors",
    "residential_interior",
    "outdoor_urban",
    "outdoor_rural",
    "construction_site",
]

# Rules: each rule maps a scene label to object/OCR indicators and weights
_SCENE_RULES: dict[str, dict[str, Any]] = {
    "indoor_kitchen": {
        "object_indicators": ["kitchen", "table", "countertop"],
        "ocr_indicators": ["kitchen", "recipe", "cook", "chef", "menu"],
        "anti_indicators": ["road", "sky", "tree"],
        "base_confidence": 0.3,
    },
    "road_highway": {
        "object_indicators": ["car", "truck", "road"],
        "ocr_indicators": ["mph", "speed", "exit", "highway", "lane"],
        "anti_indicators": ["kitchen", "table"],
        "base_confidence": 0.3,
    },
    "suburban_exterior": {
        "object_indicators": ["house", "roof", "tree"],
        "ocr_indicators": ["address", "street", "ave", "dr", "ln"],
        "anti_indicators": ["road", "car"],
        "base_confidence": 0.25,
    },
    "office": {
        "object_indicators": ["table", "phone"],
        "ocr_indicators": ["meeting", "office", "desk", "memo", "email"],
        "anti_indicators": ["road", "tree", "sky", "kitchen"],
        "base_confidence": 0.2,
    },
    "store": {
        "object_indicators": ["person", "building"],
        "ocr_indicators": ["sale", "price", "$", "buy", "shop", "store"],
        "anti_indicators": ["kitchen", "road"],
        "base_confidence": 0.2,
    },
    "restaurant": {
        "object_indicators": ["table", "person"],
        "ocr_indicators": ["menu", "restaurant", "waiter", "dine", "food"],
        "anti_indicators": ["road", "car"],
        "base_confidence": 0.2,
    },
    "snow_outdoors": {
        "object_indicators": ["sky", "tree", "water"],
        "ocr_indicators": ["snow", "winter", "ice", "cold", "freeze"],
        "anti_indicators": ["kitchen", "table"],
        "base_confidence": 0.25,
    },
    "residential_interior": {
        "object_indicators": ["table", "person"],
        "ocr_indicators": ["home", "family", "living", "room", "couch"],
        "anti_indicators": ["road", "sky", "car"],
        "base_confidence": 0.2,
    },
    "outdoor_urban": {
        "object_indicators": ["building", "car", "person", "road"],
        "ocr_indicators": ["city", "street", "downtown", "urban"],
        "anti_indicators": ["kitchen", "table"],
        "base_confidence": 0.25,
    },
    "outdoor_rural": {
        "object_indicators": ["tree", "sky"],
        "ocr_indicators": ["farm", "field", "rural", "country", "barn"],
        "anti_indicators": ["building", "car", "road"],
        "base_confidence": 0.2,
    },
    "construction_site": {
        "object_indicators": ["building", "person"],
        "ocr_indicators": ["caution", "danger", "hard hat", "construction", "site"],
        "anti_indicators": ["kitchen", "table", "restaurant"],
        "base_confidence": 0.2,
    },
}


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class SceneClassifier(abc.ABC):
    """Abstract scene classification interface."""

    @abc.abstractmethod
    def classify(
        self,
        image_path: str | Path,
        objects: list[str] | None = None,
        ocr_text: str | None = None,
    ) -> list[SceneLabel]:
        """Classify the scene in an image.

        Parameters
        ----------
        image_path:
            Path to the image frame.
        objects:
            List of detected object labels for this frame.
        ocr_text:
            Concatenated OCR text detected in this frame.
        """
        ...


# ---------------------------------------------------------------------------
# Rule-based MVP implementation
# ---------------------------------------------------------------------------

class RuleBasedSceneClassifier(SceneClassifier):
    """Scene classifier that uses object detection labels and OCR text to
    assign scene labels via configurable rules."""

    def __init__(self, min_confidence: float = 0.25):
        self._min_confidence = min_confidence

    def classify(
        self,
        image_path: str | Path,
        objects: list[str] | None = None,
        ocr_text: str | None = None,
    ) -> list[SceneLabel]:
        objects = [o.lower() for o in (objects or [])]
        ocr_lower = (ocr_text or "").lower()
        object_set = set(objects)

        results: list[SceneLabel] = []

        for label, rule in _SCENE_RULES.items():
            confidence = rule["base_confidence"]

            # Boost from object indicators
            obj_matches = object_set & set(rule["object_indicators"])
            confidence += len(obj_matches) * 0.15

            # Boost from OCR indicators
            ocr_matches = sum(1 for kw in rule["ocr_indicators"] if kw in ocr_lower)
            confidence += ocr_matches * 0.10

            # Penalty from anti-indicators
            anti_matches = object_set & set(rule["anti_indicators"])
            confidence -= len(anti_matches) * 0.10

            confidence = max(0.0, min(1.0, confidence))

            if confidence >= self._min_confidence:
                results.append(SceneLabel(label=label, confidence=round(confidence, 3)))

        # Sort by confidence descending
        results.sort(key=lambda s: s.confidence, reverse=True)
        return results


# ---------------------------------------------------------------------------
# Convenience: classify across multiple frames and aggregate
# ---------------------------------------------------------------------------

def classify_scenes_across_frames(
    classifier: SceneClassifier,
    frame_data: list[dict[str, Any]],
    top_k: int = 3,
) -> list[SceneLabel]:
    """Classify scenes across multiple frames and return the top-K labels
    by average confidence.

    Parameters
    ----------
    classifier:
        A scene classifier instance.
    frame_data:
        List of dicts with keys ``image_path``, ``objects`` (list[str]),
        ``ocr_text`` (str).
    top_k:
        Number of top scene labels to return.
    """
    label_scores: dict[str, list[float]] = {}

    for fd in frame_data:
        labels = classifier.classify(
            image_path=fd["image_path"],
            objects=fd.get("objects", []),
            ocr_text=fd.get("ocr_text", ""),
        )
        for sl in labels:
            label_scores.setdefault(sl.label, []).append(sl.confidence)

    aggregated: list[SceneLabel] = []
    for label, scores in label_scores.items():
        avg = sum(scores) / len(scores)
        aggregated.append(SceneLabel(label=label, confidence=round(avg, 3)))

    aggregated.sort(key=lambda s: s.confidence, reverse=True)
    return aggregated[:top_k]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_scene_classifier(classifier_name: str = "rule_based") -> SceneClassifier:
    """Factory to obtain a scene classifier by name."""
    if classifier_name == "rule_based":
        return RuleBasedSceneClassifier()
    raise ValueError(f"Unknown scene classifier: {classifier_name}")
