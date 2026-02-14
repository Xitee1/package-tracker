from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_user: Mapped[str] = mapped_column(String(255))
    imap_password_encrypted: Mapped[str] = mapped_column(String(1024))
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    use_polling: Mapped[bool] = mapped_column(Boolean, default=False)
    idle_supported: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="email_accounts")
    watched_folders = relationship("WatchedFolder", back_populates="account", cascade="all, delete-orphan")


class WatchedFolder(Base):
    __tablename__ = "watched_folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id", ondelete="CASCADE"))
    folder_path: Mapped[str] = mapped_column(String(512))
    last_seen_uid: Mapped[int] = mapped_column(Integer, default=0)
    max_email_age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    processing_delay_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    uidvalidity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)

    account = relationship("EmailAccount", back_populates="watched_folders")
