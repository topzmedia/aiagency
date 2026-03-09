"""Scene segmentation service.

Detects shot boundaries in video files by computing inter-frame differences
using OpenCV.  Returns a list of temporal segments.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

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
            raise RuntimeError("OpenCV (cv2) is required for scene segmentation")
    return _cv2


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SceneSegment:
    """A temporal segment of a video."""
    start_sec: float
    end_sec: float
    scene_index: int


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

def detect_scenes(
    video_path: str | Path,
    threshold: float = 30.0,
    min_scene_duration: float = 0.5,
    sample_every_n_frames: int = 1,
) -> list[SceneSegment]:
    """Detect scene/shot boundaries by computing frame-to-frame differences.

    Parameters
    ----------
    video_path:
        Path to the video file.
    threshold:
        Mean absolute difference threshold for declaring a scene change.
        Higher values yield fewer scenes.
    min_scene_duration:
        Minimum duration in seconds for a scene segment.  Very short scenes
        are merged into the previous one.
    sample_every_n_frames:
        Process every N-th frame to speed up detection.
    """
    cv2 = _get_cv2()
    video_path = str(video_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0.0

    boundaries: list[float] = [0.0]  # first scene always starts at 0
    prev_gray = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_every_n_frames != 0:
            frame_idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 120))  # low-res for speed

        if prev_gray is not None:
            diff = cv2.absdiff(gray, prev_gray)
            mean_diff = float(diff.mean())

            if mean_diff > threshold:
                timestamp = frame_idx / fps
                # Enforce minimum scene duration
                if timestamp - boundaries[-1] >= min_scene_duration:
                    boundaries.append(timestamp)

        prev_gray = gray
        frame_idx += 1

    cap.release()

    # Close last scene at video end
    if duration > 0:
        boundaries.append(duration)
    elif boundaries:
        boundaries.append(boundaries[-1] + 1.0)

    # Build scene segments
    scenes: list[SceneSegment] = []
    for i in range(len(boundaries) - 1):
        scenes.append(SceneSegment(
            start_sec=round(boundaries[i], 3),
            end_sec=round(boundaries[i + 1], 3),
            scene_index=i,
        ))

    logger.info("Detected %d scenes in %s (%.1fs)", len(scenes), video_path, duration)
    return scenes
