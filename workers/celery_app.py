"""Celery application configuration for Content Finder."""
from __future__ import annotations

import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = Celery(
    "content_finder",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={
        "workers.tasks.ingestion.*": {"queue": "ingestion"},
        "workers.tasks.analysis.*": {"queue": "analysis"},
        "workers.tasks.search.*": {"queue": "search"},
        "workers.tasks.export.*": {"queue": "default"},
    },
)

app.autodiscover_tasks(["workers.tasks"])
