"""Demo seed ingestion adapter.

Creates sample candidate_video records with realistic metadata covering
several content categories.  Used for development, testing, and
demonstrations.  Also creates corresponding VideoAnalysis stubs.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Iterator

from apps.api.services.ingestion.base import (
    AbstractIngestionAdapter,
    CandidateVideoCreate,
    IngestionResult,
    RawRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

_DEMO_RECORDS: list[dict[str, Any]] = [
    # --- Car crash videos ---
    {
        "title": "Dashcam Car Crash Compilation",
        "platform": "youtube",
        "source_url": "https://youtube.com/watch?v=demo_crash_001",
        "creator_handle": "@dashcam_daily",
        "creator_name": "Dashcam Daily",
        "caption_text": "Incredible dashcam footage of a multi-car collision on the highway. The truck swerved and hit the median.",
        "hashtags": ["#dashcam", "#carcrash", "#accident", "#highway", "#collision"],
        "duration_sec": 47.3,
        "language": "en",
        "region_hint": "US",
        "category": "car_crash",
        "analysis_stub": {
            "objects": ["car", "truck", "road", "sky"],
            "scenes": ["road_highway"],
            "actions": ["collision", "driving"],
            "audio": ["impact", "screech"],
            "ocr_text": "DASHCAM 2024-01-15 14:32",
            "transcript": "Oh no, he's swerving! That truck just hit the median. Multiple vehicles involved.",
        },
    },
    {
        "title": "Intersection Fender Bender",
        "platform": "tiktok",
        "source_url": "https://tiktok.com/@witness_cam/video/demo_crash_002",
        "creator_handle": "@witness_cam",
        "creator_name": "Witness Cam",
        "caption_text": "Caught this fender bender at the intersection. Red light runner hit a turning vehicle.",
        "hashtags": ["#fenderbender", "#accident", "#intersection", "#redlight"],
        "duration_sec": 23.8,
        "language": "en",
        "region_hint": "US",
        "category": "car_crash",
        "analysis_stub": {
            "objects": ["car", "road", "building"],
            "scenes": ["outdoor_urban"],
            "actions": ["collision"],
            "audio": ["impact", "speech"],
            "ocr_text": "",
            "transcript": "Did you see that? He ran the red light!",
        },
    },
    # --- Luxury kitchen tours ---
    {
        "title": "Dream Kitchen Tour - Marble & Gold",
        "platform": "instagram",
        "source_url": "https://instagram.com/p/demo_kitchen_001",
        "creator_handle": "@luxe_interiors",
        "creator_name": "Luxe Interiors",
        "caption_text": "Tour of this stunning luxury kitchen featuring Calacatta marble countertops, custom cabinets, and designer pendant lights over the island.",
        "hashtags": ["#kitchendesign", "#luxury", "#marble", "#interiordesign", "#dreamkitchen"],
        "duration_sec": 62.1,
        "language": "en",
        "region_hint": "US",
        "category": "luxury_kitchen",
        "analysis_stub": {
            "objects": ["kitchen", "table"],
            "scenes": ["indoor_kitchen"],
            "actions": ["cooking"],
            "audio": ["speech", "music"],
            "ocr_text": "LUXE INTERIORS | Kitchen Tour",
            "transcript": "Welcome to this gorgeous kitchen. Notice the Calacatta marble on the island and these beautiful pendant lights.",
        },
    },
    {
        "title": "Modern Farmhouse Kitchen Reveal",
        "platform": "youtube",
        "source_url": "https://youtube.com/watch?v=demo_kitchen_002",
        "creator_handle": "@home_reno_pro",
        "creator_name": "Home Reno Pro",
        "caption_text": "Before and after of our modern farmhouse kitchen renovation. White shaker cabinets, quartz countertops, and a massive island with seating.",
        "hashtags": ["#kitchenreno", "#farmhouse", "#beforeandafter", "#homedecor"],
        "duration_sec": 185.5,
        "language": "en",
        "region_hint": "US",
        "category": "luxury_kitchen",
        "analysis_stub": {
            "objects": ["kitchen", "table", "person"],
            "scenes": ["indoor_kitchen", "residential_interior"],
            "actions": ["cooking", "walking"],
            "audio": ["speech", "music"],
            "ocr_text": "BEFORE | AFTER",
            "transcript": "Here's the kitchen before renovation. And now, look at this transformation. We went with white shaker cabinets and quartz countertops.",
        },
    },
    # --- Dogs in snow ---
    {
        "title": "Golden Retriever First Snow Day",
        "platform": "tiktok",
        "source_url": "https://tiktok.com/@puppy_life/video/demo_dog_001",
        "creator_handle": "@puppy_life",
        "creator_name": "Puppy Life",
        "caption_text": "Our golden retriever experiencing snow for the first time! Pure joy! 🐕❄️",
        "hashtags": ["#goldenretriever", "#firstsnow", "#puppy", "#dogsoftiktok", "#winter"],
        "duration_sec": 34.2,
        "language": "en",
        "region_hint": "US",
        "category": "dog_snow",
        "analysis_stub": {
            "objects": ["dog", "tree", "sky"],
            "scenes": ["snow_outdoors"],
            "actions": ["dog_playing"],
            "audio": ["bark"],
            "ocr_text": "",
            "transcript": "Look at him! He loves the snow! Good boy! Come here, buddy!",
        },
    },
    {
        "title": "Husky Pack Snow Run",
        "platform": "instagram",
        "source_url": "https://instagram.com/p/demo_dog_002",
        "creator_handle": "@arctic_huskies",
        "creator_name": "Arctic Huskies",
        "caption_text": "Nothing makes our huskies happier than fresh powder. Watch them sprint through the blizzard!",
        "hashtags": ["#husky", "#snowdog", "#blizzard", "#winterwonderland", "#dogpack"],
        "duration_sec": 45.0,
        "language": "en",
        "region_hint": "CA",
        "category": "dog_snow",
        "analysis_stub": {
            "objects": ["dog", "sky"],
            "scenes": ["snow_outdoors", "outdoor_rural"],
            "actions": ["dog_playing"],
            "audio": ["bark"],
            "ocr_text": "Arctic Huskies",
            "transcript": "",
        },
    },
    # --- Public arguments ---
    {
        "title": "Road Rage Confrontation",
        "platform": "twitter",
        "source_url": "https://twitter.com/i/status/demo_argue_001",
        "creator_handle": "@street_witness",
        "creator_name": "Street Witness",
        "caption_text": "This road rage incident escalated quickly. Two drivers got out and started yelling at each other after a near-miss.",
        "hashtags": ["#roadrage", "#confrontation", "#argument", "#caught"],
        "duration_sec": 38.7,
        "language": "en",
        "region_hint": "US",
        "category": "argument",
        "analysis_stub": {
            "objects": ["person", "car", "road"],
            "scenes": ["outdoor_urban"],
            "actions": ["arguing"],
            "audio": ["speech"],
            "ocr_text": "",
            "transcript": "Hey what are you doing? You almost hit me! Get out of the road! You're the one who cut me off!",
        },
    },
    {
        "title": "Store Dispute Goes Viral",
        "platform": "tiktok",
        "source_url": "https://tiktok.com/@viral_moments/video/demo_argue_002",
        "creator_handle": "@viral_moments",
        "creator_name": "Viral Moments",
        "caption_text": "Customer and manager get into a heated dispute over a return policy. Things got loud.",
        "hashtags": ["#publicfreakout", "#argument", "#karenstrike", "#retail", "#drama"],
        "duration_sec": 72.4,
        "language": "en",
        "region_hint": "US",
        "category": "argument",
        "analysis_stub": {
            "objects": ["person", "building"],
            "scenes": ["store"],
            "actions": ["arguing"],
            "audio": ["speech"],
            "ocr_text": "RETURNS",
            "transcript": "I want to speak to your manager! Ma'am please calm down. I will not calm down, this is unacceptable!",
        },
    },
    # --- Couple / family scenes ---
    {
        "title": "Couple Cooking Together",
        "platform": "instagram",
        "source_url": "https://instagram.com/p/demo_couple_001",
        "creator_handle": "@happy_home",
        "creator_name": "Happy Home",
        "caption_text": "Saturday morning pancakes with my love. Nothing beats cooking together in our kitchen.",
        "hashtags": ["#couplegoals", "#cooking", "#breakfast", "#love", "#kitchen"],
        "duration_sec": 55.9,
        "language": "en",
        "region_hint": "US",
        "category": "couple",
        "analysis_stub": {
            "objects": ["person", "kitchen", "table"],
            "scenes": ["indoor_kitchen", "residential_interior"],
            "actions": ["smiling_together", "cooking"],
            "audio": ["speech", "music"],
            "ocr_text": "",
            "transcript": "You flip them, I'll add the berries. This is the best part of the weekend.",
        },
    },
    {
        "title": "Family Game Night Laughs",
        "platform": "youtube",
        "source_url": "https://youtube.com/watch?v=demo_couple_002",
        "creator_handle": "@family_fun",
        "creator_name": "Family Fun Channel",
        "caption_text": "Our family game night got out of hand! So many laughs and smiles. This is what home is about.",
        "hashtags": ["#familytime", "#gamenight", "#laughing", "#happyfamily", "#home"],
        "duration_sec": 124.0,
        "language": "en",
        "region_hint": "US",
        "category": "couple",
        "analysis_stub": {
            "objects": ["person", "table"],
            "scenes": ["residential_interior"],
            "actions": ["smiling_together", "celebration"],
            "audio": ["cheering", "speech"],
            "ocr_text": "GAME NIGHT",
            "transcript": "Your turn! Roll the dice! Ha, you landed on my hotel! Pay up! This is so fun.",
        },
    },
]


class DemoSeedAdapter(AbstractIngestionAdapter):
    """Create sample candidate videos for demonstration purposes."""

    @property
    def source_name(self) -> str:
        return "demo_seed"

    def validate_config(self, config: dict[str, Any]) -> bool:
        # No special config required; accepts optional category filter
        return True

    def enumerate_records(self, config: dict[str, Any]) -> Iterator[RawRecord]:
        category_filter = config.get("category")
        base_date = datetime(2024, 6, 1, 12, 0, 0)

        for idx, record in enumerate(_DEMO_RECORDS):
            if category_filter and record.get("category") != category_filter:
                continue

            # Add a synthetic publish date
            record_data = dict(record)
            record_data["publish_date"] = (base_date + timedelta(days=idx * 3)).isoformat()

            yield RawRecord(
                source_ref=f"demo_{idx:03d}:{record['title']}",
                data=record_data,
            )

    def normalize_record(self, raw: RawRecord) -> CandidateVideoCreate:
        data = raw.data

        publish_date = None
        if data.get("publish_date"):
            try:
                publish_date = datetime.fromisoformat(data["publish_date"])
            except (ValueError, TypeError):
                pass

        return CandidateVideoCreate(
            external_id=None,
            platform=data.get("platform", "unknown"),
            source_url=data["source_url"],
            canonical_url=data["source_url"],
            creator_handle=data.get("creator_handle"),
            creator_name=data.get("creator_name"),
            caption_text=data.get("caption_text"),
            hashtags_json=data.get("hashtags"),
            publish_date=publish_date,
            duration_sec=data.get("duration_sec"),
            language=data.get("language"),
            region_hint=data.get("region_hint"),
            local_media_path=None,
            metadata_json={
                "category": data.get("category"),
                "title": data.get("title"),
                "analysis_stub": data.get("analysis_stub"),
            },
            ingestion_source="demo_seed",
        )

    def run(self, config: dict[str, Any]) -> IngestionResult:
        """Override run to also collect analysis stubs for downstream use."""
        result = super().run(config)

        # Attach analysis stubs to the result for callers that want to
        # persist VideoAnalysis records alongside the candidate_videos.
        analysis_stubs: list[dict[str, Any]] = []
        for idx, record in enumerate(_DEMO_RECORDS):
            category_filter = config.get("category")
            if category_filter and record.get("category") != category_filter:
                continue
            stub = record.get("analysis_stub", {})
            if stub and idx < len(result.created_ids):
                analysis_stubs.append({
                    "candidate_video_id": result.created_ids[idx],
                    **stub,
                })

        # Store on result for external access
        result.__dict__["analysis_stubs"] = analysis_stubs

        logger.info(
            "Demo seed: created %d candidates with %d analysis stubs",
            result.created, len(analysis_stubs),
        )
        return result
