from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.database import get_db
from apps.api.models.candidate_video import CandidateVideo
from apps.api.models.feedback import FeedbackLabel, UserFeedback
from apps.api.models.result_ranking import ResultRanking
from apps.api.schemas.feedback import FeedbackCreate, FeedbackResponse
from apps.api.schemas.result import ResultExplainResponse, ResultResponse

router = APIRouter(prefix="/api/results", tags=["results"])


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(result_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(ResultRanking).where(ResultRanking.id == result_id))
    ranking = result.scalar_one_or_none()
    if not ranking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    cv_result = await db.execute(
        select(CandidateVideo).where(CandidateVideo.id == ranking.candidate_video_id)
    )
    cv = cv_result.scalar_one_or_none()

    return {
        "id": ranking.id,
        "search_id": ranking.search_id,
        "candidate_video_id": ranking.candidate_video_id,
        "final_score": ranking.final_score,
        "rank_position": ranking.rank_position,
        "accepted": ranking.accepted,
        "reason_codes_json": ranking.reason_codes_json,
        "score_breakdown_json": ranking.score_breakdown_json,
        "matched_segments_json": ranking.matched_segments_json,
        "duplicate_group_id": ranking.duplicate_group_id,
        "created_at": ranking.created_at,
        "updated_at": ranking.updated_at,
        "platform": cv.platform if cv else None,
        "source_url": cv.source_url if cv else None,
        "creator_handle": cv.creator_handle if cv else None,
        "caption_text": cv.caption_text if cv else None,
        "thumbnail_path": cv.thumbnail_path if cv else None,
    }


@router.post("/{result_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    result_id: uuid.UUID,
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
) -> UserFeedback:
    result = await db.execute(select(ResultRanking).where(ResultRanking.id == result_id))
    ranking = result.scalar_one_or_none()
    if not ranking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    feedback = UserFeedback(
        user_id=payload.user_id,
        search_id=payload.search_id,
        candidate_video_id=payload.candidate_video_id,
        label=FeedbackLabel(payload.label),
        reason=payload.reason,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)
    return feedback


@router.get("/{result_id}/explain", response_model=ResultExplainResponse)
async def explain_result(result_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(ResultRanking).where(ResultRanking.id == result_id))
    ranking = result.scalar_one_or_none()
    if not ranking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

    return {
        "result_id": ranking.id,
        "final_score": ranking.final_score,
        "rank_position": ranking.rank_position,
        "score_breakdown": ranking.score_breakdown_json,
        "matched_segments": ranking.matched_segments_json,
        "reason_codes": ranking.reason_codes_json,
    }
