from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkerStats(Base):
    __tablename__ = "worker_stats"
    __table_args__ = (
        UniqueConstraint("folder_id", "hour_bucket", name="uq_worker_stats_folder_hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id: Mapped[int] = mapped_column(Integer, ForeignKey("watched_folders.id", ondelete="CASCADE"))
    hour_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    emails_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
