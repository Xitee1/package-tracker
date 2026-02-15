import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import JSON

from app.database import Base


class UserNotificationConfig(Base):
    __tablename__ = "user_notification_config"
    __table_args__ = (
        UniqueConstraint("user_id", "module_key", name="uq_user_notification_config"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    module_key: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    events: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)


class EmailVerification(Base):
    __tablename__ = "email_verification"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    token: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column()
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
