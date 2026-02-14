from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GlobalMailConfig(Base):
    __tablename__ = "global_mail_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_user: Mapped[str] = mapped_column(String(255))
    imap_password_encrypted: Mapped[str] = mapped_column(String(1024))
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    use_polling: Mapped[bool] = mapped_column(Boolean, default=False)
    idle_supported: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)
    watched_folder_path: Mapped[str] = mapped_column(String(512), default="INBOX")
    last_seen_uid: Mapped[int] = mapped_column(Integer, default=0)
    uidvalidity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)


class UserSenderAddress(Base):
    __tablename__ = "user_sender_address"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    email_address: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="sender_addresses")
