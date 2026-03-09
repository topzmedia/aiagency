from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchCreate(BaseModel):
    raw_query: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[uuid.UUID] = None
    region: Optional[str] = None
    language: Optional[str] = None
    platforms: Optional[list[str]] = None
    include_filters: Optional[dict[str, Any]] = None
    exclude_filters: Optional[dict[str, Any]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    max_results: int = Field(default=50, ge=1, le=500)
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    raw_query: str
    normalized_query_json: Optional[dict[str, Any]] = None
    region: Optional[str] = None
    language: Optional[str] = None
    platforms: Optional[list[str]] = None
    include_filters_json: Optional[dict[str, Any]] = None
    exclude_filters_json: Optional[dict[str, Any]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    max_results: int
    confidence_threshold: float
    status: str
    progress_percent: int
    total_candidates: int
    total_analyzed: int
    total_results: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchListResponse(BaseModel):
    items: list[SearchResponse]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}


class SearchResultResponse(BaseModel):
    search: SearchResponse
    results: list[dict[str, Any]]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}
