"""Main analysis pipeline orchestrator.

Runs the full video analysis pipeline: media preparation, scene segmentation,
frame sampling, OCR, ASR, object detection, scene classification, action
analysis, audio analysis, and embedding computation.  Each step catches errors
gracefully so the pipeline can continue even if individual stages fail.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from apps.api.services.scene_segmentation import SceneSegment

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AnalysisStepResult:
    """Outcome of a single pipeline step."""
    step: str
    success: bool
    data: Any = None
    error: str | None = None


@dataclass
class VideoAnalysisResult:
    """Complete result of the analysis pipeline for one video."""
    candidate_video_id: uuid.UUID
    steps: list[AnalysisStepResult] = field(default_factory=list)
    media_info: Any = None
    scenes: list[SceneSegment] = field(default_factory=list)
    frames: list[Any] = field(default_factory=list)
    ocr_text: str = ""
    transcript_text: str = ""
    detected_objects: list[str] = field(default_factory=list)
    scene_labels: list[str] = field(default_factory=list)
    action_events: list[Any] = field(default_factory=list)
    audio_events: list[Any] = field(default_factory=list)
    embeddings: dict[str, Any] = field(default_factory=dict)
    success: bool = True

    @property
    def failed_steps(self) -> list[str]:
        return [s.step for s in self.steps if not s.success]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _run_step(name: str, fn, *args, **kwargs) -> AnalysisStepResult:
    """Execute a pipeline step, catching any exception."""
    try:
        data = fn(*args, **kwargs)
        return AnalysisStepResult(step=name, success=True, data=data)
    except Exception as exc:
        logger.error("Pipeline step '%s' failed: %s", name, exc, exc_info=True)
        return AnalysisStepResult(step=name, success=False, error=str(exc))


def analyze_video(
    candidate_video_id: uuid.UUID,
    video_path: str | Path,
    output_dir: str | Path | None = None,
    ocr_provider_name: str = "easyocr",
    asr_provider_name: str = "faster-whisper",
    asr_model_size: str = "base",
    detector_name: str = "heuristic",
    scene_classifier_name: str = "rule_based",
    action_analyzer_name: str = "rule_based",
    audio_analyzer_name: str = "heuristic",
    embedding_model: str = "all-MiniLM-L6-v2",
    scene_threshold: float = 30.0,
    frame_interval: float = 0.5,
) -> VideoAnalysisResult:
    """Run the full analysis pipeline on a single video.

    Parameters
    ----------
    candidate_video_id:
        Database UUID of the candidate video.
    video_path:
        Path to the video file on disk.
    output_dir:
        Directory for intermediate outputs (frames, audio, thumbnails).
        Defaults to a subdirectory next to the video.
    """
    video_path = Path(video_path)
    if output_dir is None:
        output_dir = video_path.parent / "analysis" / video_path.stem
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    result = VideoAnalysisResult(candidate_video_id=candidate_video_id)

    logger.info("Starting analysis pipeline for %s (%s)", candidate_video_id, video_path)

    # -----------------------------------------------------------------------
    # Step 1: Media preparation
    # -----------------------------------------------------------------------
    from apps.api.services.media_prep import probe_media, extract_thumbnail, extract_audio

    step = _run_step("media_probe", probe_media, video_path)
    result.steps.append(step)
    if step.success:
        result.media_info = step.data

    step = _run_step("thumbnail_extract", extract_thumbnail, video_path,
                     out_dir / "thumbnail.jpg")
    result.steps.append(step)

    audio_path = out_dir / "audio.wav"
    step = _run_step("audio_extract", extract_audio, video_path, audio_path)
    result.steps.append(step)
    audio_extracted = step.success

    # -----------------------------------------------------------------------
    # Step 2: Scene segmentation
    # -----------------------------------------------------------------------
    from apps.api.services.scene_segmentation import detect_scenes

    step = _run_step("scene_segmentation", detect_scenes, video_path,
                     threshold=scene_threshold)
    result.steps.append(step)
    if step.success and step.data:
        result.scenes = step.data
    else:
        # Fallback: single scene spanning entire video
        duration = result.media_info.duration_sec if result.media_info else 10.0
        result.scenes = [SceneSegment(start_sec=0.0, end_sec=duration, scene_index=0)]

    # -----------------------------------------------------------------------
    # Step 3: Frame sampling
    # -----------------------------------------------------------------------
    from apps.api.services.frame_sampling import sample_keyframes

    step = _run_step("frame_sampling", sample_keyframes, video_path, result.scenes,
                     out_dir / "frames", interval=frame_interval)
    result.steps.append(step)
    if step.success and step.data:
        result.frames = step.data

    # -----------------------------------------------------------------------
    # Step 4: OCR on frames
    # -----------------------------------------------------------------------
    if result.frames:
        from apps.api.services.ocr_service import get_ocr_provider, run_ocr_on_frames

        def _do_ocr():
            provider = get_ocr_provider(ocr_provider_name)
            frame_paths = [(f.path, f.timestamp_sec) for f in result.frames]
            return run_ocr_on_frames(provider, frame_paths)

        step = _run_step("ocr", _do_ocr)
        result.steps.append(step)
        if step.success and step.data:
            result.ocr_text = step.data.full_text
    else:
        result.steps.append(AnalysisStepResult(
            step="ocr", success=False, error="No frames available"))

    # -----------------------------------------------------------------------
    # Step 5: ASR / transcription
    # -----------------------------------------------------------------------
    if audio_extracted and audio_path.exists():
        from apps.api.services.asr_service import get_asr_provider

        def _do_asr():
            provider = get_asr_provider(asr_provider_name, model_size=asr_model_size)
            return provider.transcribe(str(audio_path))

        step = _run_step("asr", _do_asr)
        result.steps.append(step)
        if step.success and step.data:
            result.transcript_text = step.data.full_text
    else:
        result.steps.append(AnalysisStepResult(
            step="asr", success=False, error="No audio available"))

    # -----------------------------------------------------------------------
    # Step 6: Object detection on frames
    # -----------------------------------------------------------------------
    detected_objects_list: list[str] = []
    if result.frames:
        from apps.api.services.object_detection import get_object_detector, aggregate_detections

        def _do_detection():
            detector = get_object_detector(detector_name)
            frame_dets: dict[float, list] = {}
            for f in result.frames:
                dets = detector.detect(f.path)
                frame_dets[f.timestamp_sec] = dets
            return aggregate_detections(frame_dets)

        step = _run_step("object_detection", _do_detection)
        result.steps.append(step)
        if step.success and step.data:
            detected_objects_list = list(step.data.label_frequency.keys())
            result.detected_objects = detected_objects_list
    else:
        result.steps.append(AnalysisStepResult(
            step="object_detection", success=False, error="No frames available"))

    # -----------------------------------------------------------------------
    # Step 7: Scene classification
    # -----------------------------------------------------------------------
    if result.frames:
        from apps.api.services.scene_classification import (
            get_scene_classifier,
            classify_scenes_across_frames,
        )

        def _do_scene_class():
            classifier = get_scene_classifier(scene_classifier_name)
            frame_data = [
                {
                    "image_path": f.path,
                    "objects": detected_objects_list,
                    "ocr_text": result.ocr_text,
                }
                for f in result.frames
            ]
            return classify_scenes_across_frames(classifier, frame_data, top_k=3)

        step = _run_step("scene_classification", _do_scene_class)
        result.steps.append(step)
        if step.success and step.data:
            result.scene_labels = [sl.label for sl in step.data]
    else:
        result.steps.append(AnalysisStepResult(
            step="scene_classification", success=False, error="No frames available"))

    # -----------------------------------------------------------------------
    # Step 8: Action analysis
    # -----------------------------------------------------------------------
    from apps.api.services.action_analysis import get_action_analyzer

    def _do_action():
        analyzer = get_action_analyzer(action_analyzer_name)
        return analyzer.analyze(
            scenes=result.scenes,
            objects=detected_objects_list,
            transcript=result.transcript_text,
            ocr_text=result.ocr_text,
            audio_events=[],  # filled in next step on re-analysis if needed
        )

    step = _run_step("action_analysis", _do_action)
    result.steps.append(step)
    if step.success and step.data:
        result.action_events = step.data

    # -----------------------------------------------------------------------
    # Step 9: Audio analysis
    # -----------------------------------------------------------------------
    if audio_extracted and audio_path.exists():
        from apps.api.services.audio_analysis import get_audio_analyzer

        def _do_audio():
            analyzer = get_audio_analyzer(audio_analyzer_name)
            return analyzer.analyze(str(audio_path), result.transcript_text)

        step = _run_step("audio_analysis", _do_audio)
        result.steps.append(step)
        if step.success and step.data:
            result.audio_events = step.data
    else:
        result.steps.append(AnalysisStepResult(
            step="audio_analysis", success=False, error="No audio available"))

    # -----------------------------------------------------------------------
    # Step 10: Compute embeddings
    # -----------------------------------------------------------------------
    def _do_embeddings():
        from apps.api.services.embedding_service import embed_text

        emb_map: dict[str, Any] = {}
        if result.ocr_text:
            emb_map["ocr"] = embed_text(result.ocr_text).tolist()
        if result.transcript_text:
            emb_map["transcript"] = embed_text(result.transcript_text).tolist()

        # Combine all text for a unified embedding
        combined = " ".join(filter(None, [result.ocr_text, result.transcript_text]))
        if combined.strip():
            emb_map["combined"] = embed_text(combined).tolist()

        return emb_map

    step = _run_step("embeddings", _do_embeddings)
    result.steps.append(step)
    if step.success and step.data:
        result.embeddings = step.data

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    failed = result.failed_steps
    if failed:
        logger.warning(
            "Pipeline for %s completed with %d failed steps: %s",
            candidate_video_id, len(failed), failed,
        )
    else:
        logger.info("Pipeline for %s completed successfully", candidate_video_id)

    return result
