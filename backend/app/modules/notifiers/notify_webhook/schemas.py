from typing import Optional
from pydantic import BaseModel, HttpUrl


class WebhookConfigRequest(BaseModel):
    url: HttpUrl
    auth_header: Optional[str] = None


class WebhookConfigResponse(BaseModel):
    enabled: bool
    url: Optional[str] = None
    has_auth_header: bool = False
    events: list[str] = []


class WebhookEventsRequest(BaseModel):
    events: list[str]


class WebhookToggleRequest(BaseModel):
    enabled: bool


class WebhookTestRequest(BaseModel):
    url: HttpUrl
    auth_header: Optional[str] = None
