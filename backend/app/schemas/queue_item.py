from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QueueItemResponse(BaseModel):
    id: int
    user_id: int
    status: str
    source_type: str
    source_info: str
    raw_data: dict
    extracted_data: dict | None
    error_message: str | None
    order_id: int | None
    cloned_from_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueItemListResponse(BaseModel):
    items: list[QueueItemResponse]
    total: int
    page: int
    per_page: int


class QueueStatsResponse(BaseModel):
    queued: int
    processing: int
    completed: int
    failed: int
