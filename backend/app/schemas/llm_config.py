from pydantic import BaseModel
from typing import Optional


class LLMConfigRequest(BaseModel):
    provider: str
    model_name: str
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None


class LLMConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    api_base_url: str
    is_active: bool
    has_api_key: bool

    model_config = {"from_attributes": True}
