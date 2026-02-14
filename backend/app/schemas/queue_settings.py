from pydantic import BaseModel


class QueueSettingsResponse(BaseModel):
    max_age_days: int
    max_per_user: int

    model_config = {"from_attributes": True}


class UpdateQueueSettingsRequest(BaseModel):
    max_age_days: int | None = None
    max_per_user: int | None = None
