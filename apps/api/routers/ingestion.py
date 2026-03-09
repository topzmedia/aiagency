from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.ingestion_job import IngestionJob, IngestionStatus
from apps.api.schemas.ingestion import IngestionJobCreate, IngestionJobResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingestion/jobs", tags=["ingestion"])


@router.post("", response_model=IngestionJobResponse, status_code=status.HTTP_201_CREATED)
async def create_ingestion_job(
    payload: IngestionJobCreate,
    db: AsyncSession = Depends(get_db),
) -> IngestionJob:
    job = IngestionJob(
        source_type=payload.source_type,
        source_config_json=payload.source_config,
        status=IngestionStatus.queued,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    try:
        from celery import Celery
        from apps.api.config import settings

        celery_app = Celery(broker=settings.REDIS_URL)
        celery_app.send_task("workers.tasks.ingestion.run_ingestion_job", args=[str(job.id)])
        logger.info("Dispatched ingestion task for job %s", job.id)
    except Exception:
        logger.warning("Could not dispatch celery ingestion task for job %s", job.id)

    return job


@router.get("", response_model=list[IngestionJobResponse])
async def list_ingestion_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[IngestionJob]:
    query = (
        select(IngestionJob)
        .order_by(IngestionJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{job_id}", response_model=IngestionJobResponse)
async def get_ingestion_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> IngestionJob:
    result = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found")
    return job
