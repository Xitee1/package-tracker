from typing import Optional
from pydantic import BaseModel, EmailStr


class NotifyEmailConfigRequest(BaseModel):
    email: EmailStr


class NotifyEmailConfigResponse(BaseModel):
    enabled: bool
    email: Optional[str] = None
    verified: bool = False
    events: list[str] = []

    model_config = {"from_attributes": True}


class NotifyEmailEventsRequest(BaseModel):
    events: list[str]


class NotifyEmailToggleRequest(BaseModel):
    enabled: bool
