"""Seed script for Content Finder.

Creates sample data for development and testing:
- A default user
- Sample candidate videos from the seed CSV
- Sample video analyses with realistic data
- A sample search with ranked results

Usage:
    python -m scripts.seed
"""
from __future__ import annotations

import csv
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from apps.api.config import settings
from apps.api.models.base import Base
from apps.api.models.user import User
from apps.api.models.candidate_video import CandidateVideo
from apps.api.models.video_analysis import VideoAnalysis, AnalysisStatus
from apps.api.models.search import Search, SearchStatus
from apps.api.models.result_ranking import ResultRanking
from apps.api.models.collection import Collection

# Build sync URL from async URL
SYNC_URL = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")

engine = create_engine(SYNC_URL, echo=False)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

# Seed CSV path
SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "seed" / "sample_videos.csv"

# ---------------------------------------------------------------------------
# Realistic analysis data per video category
# ---------------------------------------------------------------------------

ANALYSIS_TEMPLATES: dict[str, dict] = {
    "car_crash": {
        "objects_json": [
            {"label": "car", "confidence": 0.95},
            {"label": "road", "confidence": 0.92},
            {"label": "truck", "confidence": 0.78},
            {"label": "debris", "confidence": 0.65},
        ],
        "actions_json": [
            {"label": "crash", "confidence": 0.94},
            {"label": "drive", "confidence": 0.88},
        ],
        "scenes_json": [
            {"label": "road_highway", "confidence": 0.93},
        ],
        "audio_events_json": [
            {"label": "impact", "confidence": 0.91},
            {"label": "screech", "confidence": 0.85},
        ],
        "ocr_text_json": [
            {"text": "DASHCAM", "confidence": 0.8, "bbox": [10, 10, 100, 30]},
        ],
        "transcript_text": None,
        "quality_flags_json": {"source": "seed", "resolution": "1080p"},
    },
    "kitchen": {
        "objects_json": [
            {"label": "kitchen", "confidence": 0.97},
            {"label": "countertop", "confidence": 0.91},
            {"label": "cabinets", "confidence": 0.88},
            {"label": "pendant_light", "confidence": 0.82},
            {"label": "marble", "confidence": 0.79},
        ],
        "actions_json": [
            {"label": "cook", "confidence": 0.45},
        ],
        "scenes_json": [
            {"label": "indoor_kitchen", "confidence": 0.96},
        ],
        "audio_events_json": [
            {"label": "speech", "confidence": 0.75},
        ],
        "ocr_text_json": [],
        "transcript_text": "Welcome to my luxury kitchen tour. Check out this marble island.",
        "quality_flags_json": {"source": "seed", "resolution": "4k"},
    },
    "dogs_snow": {
        "objects_json": [
            {"label": "dog", "confidence": 0.96},
            {"label": "snow", "confidence": 0.94},
            {"label": "person", "confidence": 0.72},
        ],
        "actions_json": [
            {"label": "play", "confidence": 0.92},
            {"label": "run", "confidence": 0.85},
            {"label": "jump", "confidence": 0.70},
        ],
        "scenes_json": [
            {"label": "snow_outdoors", "confidence": 0.95},
        ],
        "audio_events_json": [
            {"label": "bark", "confidence": 0.88},
        ],
        "ocr_text_json": [],
        "transcript_text": None,
        "quality_flags_json": {"source": "seed", "resolution": "1080p"},
    },
    "arguing": {
        "objects_json": [
            {"label": "person", "confidence": 0.95},
            {"label": "person", "confidence": 0.93},
        ],
        "actions_json": [
            {"label": "argue", "confidence": 0.89},
            {"label": "yell", "confidence": 0.82},
        ],
        "scenes_json": [
            {"label": "outdoor_urban", "confidence": 0.78},
        ],
        "audio_events_json": [
            {"label": "speech", "confidence": 0.95},
        ],
        "ocr_text_json": [],
        "transcript_text": "I can't believe you did that! This is ridiculous!",
        "quality_flags_json": {"source": "seed", "resolution": "720p"},
    },
    "couple_kitchen": {
        "objects_json": [
            {"label": "person", "confidence": 0.96},
            {"label": "person", "confidence": 0.94},
            {"label": "table", "confidence": 0.91},
            {"label": "kitchen", "confidence": 0.87},
        ],
        "actions_json": [
            {"label": "smile", "confidence": 0.93},
            {"label": "laugh", "confidence": 0.80},
            {"label": "eat", "confidence": 0.65},
        ],
        "scenes_json": [
            {"label": "indoor_kitchen", "confidence": 0.88},
            {"label": "residential_interior", "confidence": 0.82},
        ],
        "audio_events_json": [
            {"label": "speech", "confidence": 0.90},
        ],
        "ocr_text_json": [],
        "transcript_text": "Honey, this turned out amazing! Best recipe yet.",
        "quality_flags_json": {"source": "seed", "resolution": "1080p"},
    },
}

