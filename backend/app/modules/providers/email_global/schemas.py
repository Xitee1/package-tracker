from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class GlobalMailConfigRequest(BaseModel):
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: Optional[str] = None
    use_ssl: bool = True
    polling_interval_sec: int = 300
    use_polling: bool = False
    watched_folder_path: str = "INBOX"


class GlobalMailConfigResponse(BaseModel):
    id: int
    imap_host: str
    imap_port: int
    imap_user: str
    use_ssl: bool
    polling_interval_sec: int
    use_polling: bool
    idle_supported: Optional[bool] = None
    watched_folder_path: str

    model_config = {"from_attributes": True}


class GlobalMailFoldersResponse(BaseModel):
    folders: list[str]
    idle_supported: bool


class GlobalMailInfoResponse(BaseModel):
    configured: bool
    email_address: Optional[str] = None


class CreateSenderAddressRequest(BaseModel):
    email_address: EmailStr


class SenderAddressResponse(BaseModel):
    id: int
    email_address: str
    created_at: datetime

    model_config = {"from_attributes": True}
