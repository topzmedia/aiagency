"""Tests for the scoring engine used in search ranking."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from workers.tasks.search import _score_candidate


def _make_candidate(
    caption_text="",
    hashtags_json=None,
    publish_date=None,
):
    """Create a mock candidate video object."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        caption_text=caption_text,
        hashtags_json=hashtags_json or [],
        publish_date=publish_date,
    )


def _make_analysis(
    status="completed",
    objects_json=None,
    scenes_json=None,
    actions_json=None,
    transcript_text=None,
    ocr_text_json=None,
    audio_events_json=None,
):
    """Create a mock analysis object."""
    status_obj = SimpleNamespace(value=status)
    return SimpleNamespace(
        status=status_obj,
        objects_json=objects_json or [],
        scenes_json=scenes_json or [],
        actions_json=actions_json or [],
        transcript_text=transcript_text,
        ocr_text_json=ocr_text_json or [],
        audio_events_json=audio_events_json or [],
    )


def _make_query(
    entities=None,
    actions=None,
    scenes=None,
    synonyms=None,
    audio_events=None,
    exclude=None,
):
    return {
        "entities": entities or [],
        "actions": actions or [],
        "scenes": scenes or [],
        "synonyms": synonyms or [],
        "audio_events": audio_events or [],
        "exclude": exclude or [],
    }


class TestScoring:
    def test_perfect_score(self):
        """A candidate that matches all query terms should get a high score."""
        candidate = _make_candidate(
            caption_text="car crash dashcam highway accident collision",
            hashtags_json=["dashcam", "carcrash"],
        )
        analysis = _make_analysis(
            objects_json=[{"label": "car"}, {"label": "road"}],
            scenes_json=[{"label": "road_highway"}],
            actions_json=[{"label": "crash"}],
            audio_events_json=[{"label": "impact"}],
        )
        query = _make_query(
            entities=["car"],
            actions=["crash"],
            scenes=["road_highway"],
            synonyms=["collision", "accident", "dashcam"],
            audio_events=["impact"],
        )
        score, breakdown, reasons = _score_candidate(candidate, analysis, query)
        assert score > 0.5
        assert "caption_relevance" in breakdown
        assert "analysis_relevance" in breakdown
        assert len(reasons) > 0

    def test_zero_score(self):
        """A candidate with no matching terms should get zero or near-zero."""
        candidate = _make_candidate(
            caption_text="cooking recipe tutorial",
            hashtags_json=["cooking"],
        )
        analysis = _make_analysis(
            objects_json=[{"label": "food"}],
            scenes_json=[{"label": "indoor_kitchen"}],
        )
        query = _make_query(
            entities=["car"],
            actions=["crash"],
            scenes=["road_highway"],
            synonyms=["collision"],
        )
        score, breakdown, reasons = _score_candidate(candidate, analysis, query)
        assert score < 0.1

    def test_partial_match(self):
        """A candidate matching some terms should get a moderate score."""
        candidate = _make_candidate(
            caption_text="car driving on highway at sunset",
            hashtags_json=["driving", "highway"],
        )
        analysis = _make_analysis(
            objects_json=[{"label": "car"}, {"label": "road"}],
            scenes_json=[{"label": "road_highway"}],
        )
        query = _make_query(
            entities=["car"],
            actions=["crash"],
            scenes=["road_highway"],
            synonyms=["collision", "accident"],
        )
        score, breakdown, reasons = _score_candidate(candidate, analysis, query)
        assert 0.1 < score < 0.8

    def test_penalty_application(self):
        """Excluded terms should reduce the score."""
        candidate = _make_candidate(
            caption_text="car crash music video compilation",
            hashtags_json=["carcrash", "musicvideo"],
        )
        analysis = _make_analysis()
        query = _make_query(
            entities=["car"],
            actions=["crash"],
            exclude=["music video"],
        )
        score, breakdown, reasons = _score_candidate(candidate, analysis, query)
        assert breakdown["penalty"] < 0
        assert any("penalty" in r for r in reasons)

    def test_reason_codes_generation(self):
        """Score function should generate descriptive reason codes."""
        candidate = _make_candidate(
            caption_text="dog playing in snow",
            hashtags_json=["dogs", "snow"],
        )
        analysis = _make_analysis(
            objects_json=[{"label": "dog"}, {"label": "snow"}],
            scenes_json=[{"label": "snow_outdoors"}],
            audio_events_json=[{"label": "bark"}],
        )
        query = _make_query(
            entities=["dog", "snow"],
            actions=["play"],
            scenes=["snow_outdoors"],
            synonyms=["puppy", "winter"],
            audio_events=["bark"],
        )
        score, breakdown, reasons = _score_candidate(candidate, analysis, query)
        assert len(reasons) > 0
        assert any("caption_match" in r for r in reasons)

    def test_threshold_filtering(self):
        """Scores below threshold should be filterable."""
        candidate = _make_candidate(caption_text="random unrelated content")
        analysis = _make_analysis()
        query = _make_query(
            entities=["car"],
            actions=["crash"],
        )
        score, _, _ = _score_candidate(candidate, analysis, query)
        threshold = 0.3
        assert score < threshold

    def test_no_analysis_still_scores(self):
        """Candidates without analysis should still get caption-based scores."""
        candidate = _make_candidate(
            caption_text="car crash dashcam footage",
        )
        query = _make_query(
            entities=["car"],
            actions=["crash"],
            synonyms=["dashcam"],
        )
        score, breakdown, reasons = _score_candidate(candidate, None, query)
        assert score > 0.0
        assert breakdown["analysis_relevance"] == 0.0
