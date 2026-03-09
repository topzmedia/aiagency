from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    user_id: Optional[uuid.UUID] = None
    search_id: uuid.UUID
    candidate_video_id: uuid.UUID
    label: str = Field(..., pattern=r"^(very_relevant|somewhat_relevant|irrelevant)$")
    reason: Optional[str] = None

    model_config = {"from_attributes": True}


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    search_id: uuid.UUID
    candidate_video_id: uuid.UUID
    label: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
