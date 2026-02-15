from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


class SmtpSecurity(str, Enum):
    TLS = "tls"
    STARTTLS = "starttls"
    NONE = "none"


class SmtpConfigRequest(BaseModel):
    host: str
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    security: Literal["tls", "starttls", "none"] = "starttls"
    sender_address: EmailStr
    sender_name: str = "Package Tracker"


class SmtpConfigResponse(BaseModel):
    id: int
    host: str
    port: int
    username: Optional[str] = None
    security: str
    sender_address: str
    sender_name: str

    model_config = {"from_attributes": True}


class SmtpTestRequest(BaseModel):
    recipient: EmailStr
