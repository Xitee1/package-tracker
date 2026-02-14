from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueueSettings(Base):
    __tablename__ = "queue_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=7)
    max_per_user: Mapped[int] = mapped_column(Integer, default=5000)
