"""Tests for the query interpreter service."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.services.query_interpreter import interpret_query, ParsedQuery


class TestBasicQueryParsing:
    def test_basic_query_parsing(self):
        result = interpret_query("car crash on highway")
        assert isinstance(result, ParsedQuery)
        assert result.raw_query == "car crash on highway"
        assert len(result.entities) > 0
        assert len(result.actions) > 0

    def test_car_crash_query(self):
        result = interpret_query("car crash dashcam footage")
        assert "car" in result.entities
        assert "crash" in result.actions
        assert "road_highway" in result.scenes
        assert "impact" in result.audio_events
        # Should have synonyms for car crash
        assert len(result.synonyms) > 0
        assert any(s in result.synonyms for s in ["collision", "wreck", "accident"])

    def test_luxury_kitchen_query(self):
        result = interpret_query("luxury kitchen marble island cabinets")
        assert "kitchen" in result.entities
        assert "indoor_kitchen" in result.scenes
        # Luxury synonym expansion
        assert len(result.synonyms) > 0

    def test_exclude_filters(self):
        result = interpret_query(
            "car crash footage",
            exclude_filters={"terms": ["music video", "compilation"]},
        )
        assert "music video" in result.exclude
        assert "compilation" in result.exclude

    def test_synonym_expansion(self):
        result = interpret_query("dog playing in snow")
        assert "dog" in result.entities
        assert "play" in result.actions
        # Dog synonyms
        synonyms_set = set(result.synonyms)
        assert any(s in synonyms_set for s in ["puppy", "canine", "pet"])
        # Snow synonyms
        assert any(s in synonyms_set for s in ["winter", "blizzard", "frost"])

    def test_empty_query(self):
        result = interpret_query("")
        assert result.raw_query == ""
        assert result.entities == []
        assert result.actions == []
        assert result.scenes == []
        assert result.synonyms == []

    def test_include_filters_examples(self):
        result = interpret_query(
            "car crash",
            include_filters={"examples": ["example1.mp4"]},
        )
        assert "example1.mp4" in result.positive_examples

    def test_audio_events_detected(self):
        result = interpret_query("dog barking loudly")
        assert "bark" in result.audio_events

    def test_scene_inference(self):
        result = interpret_query("snow winter blizzard outdoors")
        assert "snow_outdoors" in result.scenes

    def test_ocr_terms_populated(self):
        result = interpret_query("car crash")
        assert len(result.ocr_terms) > 0
        assert "car" in result.ocr_terms
