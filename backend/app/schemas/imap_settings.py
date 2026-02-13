from pydantic import BaseModel


class ImapSettingsRequest(BaseModel):
    max_email_age_days: int = 7
    processing_delay_sec: float = 2.0
    check_uidvalidity: bool = True


class ImapSettingsResponse(BaseModel):
    id: int
    max_email_age_days: int
    processing_delay_sec: float
    check_uidvalidity: bool

    model_config = {"from_attributes": True}
