from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


IDLE_TIMEOUT_SEC = 24 * 60  # 24 minutes, safely under RFC 2177's 29-minute limit
MAX_BACKOFF_SEC = 300  # 5 minutes max backoff


class WorkerMode(StrEnum):
    CONNECTING = "connecting"
    IDLE = "idle"
    POLLING = "polling"
    PROCESSING = "processing"
    ERROR_BACKOFF = "error_backoff"


@dataclass
class WorkerState:
    folder_id: int
    account_id: int
    mode: str = WorkerMode.CONNECTING
    last_scan_at: datetime | None = None
    next_scan_at: datetime | None = None
    last_activity_at: datetime | None = None
    queue_total: int = 0
    queue_position: int = 0
    current_email_subject: str | None = None
    current_email_sender: str | None = None
    error: str | None = None

    def clear_queue(self):
        self.queue_total = 0
        self.queue_position = 0
        self.current_email_subject = None
        self.current_email_sender = None
