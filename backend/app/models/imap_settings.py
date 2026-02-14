from sqlalchemy import Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImapSettings(Base):
    __tablename__ = "imap_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_email_age_days: Mapped[int] = mapped_column(Integer, default=7)
    check_uidvalidity: Mapped[bool] = mapped_column(Boolean, default=True)
