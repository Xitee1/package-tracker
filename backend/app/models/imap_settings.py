from sqlalchemy import Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImapSettings(Base):
    __tablename__ = "imap_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_email_age_days: Mapped[int] = mapped_column(Integer, default=7)
    processing_delay_sec: Mapped[float] = mapped_column(Float, default=2.0)
    check_uidvalidity: Mapped[bool] = mapped_column(Boolean, default=True)
