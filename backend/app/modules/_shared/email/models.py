from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(20), default="user_account")
    folder_path: Mapped[str] = mapped_column(String(512))
    email_uid: Mapped[int] = mapped_column(Integer)
    message_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    queue_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("queue_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account = relationship("EmailAccount")
    queue_item = relationship("QueueItem")
