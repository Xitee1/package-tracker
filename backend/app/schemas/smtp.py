from typing import Optional

from pydantic import BaseModel, EmailStr


class SmtpConfigRequest(BaseModel):
    host: str
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    sender_address: EmailStr
    sender_name: str = "Package Tracker"


class SmtpConfigResponse(BaseModel):
    id: int
    host: str
    port: int
    username: Optional[str] = None
    use_tls: bool
    sender_address: str
    sender_name: str

    model_config = {"from_attributes": True}


class SmtpTestRequest(BaseModel):
    recipient: EmailStr
