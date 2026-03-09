"""Frame sampling service.

Samples keyframes from a video at a configurable interval within each scene
segment.  Frames are saved as JPEG images for downstream analysis (OCR,
object detection, scene classification).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from apps.api.services.scene_segmentation import SceneSegment

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
            raise RuntimeError("OpenCV (cv2) is required for frame sampling")
    return _cv2


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FrameSample:
    """A sampled keyframe written to disk."""
    path: str
    timestamp_sec: float
    scene_index: int


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def sample_keyframes(
    video_path: str | Path,
    scenes: list[SceneSegment],
    output_dir: str | Path | None = None,
    interval: float = 0.5,
    jpeg_quality: int = 85,
) -> list[FrameSample]:
    """Sample keyframes from a video within each scene.

    Parameters
    ----------
    video_path:
        Path to the source video.
    scenes:
        List of scene segments (from :func:`detect_scenes`).
    output_dir:
        Directory to write JPEG frames to.  Defaults to a ``frames/``
        subdirectory next to the video.
    interval:
        Sampling interval in seconds within each scene.
    jpeg_quality:
        JPEG encoding quality (1-100).
    """
    cv2 = _get_cv2()
    video_path = Path(video_path)

    if output_dir is None:
        output_dir = video_path.parent / "frames" / video_path.stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    samples: list[FrameSample] = []

    for scene in scenes:
        t = scene.start_sec
        while t < scene.end_sec:
            frame_number = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                break

            filename = f"scene{scene.scene_index:04d}_t{t:07.3f}.jpg"
            frame_path = out_dir / filename

            cv2.imwrite(
                str(frame_path),
                frame,
                [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality],
            )

            samples.append(FrameSample(
                path=str(frame_path),
                timestamp_sec=round(t, 3),
                scene_index=scene.scene_index,
            ))

            t += interval

    cap.release()
    logger.info("Sampled %d keyframes from %s", len(samples), video_path)
    return samples
