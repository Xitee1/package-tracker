from sqlalchemy import Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScanHistorySettings(Base):
    __tablename__ = "scan_history_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=7)
    max_per_user: Mapped[int] = mapped_column(Integer, default=1000)
    cleanup_interval_hours: Mapped[float] = mapped_column(Float, default=1.0)
