from pydantic import BaseModel, Field


class QueueSettingsResponse(BaseModel):
    max_age_days: int = Field(ge=1)
    max_per_user: int = Field(ge=1)

    model_config = {"from_attributes": True}


class UpdateQueueSettingsRequest(BaseModel):
    max_age_days: int = Field(ge=1)
    max_per_user: int = Field(ge=1)
