from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailScan(Base):
    __tablename__ = "email_scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE")
    )
    folder_path: Mapped[str] = mapped_column(String(512))
    email_uid: Mapped[int] = mapped_column(Integer)
    message_id: Mapped[str] = mapped_column(String(512), index=True)
    subject: Mapped[str] = mapped_column(String(1024), default="")
    sender: Mapped[str] = mapped_column(String(512), default="")
    email_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    rescan_queued: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account = relationship("EmailAccount")
    order = relationship("Order")
