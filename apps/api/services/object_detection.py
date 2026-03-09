"""Object detection service.

Provides an interface for detecting objects in video frames and an MVP
implementation using heuristic colour/contour analysis.  The interface is
designed so a real model (e.g. YOLOv8 via OpenCV DNN) can be swapped in
without changing downstream consumers.
"""
from __future__ import annotations

import abc
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-load OpenCV
# ---------------------------------------------------------------------------
_cv2 = None


def _get_cv2():
    global _cv2
    if _cv2 is None:
        try:
            import cv2  # type: ignore[import-untyped]
            _cv2 = cv2
        except ImportError:
            raise RuntimeError("OpenCV (cv2) is required for object detection")
    return _cv2


# ---------------------------------------------------------------------------
# Common label set
# ---------------------------------------------------------------------------

COMMON_LABELS = [
    "car", "truck", "person", "dog", "roof", "house", "kitchen", "table",
    "phone", "fire", "road", "tree", "building", "water", "sky",
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BBox:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass
class DetectionResult:
    """A single object detection."""
    label: str
    confidence: float
    bbox: BBox | None = None


@dataclass
class AggregatedDetections:
    """Detections aggregated across multiple frames."""
    all_detections: list[DetectionResult] = field(default_factory=list)
    label_frequency: dict[str, int] = field(default_factory=dict)
    label_max_confidence: dict[str, float] = field(default_factory=dict)
    frame_count: int = 0


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class ObjectDetector(abc.ABC):
    """Abstract object detection interface."""

    @abc.abstractmethod
    def detect(self, image_path: str | Path) -> list[DetectionResult]:
        """Detect objects in a single image."""
        ...


# ---------------------------------------------------------------------------
# MVP heuristic implementation
# ---------------------------------------------------------------------------

# HSV colour ranges for simple object heuristics
_COLOUR_RULES: list[dict[str, Any]] = [
    {
        "label": "sky",
        "lower": (90, 40, 120),
        "upper": (130, 255, 255),
        "min_area_ratio": 0.15,
        "region": "top",
    },
    {
        "label": "road",
        "lower": (0, 0, 40),
        "upper": (180, 60, 140),
        "min_area_ratio": 0.10,
        "region": "bottom",
    },
    {
        "label": "tree",
        "lower": (35, 40, 40),
        "upper": (85, 255, 255),
        "min_area_ratio": 0.05,
        "region": "any",
    },
    {
        "label": "water",
        "lower": (85, 50, 50),
        "upper": (135, 255, 200),
        "min_area_ratio": 0.10,
        "region": "bottom",
    },
    {
        "label": "fire",
        "lower": (0, 150, 150),
        "upper": (20, 255, 255),
        "min_area_ratio": 0.02,
        "region": "any",
    },
]


class HeuristicObjectDetector(ObjectDetector):
    """MVP object detector using colour analysis and contour heuristics.

    This is a placeholder that produces approximate detections.  Replace with
    a real model (e.g. YOLOv8 via OpenCV DNN) for production accuracy.
    """

    def detect(self, image_path: str | Path) -> list[DetectionResult]:
        cv2 = _get_cv2()
        import numpy as np  # noqa: F811

        img = cv2.imread(str(image_path))
        if img is None:
            logger.warning("Could not read image: %s", image_path)
            return []

        h, w = img.shape[:2]
        total_pixels = h * w
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        results: list[DetectionResult] = []

        for rule in _COLOUR_RULES:
            lower = np.array(rule["lower"], dtype=np.uint8)
            upper = np.array(rule["upper"], dtype=np.uint8)

            # Apply region mask
            mask = cv2.inRange(hsv, lower, upper)
            if rule["region"] == "top":
                mask[h // 2:, :] = 0
            elif rule["region"] == "bottom":
                mask[:h // 2, :] = 0

            area_ratio = float(cv2.countNonZero(mask)) / total_pixels
            if area_ratio >= rule["min_area_ratio"]:
                confidence = min(1.0, area_ratio / (rule["min_area_ratio"] * 3))
                results.append(DetectionResult(
                    label=rule["label"],
                    confidence=round(confidence, 3),
                ))

        # Contour-based heuristic for large blobs (potential vehicles, people)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        edges = cv2.Canny(blurred, 30, 100)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        large_contours = [
            c for c in contours
            if cv2.contourArea(c) > total_pixels * 0.01
        ]

        if large_contours:
            # Largest contour in lower half -> possible vehicle
            for cnt in sorted(large_contours, key=cv2.contourArea, reverse=True)[:3]:
                x_c, y_c, w_c, h_c = cv2.boundingRect(cnt)
                center_y = y_c + h_c / 2
                area_ratio = (w_c * h_c) / total_pixels
                aspect = w_c / max(h_c, 1)

                if center_y > h * 0.4 and 1.2 < aspect < 4.0 and area_ratio > 0.02:
                    results.append(DetectionResult(
                        label="car",
                        confidence=round(min(0.6, area_ratio * 5), 3),
                        bbox=BBox(
                            x_min=float(x_c),
                            y_min=float(y_c),
                            x_max=float(x_c + w_c),
                            y_max=float(y_c + h_c),
                        ),
                    ))
                elif 0.3 < aspect < 1.5 and area_ratio > 0.01:
                    results.append(DetectionResult(
                        label="person",
                        confidence=round(min(0.5, area_ratio * 4), 3),
                        bbox=BBox(
                            x_min=float(x_c),
                            y_min=float(y_c),
                            x_max=float(x_c + w_c),
                            y_max=float(y_c + h_c),
                        ),
                    ))

        return results


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate_detections(
    frame_detections: dict[float, list[DetectionResult]],
    min_confidence: float = 0.2,
) -> AggregatedDetections:
    """Aggregate detections across frames, computing frequency and max confidence.

    Parameters
    ----------
    frame_detections:
        Mapping of frame timestamp to list of detections.
    min_confidence:
        Filter out detections below this confidence.
    """
    freq: dict[str, int] = defaultdict(int)
    max_conf: dict[str, float] = defaultdict(float)
    all_dets: list[DetectionResult] = []

    for ts in sorted(frame_detections.keys()):
        for det in frame_detections[ts]:
            if det.confidence < min_confidence:
                continue
            all_dets.append(det)
            freq[det.label] += 1
            if det.confidence > max_conf[det.label]:
                max_conf[det.label] = det.confidence

    return AggregatedDetections(
        all_detections=all_dets,
        label_frequency=dict(freq),
        label_max_confidence={k: round(v, 4) for k, v in max_conf.items()},
        frame_count=len(frame_detections),
    )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_object_detector(detector_name: str = "heuristic") -> ObjectDetector:
    """Factory function to obtain an object detector by name."""
    if detector_name == "heuristic":
        return HeuristicObjectDetector()
    raise ValueError(f"Unknown object detector: {detector_name}")
