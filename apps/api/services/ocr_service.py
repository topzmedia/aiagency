"""OCR service with provider interface.

Extracts text from video frames using an OCR backend (default: EasyOCR).
Provides aggregation and deduplication of OCR results across multiple frames.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BBox:
    """Bounding box for detected text."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass
class OCRResult:
    """A single OCR detection."""
    text: str
    confidence: float
    bbox: BBox | None = None
    frame_timestamp: float | None = None


@dataclass
class AggregatedOCR:
    """Aggregated OCR results across all frames of a video."""
    all_results: list[OCRResult] = field(default_factory=list)
    unique_texts: list[str] = field(default_factory=list)
    full_text: str = ""


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------

class OCRProvider(abc.ABC):
    """Abstract OCR provider interface."""

    @abc.abstractmethod
    def run_ocr(self, image_path: str | Path) -> list[OCRResult]:
        """Run OCR on a single image and return detected text regions."""
        ...


# ---------------------------------------------------------------------------
# EasyOCR implementation (lazy-loaded)
# ---------------------------------------------------------------------------

class EasyOCRProvider(OCRProvider):
    """OCR provider using EasyOCR."""

    def __init__(self, languages: list[str] | None = None):
        self._languages = languages or ["en"]
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr  # type: ignore[import-untyped]
                self._reader = easyocr.Reader(self._languages, gpu=False)
                logger.info("EasyOCR reader initialised (languages=%s)", self._languages)
            except ImportError:
                raise RuntimeError(
                    "easyocr is required for EasyOCRProvider. "
                    "Install with: pip install easyocr"
                )
        return self._reader

    def run_ocr(self, image_path: str | Path) -> list[OCRResult]:
        reader = self._get_reader()
        image_path = str(image_path)

        try:
            raw_results = reader.readtext(image_path)
        except Exception:
            logger.exception("EasyOCR failed on %s", image_path)
            return []

        results: list[OCRResult] = []
        for bbox_points, text, confidence in raw_results:
            # bbox_points is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            bbox = BBox(
                x_min=min(xs),
                y_min=min(ys),
                x_max=max(xs),
                y_max=max(ys),
            )
            results.append(OCRResult(
                text=text.strip(),
                confidence=float(confidence),
                bbox=bbox,
            ))

        return results


# ---------------------------------------------------------------------------
# Aggregation / deduplication helpers
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Lowercase and strip whitespace for dedup comparison."""
    return " ".join(text.lower().split())


def aggregate_ocr_results(
    frame_results: dict[float, list[OCRResult]],
    min_confidence: float = 0.3,
) -> AggregatedOCR:
    """Aggregate and deduplicate OCR results from multiple frames.

    Parameters
    ----------
    frame_results:
        Mapping of frame timestamp to OCR results for that frame.
    min_confidence:
        Discard results below this confidence threshold.
    """
    all_results: list[OCRResult] = []
    seen_normalized: set[str] = set()
    unique_texts: list[str] = []

    for ts in sorted(frame_results.keys()):
        for r in frame_results[ts]:
            if r.confidence < min_confidence:
                continue
            r.frame_timestamp = ts
            all_results.append(r)

            norm = _normalize_text(r.text)
            if norm and norm not in seen_normalized:
                seen_normalized.add(norm)
                unique_texts.append(r.text.strip())

    full_text = " ".join(unique_texts)

    return AggregatedOCR(
        all_results=all_results,
        unique_texts=unique_texts,
        full_text=full_text,
    )


# ---------------------------------------------------------------------------
# Convenience: run OCR across frames
# ---------------------------------------------------------------------------

def run_ocr_on_frames(
    provider: OCRProvider,
    frame_paths: list[tuple[str, float]],
    min_confidence: float = 0.3,
) -> AggregatedOCR:
    """Run OCR on a list of frames and return aggregated results.

    Parameters
    ----------
    provider:
        The OCR backend to use.
    frame_paths:
        List of (image_path, timestamp_sec) tuples.
    min_confidence:
        Discard results below this confidence.
    """
    frame_results: dict[float, list[OCRResult]] = {}
    for path, ts in frame_paths:
        try:
            results = provider.run_ocr(path)
            frame_results[ts] = results
        except Exception:
            logger.exception("OCR failed for frame %s", path)
            frame_results[ts] = []

    return aggregate_ocr_results(frame_results, min_confidence=min_confidence)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_ocr_provider(provider_name: str = "easyocr") -> OCRProvider:
    """Factory function to get an OCR provider by name."""
    if provider_name == "easyocr":
        return EasyOCRProvider()
    raise ValueError(f"Unknown OCR provider: {provider_name}")
