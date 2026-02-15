from datetime import datetime

from pydantic import BaseModel


class QueueItemSummaryResponse(BaseModel):
    id: int
    user_id: int
    status: str
    source_type: str
    source_info: str
    error_message: str | None
    order_id: int | None
    cloned_from_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueItemResponse(QueueItemSummaryResponse):
    raw_data: dict
    extracted_data: dict | None


class QueueItemListResponse(BaseModel):
    items: list[QueueItemSummaryResponse]
    total: int
    page: int
    per_page: int


class QueueStatsResponse(BaseModel):
    queued: int
    processing: int
    completed: int
    failed: int
