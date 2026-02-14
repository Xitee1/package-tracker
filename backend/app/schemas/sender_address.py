from datetime import datetime

from pydantic import BaseModel, EmailStr


class CreateSenderAddressRequest(BaseModel):
    email_address: EmailStr


class SenderAddressResponse(BaseModel):
    id: int
    email_address: str
    created_at: datetime

    model_config = {"from_attributes": True}
