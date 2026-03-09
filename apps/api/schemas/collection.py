from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    user_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class CollectionResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    model_config = {"from_attributes": True}


class CollectionItemCreate(BaseModel):
    candidate_video_id: uuid.UUID
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class CollectionItemResponse(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    candidate_video_id: uuid.UUID
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
