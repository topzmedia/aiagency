"""Tests for CSV ingestion adapter."""
from __future__ import annotations

import csv
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from sqlalchemy import StaticPool, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apps.api.models.base import Base
from apps.api.models.candidate_video import CandidateVideo
from workers.tasks.ingestion import _csv_adapter


@pytest.fixture
def sync_session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _write_csv(rows: list[dict], path: str):
    """Write rows to a CSV file."""
    if not rows:
        with open(path, "w") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestCSVImport:
    def test_valid_csv_import(self, sync_session):
        """Valid CSV rows should be imported as CandidateVideo records."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmppath = f.name
        try:
            rows = [
                {
                    "source_url": "https://example.com/v1",
                    "platform": "tiktok",
                    "creator_handle": "@test",
                    "caption_text": "Test video one",
                    "hashtags": "test,video",
                    "publish_date": "2025-01-01T00:00:00",
                    "language": "en",
                    "region_hint": "US",
                    "duration_sec": "30",
                },
                {
                    "source_url": "https://example.com/v2",
                    "platform": "youtube",
                    "creator_handle": "@test2",
                    "caption_text": "Test video two",
                    "hashtags": "test",
                    "publish_date": "2025-02-01T00:00:00",
                    "language": "en",
                    "region_hint": "US",
                    "duration_sec": "60",
                },
            ]
            _write_csv(rows, tmppath)

            imported, rejected, logs = _csv_adapter({"file_path": tmppath}, sync_session)
            assert imported == 2
            assert rejected == 0

            all_cv = sync_session.execute(select(CandidateVideo)).scalars().all()
            assert len(all_cv) == 2
            assert all_cv[0].platform in ("tiktok", "youtube")
        finally:
            os.unlink(tmppath)

    def test_missing_columns(self, sync_session):
        """Rows missing required source_url should be rejected."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmppath = f.name
        try:
            rows = [
                {
                    "platform": "tiktok",
                    "caption_text": "No URL here",
                },
            ]
            _write_csv(rows, tmppath)

            imported, rejected, logs = _csv_adapter({"file_path": tmppath}, sync_session)
            assert imported == 0
            assert rejected == 1
            assert any("missing source_url" in str(entry) for entry in logs)
        finally:
            os.unlink(tmppath)

    def test_partial_data(self, sync_session):
        """Rows with only source_url and platform should import with optional fields null."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmppath = f.name
        try:
            rows = [
                {
                    "source_url": "https://example.com/minimal",
                    "platform": "tiktok",
                    "creator_handle": "",
                    "caption_text": "",
                    "hashtags": "",
                    "publish_date": "",
                    "language": "",
                    "region_hint": "",
                    "duration_sec": "",
                },
            ]
            _write_csv(rows, tmppath)

            imported, rejected, logs = _csv_adapter({"file_path": tmppath}, sync_session)
            assert imported == 1
            assert rejected == 0

            cv = sync_session.execute(select(CandidateVideo)).scalar_one()
            assert cv.source_url == "https://example.com/minimal"
            assert cv.caption_text is None
            assert cv.duration_sec is None
        finally:
            os.unlink(tmppath)

    def test_nonexistent_file(self, sync_session):
        """Non-existent CSV path should return error log."""
        imported, rejected, logs = _csv_adapter({"file_path": "/nonexistent/file.csv"}, sync_session)
        assert imported == 0
        assert rejected == 0
        assert any("not found" in str(entry) for entry in logs)

    def test_invalid_duration(self, sync_session):
        """Invalid duration_sec should be treated as None, not crash."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            tmppath = f.name
        try:
            rows = [
                {
                    "source_url": "https://example.com/bad-dur",
                    "platform": "tiktok",
                    "duration_sec": "not_a_number",
                    "publish_date": "",
                    "caption_text": "test",
                    "hashtags": "",
                    "language": "en",
                    "region_hint": "US",
                    "creator_handle": "",
                },
            ]
            _write_csv(rows, tmppath)

            imported, rejected, logs = _csv_adapter({"file_path": tmppath}, sync_session)
            assert imported == 1
            cv = sync_session.execute(select(CandidateVideo)).scalar_one()
            assert cv.duration_sec is None
        finally:
            os.unlink(tmppath)