# Map CSV caption keywords to analysis template
def _get_analysis_template(caption: str) -> dict:
    caption_lower = (caption or "").lower()
    if any(kw in caption_lower for kw in ["crash", "dashcam", "collision", "accident"]):
        return ANALYSIS_TEMPLATES["car_crash"]
    if any(kw in caption_lower for kw in ["kitchen tour", "luxury kitchen", "marble", "cabinets"]):
        return ANALYSIS_TEMPLATES["kitchen"]
    if any(kw in caption_lower for kw in ["dog", "puppy", "snow", "winter"]):
        return ANALYSIS_TEMPLATES["dogs_snow"]
    if any(kw in caption_lower for kw in ["argu", "yell", "fight", "confrontation"]):
        return ANALYSIS_TEMPLATES["arguing"]
    if any(kw in caption_lower for kw in ["couple", "smiling", "family", "table"]):
        return ANALYSIS_TEMPLATES["couple_kitchen"]
    return ANALYSIS_TEMPLATES["couple_kitchen"]  # default


def seed():
    """Run the full seed pipeline."""
    session: Session = SessionFactory()

    try:
        print("=" * 60)
        print("Content Finder - Seed Script")
        print("=" * 60)

        # 1. Create tables (if not existing)
        Base.metadata.create_all(engine)
        print("[OK] Database tables ensured")

        # 2. Create default user
        existing_user = session.execute(
            select(User).where(User.email == "demo@contentfinder.dev")
        ).scalar_one_or_none()

        if existing_user:
            user = existing_user
            print(f"[--] Default user already exists: {user.id}")
        else:
            user = User(id=uuid.uuid4(), email="demo@contentfinder.dev")
            session.add(user)
            session.flush()
            print(f"[OK] Created default user: {user.id}")

        # 3. Import candidate videos from seed CSV
        candidate_ids: list[uuid.UUID] = []

        if SEED_CSV.exists():
            with open(SEED_CSV, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    source_url = row.get("source_url", "").strip()
                    if not source_url:
                        continue

                    # Check if already imported
                    existing = session.execute(
                        select(CandidateVideo).where(CandidateVideo.source_url == source_url)
                    ).scalar_one_or_none()

                    if existing:
                        candidate_ids.append(existing.id)
                        continue

                    publish_date = None
                    pd_str = row.get("publish_date", "").strip()
                    if pd_str:
                        try:
                            publish_date = datetime.fromisoformat(pd_str)
                        except ValueError:
                            pass

                    duration_sec = None
                    dur_str = row.get("duration_sec", "").strip()
                    if dur_str:
                        try:
                            duration_sec = float(dur_str)
                        except ValueError:
                            pass

                    hashtags_raw = row.get("hashtags", "").strip()
                    hashtags = [h.strip() for h in hashtags_raw.split(",") if h.strip()] if hashtags_raw else []

                    cv = CandidateVideo(
                        id=uuid.uuid4(),
                        external_id=row.get("external_id", "").strip() or None,
                        platform=row.get("platform", "unknown").strip(),
                        source_url=source_url,
                        creator_handle=row.get("creator_handle", "").strip() or None,
                        caption_text=row.get("caption_text", "").strip() or None,
                        hashtags_json=hashtags if hashtags else None,
                        publish_date=publish_date,
                        duration_sec=duration_sec,
                        language=row.get("language", "en").strip(),
                        region_hint=row.get("region_hint", "US").strip(),
                        ingestion_source="seed",
                        metadata_json={},
                    )
                    session.add(cv)
                    session.flush()
                    candidate_ids.append(cv.id)

            print(f"[OK] Loaded {len(candidate_ids)} candidate videos from seed CSV")
        else:
            print(f"[!!] Seed CSV not found at {SEED_CSV}")

        # 4. Create sample analyses
        analyses_created = 0
        for cv_id in candidate_ids:
            existing_analysis = session.execute(
                select(VideoAnalysis).where(VideoAnalysis.candidate_video_id == cv_id)
            ).scalar_one_or_none()

            if existing_analysis:
                continue

            cv = session.get(CandidateVideo, cv_id)
            template = _get_analysis_template(cv.caption_text if cv else "")

            analysis = VideoAnalysis(
                id=uuid.uuid4(),
                candidate_video_id=cv_id,
                status=AnalysisStatus.completed,
                objects_json=template["objects_json"],
                actions_json=template["actions_json"],
                scenes_json=template["scenes_json"],
                audio_events_json=template["audio_events_json"],
                ocr_text_json=template["ocr_text_json"],
                transcript_text=template["transcript_text"],
                transcript_chunks_json=[],
                quality_flags_json=template["quality_flags_json"],
            )
            session.add(analysis)
            analyses_created += 1

        session.flush()
        print(f"[OK] Created {analyses_created} video analyses")

        # 5. Create a sample search with results
        existing_search = session.execute(
            select(Search).where(
                Search.raw_query == "car crash dashcam footage",
                Search.user_id == user.id,
            )
        ).scalar_one_or_none()

        if existing_search:
            print(f"[--] Sample search already exists: {existing_search.id}")
        else:
            search = Search(
                id=uuid.uuid4(),
                user_id=user.id,
                raw_query="car crash dashcam footage",
                normalized_query_json={
                    "raw_query": "car crash dashcam footage",
                    "entities": ["car", "dashcam"],
                    "actions": ["crash"],
                    "scenes": ["road_highway"],
                    "attributes": ["footage"],
                    "audio_events": ["impact", "screech"],
                    "synonyms": ["collision", "wreck", "accident", "fender bender"],
                    "ocr_terms": ["car", "crash", "dashcam"],
                    "exclude": [],
                },
                status=SearchStatus.completed,
                progress_percent=100,
                max_results=50,
                confidence_threshold=0.3,
            )
            session.add(search)
            session.flush()

            # Add result rankings for matching candidates
            rank = 0
            for cv_id in candidate_ids:
                cv = session.get(CandidateVideo, cv_id)
                if not cv:
                    continue
                caption = (cv.caption_text or "").lower()
                if any(kw in caption for kw in ["crash", "dashcam", "collision", "accident"]):
                    rank += 1
                    score = max(0.3, 0.95 - (rank - 1) * 0.08)
                    ranking = ResultRanking(
                        id=uuid.uuid4(),
                        search_id=search.id,
                        candidate_video_id=cv_id,
                        final_score=round(score, 4),
                        rank_position=rank,
                        accepted=True,
                        reason_codes_json=["caption_match:3_terms", "scene_match:road_highway", "audio_match:impact"],
                        score_breakdown_json={
                            "caption_relevance": 0.30,
                            "analysis_relevance": 0.28,
                            "scene_match": 0.15,
                            "audio_match": 0.10,
                            "recency_bonus": 0.03,
                            "penalty": 0.0,
                        },
                    )
                    session.add(ranking)

            search.total_candidates = len(candidate_ids)
            search.total_analyzed = len(candidate_ids)
            search.total_results = rank
            session.flush()
            print(f"[OK] Created sample search '{search.raw_query}' with {rank} results")

        # 6. Create a sample collection
        existing_collection = session.execute(
            select(Collection).where(
                Collection.name == "Insurance Claims Review",
                Collection.user_id == user.id,
            )
        ).scalar_one_or_none()

        if existing_collection:
            print(f"[--] Sample collection already exists: {existing_collection.id}")
        else:
            collection = Collection(
                id=uuid.uuid4(),
                user_id=user.id,
                name="Insurance Claims Review",
                description="Car crash and damage footage for insurance claim verification",
            )
            session.add(collection)
            session.flush()
            print(f"[OK] Created sample collection: {collection.name}")

        session.commit()

        # Summary
        total_candidates = session.execute(select(CandidateVideo)).scalars().all()
        total_analyses = session.execute(select(VideoAnalysis)).scalars().all()
        total_searches = session.execute(select(Search)).scalars().all()

        print()
        print("=" * 60)
        print("Seed Summary")
        print("=" * 60)
        print(f"  Users:            1")
        print(f"  Candidate Videos: {len(total_candidates)}")
        print(f"  Video Analyses:   {len(total_analyses)}")
        print(f"  Searches:         {len(total_searches)}")
        print(f"  Collections:      1")
        print("=" * 60)
        print("Done!")

    except Exception as exc:
        session.rollback()
        print(f"[ERROR] Seed failed: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
