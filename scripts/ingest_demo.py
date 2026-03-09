"""Demo ingestion script.

Runs a CSV ingestion job using the sample_videos.csv seed data,
demonstrating the full ingestion pipeline.

Usage:
    python -m scripts.ingest_demo
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.api.config import settings
from apps.api.models.base import Base
from apps.api.models.ingestion_job import IngestionJob, IngestionStatus

SYNC_URL = settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
engine = create_engine(SYNC_URL, echo=False)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

SEED_CSV = Path(__file__).resolve().parent.parent / "data" / "seed" / "sample_videos.csv"


def main():
    """Create and dispatch an ingestion job for the sample CSV."""
    print("=" * 60)
    print("Content Finder - Demo Ingestion")
    print("=" * 60)

    if not SEED_CSV.exists():
        print(f"[ERROR] Seed CSV not found: {SEED_CSV}")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(engine)

    session = SessionFactory()
    try:
        # Create ingestion job record
        job = IngestionJob(
            id=uuid.uuid4(),
            source_type="csv",
            source_config_json={"file_path": str(SEED_CSV)},
            status=IngestionStatus.queued,
        )
        session.add(job)
        session.commit()
        print(f"[OK] Created ingestion job: {job.id}")

        # Try to dispatch to Celery
        try:
            from workers.tasks.ingestion import run_ingestion_job
            result = run_ingestion_job.delay(str(job.id))
            print(f"[OK] Dispatched to Celery worker (task_id={result.id})")
            print("     Monitor with: make worker-logs")
        except Exception as exc:
            print(f"[!!] Could not dispatch to Celery: {exc}")
            print("     Running synchronously instead...")

            # Run synchronously as fallback
            from workers.tasks.ingestion import _csv_adapter
            source_config = {"file_path": str(SEED_CSV)}
            imported, rejected, log_entries = _csv_adapter(source_config, session)

            job.status = IngestionStatus.completed
            job.imported_records = imported
            job.rejected_records = rejected
            job.total_records = imported + rejected
            job.log_json = log_entries
            session.commit()

            print(f"[OK] Ingestion completed synchronously:")
            print(f"     Imported: {imported}")
            print(f"     Rejected: {rejected}")

    except Exception as exc:
        session.rollback()
        print(f"[ERROR] Ingestion failed: {exc}")
        raise
    finally:
        session.close()

    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
