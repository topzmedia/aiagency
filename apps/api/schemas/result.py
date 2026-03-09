from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: uuid.UUID
    search_id: uuid.UUID
    candidate_video_id: uuid.UUID
    final_score: float
    rank_position: int
    accepted: bool
    reason_codes_json: Optional[list[str]] = None
    score_breakdown_json: Optional[dict[str, Any]] = None
    matched_segments_json: Optional[list[dict[str, Any]]] = None
    duplicate_group_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Inline candidate video info
    platform: Optional[str] = None
    source_url: Optional[str] = None
    creator_handle: Optional[str] = None
    caption_text: Optional[str] = None
    thumbnail_path: Optional[str] = None

    model_config = {"from_attributes": True}


class ResultExplainResponse(BaseModel):
    result_id: uuid.UUID
    final_score: float
    rank_position: int
    score_breakdown: Optional[dict[str, Any]] = None
    matched_segments: Optional[list[dict[str, Any]]] = None
    reason_codes: Optional[list[str]] = None

    model_config = {"from_attributes": True}


class ResultListResponse(BaseModel):
    items: list[ResultResponse]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}
