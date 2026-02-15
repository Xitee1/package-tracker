from pydantic import BaseModel, Field, model_validator
from typing import Optional

# Providers that support each field
PROVIDERS_WITH_API_KEY = {"openai", "anthropic", "custom"}
PROVIDERS_WITH_BASE_URL = {"openai", "ollama", "custom"}


class LLMConfigPutRequest(BaseModel):
    """Schema for PUT /config - all fields must be explicitly provided (can be null)."""
    provider: str
    model_name: str
    # Fields must be explicitly provided (no defaults) but can be null
    api_key: Optional[str] = Field(...)
    api_base_url: Optional[str] = Field(...)
    system_prompt: Optional[str] = Field(...)

    @model_validator(mode="after")
    def validate_provider_fields(self):
        known = self.provider in (PROVIDERS_WITH_API_KEY | PROVIDERS_WITH_BASE_URL)
        if known:
            if self.api_key and self.provider not in PROVIDERS_WITH_API_KEY:
                raise ValueError(f"Provider '{self.provider}' does not use an API key")
            if self.api_base_url and self.provider not in PROVIDERS_WITH_BASE_URL:
                raise ValueError(f"Provider '{self.provider}' does not use a base URL")
        return self


class LLMConfigRequest(BaseModel):
    """Deprecated: Use LLMConfigPutRequest for PUT operations."""
    provider: str
    model_name: str
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    system_prompt: Optional[str] = None

    @model_validator(mode="after")
    def validate_provider_fields(self):
        known = self.provider in (PROVIDERS_WITH_API_KEY | PROVIDERS_WITH_BASE_URL)
        if known:
            if self.api_key and self.provider not in PROVIDERS_WITH_API_KEY:
                raise ValueError(f"Provider '{self.provider}' does not use an API key")
            if self.api_base_url and self.provider not in PROVIDERS_WITH_BASE_URL:
                raise ValueError(f"Provider '{self.provider}' does not use a base URL")
        return self


class LLMConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    api_base_url: Optional[str]
    is_active: bool
    has_api_key: bool
    system_prompt: Optional[str] = None
    default_system_prompt: str = ""

    model_config = {"from_attributes": True}
