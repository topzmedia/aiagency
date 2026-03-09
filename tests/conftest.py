"""Pytest fixtures for Content Finder tests."""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure project root on path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from apps.api.models.base import Base
from apps.api.models.user import User
from apps.api.models.candidate_video import CandidateVideo
from apps.api.models.video_analysis import VideoAnalysis, AnalysisStatus
from apps.api.models.search import Search, SearchStatus
from apps.api.models.result_ranking import ResultRanking
from apps.api.models.collection import Collection
from apps.api.models.ingestion_job import IngestionJob, IngestionStatus


# ---------------------------------------------------------------------------
# Async DB fixtures (SQLite in-memory for fast tests)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create an async in-memory SQLite engine for tests."""
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async DB session for each test."""
    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Sync DB fixtures (for workers/celery tests)
# ---------------------------------------------------------------------------

SYNC_TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def sync_engine():
    """Create a sync in-memory SQLite engine."""
    engine = create_engine(
        SYNC_TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Provide a sync DB session for each test."""
    factory = sessionmaker(bind=sync_engine, expire_on_commit=False)
    session = factory()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def app(async_engine):
    """Create a FastAPI test app with overridden DB dependency."""
    from apps.api.main import app as fastapi_app
    from apps.api.database import get_db

    factory = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    """Provide an async HTTP test client."""
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="test@example.com")
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def sample_candidates(db_session: AsyncSession) -> list[CandidateVideo]:
    candidates = []
    data = [
        {
            "platform": "tiktok",
            "source_url": "https://example.com/test/crash-001",
            "creator_handle": "@test_crashes",
            "caption_text": "Car crash on highway caught by dashcam camera",
            "hashtags_json": ["dashcam", "carcrash", "accident"],
            "duration_sec": 45.0,
            "language": "en",
            "region_hint": "US",
            "ingestion_source": "test",
        },
        {
            "platform": "youtube",
            "source_url": "https://example.com/test/kitchen-001",
            "creator_handle": "@test_homes",
            "caption_text": "Luxury kitchen tour with marble countertops and custom cabinets",
            "hashtags_json": ["kitchen", "luxury", "hometour"],
            "duration_sec": 120.0,
            "language": "en",
            "region_hint": "US",
            "ingestion_source": "test",
        },
        {
            "platform": "instagram",
            "source_url": "https://example.com/test/dogs-001",
            "creator_handle": "@test_pets",
            "caption_text": "Dogs playing in snow winter wonderland puppy zoomies",
            "hashtags_json": ["dogs", "snow", "winter", "puppies"],
            "duration_sec": 38.0,
            "language": "en",
            "region_hint": "US",
            "ingestion_source": "test",
        },
    ]
    for d in data:
        cv = CandidateVideo(id=uuid.uuid4(), **d, metadata_json={})
        db_session.add(cv)
        candidates.append(cv)
    await db_session.flush()
    return candidates


@pytest_asyncio.fixture
async def sample_analyses(db_session: AsyncSession, sample_candidates: list[CandidateVideo]) -> list[VideoAnalysis]:
    analyses = []
    templates = [
        {
            "objects_json": [{"label": "car", "confidence": 0.95}, {"label": "road", "confidence": 0.9}],
            "actions_json": [{"label": "crash", "confidence": 0.92}],
            "scenes_json": [{"label": "road_highway", "confidence": 0.93}],
            "audio_events_json": [{"label": "impact", "confidence": 0.91}],
        },
        {
            "objects_json": [{"label": "kitchen", "confidence": 0.97}, {"label": "marble", "confidence": 0.85}],
            "actions_json": [],
            "scenes_json": [{"label": "indoor_kitchen", "confidence": 0.96}],
            "audio_events_json": [{"label": "speech", "confidence": 0.75}],
        },
        {
            "objects_json": [{"label": "dog", "confidence": 0.96}, {"label": "snow", "confidence": 0.94}],
            "actions_json": [{"label": "play", "confidence": 0.92}, {"label": "run", "confidence": 0.85}],
            "scenes_json": [{"label": "snow_outdoors", "confidence": 0.95}],
            "audio_events_json": [{"label": "bark", "confidence": 0.88}],
        },
    ]
    for cv, tmpl in zip(sample_candidates, templates):
        analysis = VideoAnalysis(
            id=uuid.uuid4(),
            candidate_video_id=cv.id,
            status=AnalysisStatus.completed,
            **tmpl,
        )
        db_session.add(analysis)
        analyses.append(analysis)
    await db_session.flush()
    return analyses


# ---------------------------------------------------------------------------
# Mock services
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_celery(monkeypatch):
    """Mock Celery task dispatch so it doesn't require a running broker."""
    mock_delay = MagicMock(return_value=MagicMock(id="mock-task-id"))
    monkeypatch.setattr(
        "workers.tasks.search.process_search.delay", mock_delay, raising=False,
    )
    monkeypatch.setattr(
        "workers.tasks.ingestion.run_ingestion_job.delay", mock_delay, raising=False,
    )
    return mock_delay
