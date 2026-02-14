from pydantic import BaseModel
from typing import Optional


class CreateAccountRequest(BaseModel):
    name: str
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: str
    use_ssl: bool = True
    polling_interval_sec: int = 300
    use_polling: bool = False


class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    use_ssl: Optional[bool] = None
    polling_interval_sec: Optional[int] = None
    is_active: Optional[bool] = None
    use_polling: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    imap_host: str
    imap_port: int
    imap_user: str
    use_ssl: bool
    polling_interval_sec: int
    is_active: bool
    use_polling: bool
    idle_supported: Optional[bool] = None

    model_config = {"from_attributes": True}


class WatchFolderRequest(BaseModel):
    folder_path: str


class UpdateWatchedFolderRequest(BaseModel):
    max_email_age_days: Optional[int] = None
    processing_delay_sec: Optional[float] = None


class WatchedFolderResponse(BaseModel):
    id: int
    folder_path: str
    last_seen_uid: int
    max_email_age_days: Optional[int] = None
    processing_delay_sec: Optional[float] = None

    model_config = {"from_attributes": True}
