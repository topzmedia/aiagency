"""Analysis tasks: run ML analysis pipelines on candidate videos."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select

from workers.celery_app import app
from workers.db import get_sync_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ML model helpers (graceful degradation when models unavailable)
# ---------------------------------------------------------------------------

def _try_load_embedding_model():
    """Attempt to load sentence-transformers model.  Returns None on failure."""
    try:
        from sentence_transformers import SentenceTransformer
        import os
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
        return SentenceTransformer(model_name)
    except Exception as exc:
        logger.warning("Could not load embedding model: %s", exc)
        return None


def _compute_text_embedding(text: str, model: Any) -> list[float] | None:
    """Compute embedding vector for text.  Returns None if model unavailable."""
    if model is None or not text or not text.strip():
        return None
    try:
        vec = model.encode(text, show_progress_bar=False)
        return vec.tolist()
    except Exception as exc:
        logger.warning("Embedding computation failed: %s", exc)
        return None


def _generate_placeholder_analysis(candidate: Any) -> dict[str, Any]:
    """Generate placeholder analysis data from metadata when ML models are
    unavailable.  This allows the pipeline to function in degraded mode."""
    caption = candidate.caption_text or ""
    hashtags = candidate.hashtags_json or []

    # Extract objects/entities from caption heuristically
    import re
    words = re.findall(r"[a-z]+", caption.lower())
    common_objects = {
        "car", "truck", "vehicle", "dog", "puppy", "cat", "person", "people",
        "kitchen", "house", "building", "road", "tree", "phone", "camera",
        "table", "chair", "food", "water", "fire", "snow", "ice", "couple",
    }
    detected_objects = [{"label": w, "confidence": 0.5} for w in set(words) & common_objects]

    common_actions = {
        "crash", "drive", "walk", "run", "play", "argue", "smile", "laugh",
        "cook", "eat", "dance", "fight", "bark", "sing", "fall", "jump",
    }
    detected_actions = [{"label": w, "confidence": 0.5} for w in set(words) & common_actions]

    # Scene inference from caption
    scene_map = {
        "road": "road_highway", "highway": "road_highway", "dashcam": "road_highway",
        "kitchen": "indoor_kitchen", "cooking": "indoor_kitchen",
        "snow": "snow_outdoors", "winter": "snow_outdoors",
        "house": "suburban_exterior", "roof": "suburban_exterior",
        "home": "residential_interior", "family": "residential_interior",
    }
    detected_scenes = []
    for w in words:
        if w in scene_map:
            detected_scenes.append({"label": scene_map[w], "confidence": 0.5})

    return {
        "objects_json": detected_objects,
        "actions_json": detected_actions,
        "scenes_json": detected_scenes,
        "ocr_text_json": [],
        "transcript_text": None,
        "transcript_chunks_json": [],
        "audio_events_json": [],
        "quality_flags_json": {"source": "placeholder", "ml_available": False},
    }


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@app.task(name="workers.tasks.analysis.analyze_candidate_video", bind=True, max_retries=2)
def analyze_candidate_video(self, candidate_video_id: str) -> dict:
    """Run the full analysis pipeline on a candidate video.

    When ML models are available, this runs object detection, scene
    classification, OCR, ASR, and audio event detection.  When models are
    unavailable, it falls back to heuristic analysis from metadata.
    """
    from apps.api.models.candidate_video import CandidateVideo
    from apps.api.models.video_analysis import VideoAnalysis, AnalysisStatus

    session = get_sync_session()
    try:
        cv_id = uuid.UUID(candidate_video_id)
        candidate = session.get(CandidateVideo, cv_id)
        if candidate is None:
            logger.error("CandidateVideo %s not found", candidate_video_id)
            return {"error": "candidate_not_found"}

        # Find or create analysis record
        analysis = session.execute(
            select(VideoAnalysis).where(VideoAnalysis.candidate_video_id == cv_id)
        ).scalar_one_or_none()

        if analysis is None:
            analysis = VideoAnalysis(
                id=uuid.uuid4(),
                candidate_video_id=cv_id,
                status=AnalysisStatus.pending,
            )
            session.add(analysis)
            session.flush()

        if analysis.status == AnalysisStatus.completed:
            logger.info("Analysis already completed for %s", candidate_video_id)
            return {"candidate_video_id": candidate_video_id, "status": "already_completed"}

        analysis.status = AnalysisStatus.processing
        session.commit()

        # Run analysis (graceful degradation)
        try:
            # In production, this would run real ML pipelines:
            #   - Object detection (YOLO / DETR)
            #   - Scene classification
            #   - OCR (EasyOCR / PaddleOCR)
            #   - ASR (Whisper)
            #   - Audio event detection
            # For now, use placeholder analysis
            result = _generate_placeholder_analysis(candidate)
        except Exception as exc:
            logger.warning("ML pipeline failed, using placeholder: %s", exc)
            result = _generate_placeholder_analysis(candidate)

        # Update analysis record
        analysis.objects_json = result["objects_json"]
        analysis.actions_json = result["actions_json"]
        analysis.scenes_json = result["scenes_json"]
        analysis.ocr_text_json = result["ocr_text_json"]
        analysis.transcript_text = result["transcript_text"]
        analysis.transcript_chunks_json = result["transcript_chunks_json"]
        analysis.audio_events_json = result["audio_events_json"]
        analysis.quality_flags_json = result["quality_flags_json"]
        analysis.status = AnalysisStatus.completed
        session.commit()

        # Trigger embedding computation
        try:
            compute_embeddings.delay(candidate_video_id)
        except Exception as exc:
            logger.warning("Could not queue embedding computation: %s", exc)

        logger.info("Analysis completed for %s", candidate_video_id)
        return {
            "candidate_video_id": candidate_video_id,
            "status": "completed",
            "objects_count": len(result["objects_json"]),
            "scenes_count": len(result["scenes_json"]),
        }

    except Exception as exc:
        session.rollback()
        logger.exception("Analysis failed for %s: %s", candidate_video_id, exc)
        try:
            analysis = session.execute(
                select(VideoAnalysis).where(
                    VideoAnalysis.candidate_video_id == uuid.UUID(candidate_video_id)
                )
            ).scalar_one_or_none()
            if analysis:
                analysis.status = AnalysisStatus.failed
                session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


@app.task(name="workers.tasks.analysis.compute_embeddings", bind=True, max_retries=1)
def compute_embeddings(self, candidate_video_id: str) -> dict:
    """Compute text embeddings for caption, OCR text, and transcript.

    Embeddings are stored in the ContentEmbedding table for vector search.
    Gracefully degrades if embedding model is unavailable.
    """
    from apps.api.models.candidate_video import CandidateVideo
    from apps.api.models.video_analysis import VideoAnalysis
    from apps.api.models.embedding import ContentEmbedding, EmbeddingType, EMBEDDING_DIM

    session = get_sync_session()
    try:
        cv_id = uuid.UUID(candidate_video_id)
        candidate = session.get(CandidateVideo, cv_id)
        if candidate is None:
            return {"error": "candidate_not_found"}

        model = _try_load_embedding_model()
        if model is None:
            logger.warning(
                "Embedding model unavailable; skipping embeddings for %s",
                candidate_video_id,
            )
            return {
                "candidate_video_id": candidate_video_id,
                "status": "skipped",
                "reason": "model_unavailable",
            }

        analysis = session.execute(
            select(VideoAnalysis).where(VideoAnalysis.candidate_video_id == cv_id)
        ).scalar_one_or_none()

        stored = 0

        # Embedding sources: (type, text_content)
        sources: list[tuple[EmbeddingType, str | None]] = [
            (EmbeddingType.caption, candidate.caption_text),
        ]
        if analysis:
            # OCR text
            ocr_texts = [entry.get("text", "") for entry in (analysis.ocr_text_json or [])]
            ocr_combined = " ".join(ocr_texts).strip()
            if ocr_combined:
                sources.append((EmbeddingType.ocr, ocr_combined))

            # Transcript
            if analysis.transcript_text:
                sources.append((EmbeddingType.transcript, analysis.transcript_text))

        for emb_type, text_content in sources:
            if not text_content or not text_content.strip():
                continue

            vec = _compute_text_embedding(text_content, model)
            if vec is None:
                continue

            # Check if embedding already exists
            existing = session.execute(
                select(ContentEmbedding).where(
                    ContentEmbedding.candidate_video_id == cv_id,
                    ContentEmbedding.embedding_type == emb_type,
                )
            ).scalar_one_or_none()

            if existing:
                existing.embedding = vec
                existing.text_content = text_content
            else:
                emb = ContentEmbedding(
                    id=uuid.uuid4(),
                    candidate_video_id=cv_id,
                    embedding_type=emb_type,
                    text_content=text_content,
                    embedding=vec,
                )
                session.add(emb)
            stored += 1

        session.commit()
        logger.info("Stored %d embeddings for %s", stored, candidate_video_id)
        return {
            "candidate_video_id": candidate_video_id,
            "status": "completed",
            "embeddings_stored": stored,
        }

    except Exception as exc:
        session.rollback()
        logger.exception("Embedding computation failed for %s: %s", candidate_video_id, exc)
        raise self.retry(exc=exc, countdown=20)
    finally:
        session.close()
