"""Synchronous database session factory for Celery workers.

Celery workers cannot use async sessions reliably, so we provide a plain
synchronous SQLAlchemy session factory here.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_ASYNC_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/contentfinder",
)

# Convert async URL to sync
SYNC_DATABASE_URL = _ASYNC_URL.replace("+asyncpg", "").replace("+aiosqlite", "")

engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

SyncSessionFactory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_sync_session() -> Session:
    """Return a new synchronous database session."""
    return SyncSessionFactory()
