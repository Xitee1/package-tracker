import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_item import QueueItem
from app.models.queue_settings import QueueSettings

logger = logging.getLogger(__name__)


async def cleanup_queue(db: AsyncSession) -> None:
    """Delete old QueueItems based on QueueSettings."""
    result = await db.execute(select(QueueSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return

    total_removed = 0

    # 1. Delete entries older than max_age_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.max_age_days)
    age_stmt = delete(QueueItem).where(QueueItem.created_at < cutoff)
    age_result = await db.execute(age_stmt)
    total_removed += age_result.rowcount

    # 2. Per-user cap: delete oldest excess entries beyond max_per_user
    user_counts_stmt = (
        select(QueueItem.user_id, func.count(QueueItem.id).label("cnt"))
        .group_by(QueueItem.user_id)
        .having(func.count(QueueItem.id) > settings.max_per_user)
    )
    user_counts = await db.execute(user_counts_stmt)

    for user_id, count in user_counts:
        excess = count - settings.max_per_user
        oldest_ids_stmt = (
            select(QueueItem.id)
            .where(QueueItem.user_id == user_id)
            .order_by(QueueItem.created_at.asc())
            .limit(excess)
        )
        oldest_ids_result = await db.execute(oldest_ids_stmt)
        ids_to_delete = [row[0] for row in oldest_ids_result]

        if ids_to_delete:
            del_stmt = delete(QueueItem).where(QueueItem.id.in_(ids_to_delete))
            del_result = await db.execute(del_stmt)
            total_removed += del_result.rowcount

    await db.commit()

    if total_removed > 0:
        logger.info(f"Queue cleanup: removed {total_removed} items")
