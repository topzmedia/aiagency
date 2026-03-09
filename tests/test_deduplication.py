"""Tests for deduplication logic."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers.tasks.search import _deduplicate_results


class TestDeduplication:
    def test_exact_duplicate_detection(self):
        """Exact duplicate captions should be grouped."""
        rankings = [
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.9,
                "caption_text": "Car crash on highway caught by dashcam camera footage",
            },
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.85,
                "caption_text": "Car crash on highway caught by dashcam camera footage",
            },
        ]
        result = _deduplicate_results(rankings, session=None)
        # First one should not be a duplicate
        assert result[0]["duplicate_group_key"] is None
        # Second one should be flagged as duplicate
        assert result[1]["duplicate_group_key"] is not None

    def test_near_duplicate_grouping(self):
        """Captions with >80% token overlap should be grouped as near-duplicates."""
        rankings = [
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.9,
                "caption_text": "Amazing car crash caught on dashcam highway footage compilation",
            },
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.85,
                "caption_text": "Incredible car crash caught on dashcam highway footage compilation",
            },
        ]
        result = _deduplicate_results(rankings, session=None)
        # Should detect near-duplicate
        assert result[1]["duplicate_group_key"] is not None

    def test_different_videos(self):
        """Completely different captions should not be grouped."""
        rankings = [
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.9,
                "caption_text": "Car crash on highway caught by dashcam",
            },
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.85,
                "caption_text": "Luxury kitchen tour with marble countertops and pendant lights",
            },
        ]
        result = _deduplicate_results(rankings, session=None)
        assert result[0]["duplicate_group_key"] is None
        assert result[1]["duplicate_group_key"] is None

    def test_empty_input(self):
        """Empty rankings list should return empty."""
        result = _deduplicate_results([], session=None)
        assert result == []

    def test_single_entry(self):
        """Single entry should not be flagged as duplicate."""
        rankings = [
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.9,
                "caption_text": "Car crash caught on camera",
            },
        ]
        result = _deduplicate_results(rankings, session=None)
        assert result[0]["duplicate_group_key"] is None

    def test_empty_captions(self):
        """Entries with empty captions should not crash dedup."""
        rankings = [
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.9,
                "caption_text": "",
            },
            {
                "candidate_video_id": str(uuid.uuid4()),
                "final_score": 0.85,
                "caption_text": "",
            },
        ]
        result = _deduplicate_results(rankings, session=None)
        assert len(result) == 2
