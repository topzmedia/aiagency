from __future__ import annotations

import csv
import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.candidate_video import CandidateVideo
from apps.api.models.result_ranking import ResultRanking
from apps.api.models.search import Search, SearchStatus
from apps.api.schemas.search import (
    SearchCreate,
    SearchListResponse,
    SearchResponse,
    SearchResultResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/searches", tags=["searches"])


@router.post("", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def create_search(payload: SearchCreate, db: AsyncSession = Depends(get_db)) -> Search:
    search = Search(
        raw_query=payload.raw_query,
        user_id=payload.user_id,
        region=payload.region,
        language=payload.language,
        platforms=payload.platforms,
        include_filters_json=payload.include_filters,
        exclude_filters_json=payload.exclude_filters,
        date_from=payload.date_from,
        date_to=payload.date_to,
        max_results=payload.max_results,
        confidence_threshold=payload.confidence_threshold,
        status=SearchStatus.queued,
    )
    db.add(search)
    await db.flush()
    await db.refresh(search)

    # Dispatch celery task (best-effort; worker may not be running)
    try:
        from celery import Celery
        from apps.api.config import settings

        celery_app = Celery(broker=settings.REDIS_URL)
        celery_app.send_task("workers.tasks.search.process_search", args=[str(search.id)])
        logger.info("Dispatched search task for %s", search.id)
    except Exception:
        logger.warning("Could not dispatch celery task for search %s – worker may be offline", search.id)

    return search


@router.get("", response_model=SearchListResponse)
async def list_searches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Search).order_by(Search.created_at.desc())
    count_query = select(func.count()).select_from(Search)

    if status_filter:
        query = query.where(Search.status == status_filter)
        count_query = count_query.where(Search.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{search_id}", response_model=SearchResponse)
async def get_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Search:
    result = await db.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")
    return search


@router.get("/{search_id}/results", response_model=SearchResultResponse)
async def get_search_results(
    search_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")

    query = (
        select(ResultRanking)
        .where(ResultRanking.search_id == search_id)
        .order_by(ResultRanking.rank_position)
    )
    count_query = select(func.count()).select_from(ResultRanking).where(ResultRanking.search_id == search_id)

    if min_score is not None:
        query = query.where(ResultRanking.final_score >= min_score)
        count_query = count_query.where(ResultRanking.final_score >= min_score)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.offset((page - 1) * page_size).limit(page_size)
    rankings_result = await db.execute(query)
    rankings = list(rankings_result.scalars().all())

    # Hydrate with candidate video info
    results_list = []
    for r in rankings:
        cv_result = await db.execute(select(CandidateVideo).where(CandidateVideo.id == r.candidate_video_id))
        cv = cv_result.scalar_one_or_none()
        entry = {
            "id": str(r.id),
            "search_id": str(r.search_id),
            "candidate_video_id": str(r.candidate_video_id),
            "final_score": r.final_score,
            "rank_position": r.rank_position,
            "accepted": r.accepted,
            "reason_codes_json": r.reason_codes_json,
            "score_breakdown_json": r.score_breakdown_json,
            "matched_segments_json": r.matched_segments_json,
            "duplicate_group_id": str(r.duplicate_group_id) if r.duplicate_group_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "platform": cv.platform if cv else None,
            "source_url": cv.source_url if cv else None,
            "creator_handle": cv.creator_handle if cv else None,
            "caption_text": cv.caption_text if cv else None,
            "thumbnail_path": cv.thumbnail_path if cv else None,
        }
        results_list.append(entry)

    return {
        "search": search,
        "results": results_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{search_id}/rerank", response_model=SearchResponse)
async def rerank_search(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Search:
    result = await db.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")

    search.status = SearchStatus.queued
    search.progress_percent = 0
    await db.flush()
    await db.refresh(search)

    try:
        from celery import Celery
        from apps.api.config import settings

        celery_app = Celery(broker=settings.REDIS_URL)
        celery_app.send_task("workers.tasks.search.rerank_search", args=[str(search.id)])
        logger.info("Dispatched rerank task for %s", search.id)
    except Exception:
        logger.warning("Could not dispatch celery rerank task for search %s", search.id)

    return search


@router.get("/{search_id}/export.csv")
async def export_csv(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    result = await db.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")

    rankings_result = await db.execute(
        select(ResultRanking)
        .where(ResultRanking.search_id == search_id)
        .order_by(ResultRanking.rank_position)
    )
    rankings = list(rankings_result.scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "rank", "final_score", "accepted", "candidate_video_id",
        "platform", "source_url", "creator_handle", "caption_text",
    ])

    for r in rankings:
        cv_result = await db.execute(select(CandidateVideo).where(CandidateVideo.id == r.candidate_video_id))
        cv = cv_result.scalar_one_or_none()
        writer.writerow([
            r.rank_position,
            r.final_score,
            r.accepted,
            str(r.candidate_video_id),
            cv.platform if cv else "",
            cv.source_url if cv else "",
            cv.creator_handle if cv else "",
            (cv.caption_text or "")[:200] if cv else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=search_{search_id}_results.csv"},
    )


@router.get("/{search_id}/export.json")
async def export_json(search_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    result = await db.execute(select(Search).where(Search.id == search_id))
    search = result.scalar_one_or_none()
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found")

    rankings_result = await db.execute(
        select(ResultRanking)
        .where(ResultRanking.search_id == search_id)
        .order_by(ResultRanking.rank_position)
    )
    rankings = list(rankings_result.scalars().all())

    export_data = {
        "search_id": str(search.id),
        "raw_query": search.raw_query,
        "status": search.status.value if hasattr(search.status, "value") else str(search.status),
        "total_results": search.total_results,
        "results": [],
    }

    for r in rankings:
        cv_result = await db.execute(select(CandidateVideo).where(CandidateVideo.id == r.candidate_video_id))
        cv = cv_result.scalar_one_or_none()
        export_data["results"].append({
            "rank": r.rank_position,
            "final_score": r.final_score,
            "accepted": r.accepted,
            "candidate_video_id": str(r.candidate_video_id),
            "platform": cv.platform if cv else None,
            "source_url": cv.source_url if cv else None,
            "creator_handle": cv.creator_handle if cv else None,
            "caption_text": cv.caption_text if cv else None,
            "score_breakdown": r.score_breakdown_json,
            "matched_segments": r.matched_segments_json,
        })

    return JSONResponse(content=export_data)
