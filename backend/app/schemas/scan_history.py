from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EmailScanResponse(BaseModel):
    id: int
    account_id: int
    account_name: str | None = None
    folder_path: str
    email_uid: int
    message_id: str
    subject: str
    sender: str
    email_date: datetime | None
    is_relevant: bool
    llm_raw_response: dict | None
    order_id: int | None
    rescan_queued: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailScanListResponse(BaseModel):
    items: list[EmailScanResponse]
    total: int
    page: int
    per_page: int


class EmailContentResponse(BaseModel):
    subject: str
    sender: str
    date: str | None
    body_text: str


class ScanHistorySettingsResponse(BaseModel):
    max_age_days: int
    max_per_user: int
    cleanup_interval_hours: float

    model_config = {"from_attributes": True}


class UpdateScanHistorySettingsRequest(BaseModel):
    max_age_days: int | None = None
    max_per_user: int | None = None
    cleanup_interval_hours: float | None = None
