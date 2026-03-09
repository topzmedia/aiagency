from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class IngestionJobCreate(BaseModel):
    source_type: str = Field(..., min_length=1, max_length=128)
    source_config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class IngestionJobResponse(BaseModel):
    id: uuid.UUID
    source_type: str
    source_config_json: dict[str, Any]
    status: str
    total_records: int
    imported_records: int
    rejected_records: int
    log_json: Optional[list[dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
