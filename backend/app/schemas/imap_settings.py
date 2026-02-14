from pydantic import BaseModel


class ImapSettingsRequest(BaseModel):
    max_email_age_days: int = 7
    check_uidvalidity: bool = True


class ImapSettingsResponse(BaseModel):
    id: int
    max_email_age_days: int
    check_uidvalidity: bool

    model_config = {"from_attributes": True}
