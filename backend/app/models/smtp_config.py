from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=587)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    security: Mapped[str] = mapped_column(String(10), default="starttls")
    sender_address: Mapped[str] = mapped_column(String(320))
    sender_name: Mapped[str] = mapped_column(String(255), default="Package Tracker")
