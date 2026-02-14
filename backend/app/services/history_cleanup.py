import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_scan import EmailScan
from app.models.scan_history_settings import ScanHistorySettings

logger = logging.getLogger(__name__)


async def cleanup_scan_history(db: AsyncSession) -> None:
    """Delete old EmailScan entries based on ScanHistorySettings."""
    result = await db.execute(select(ScanHistorySettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return

    total_removed = 0

    # 1. Delete entries older than max_age_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.max_age_days)
    age_stmt = delete(EmailScan).where(EmailScan.created_at < cutoff)
    age_result = await db.execute(age_stmt)
    total_removed += age_result.rowcount

    # 2. Per-user cap: delete oldest excess entries beyond max_per_user
    # Get user_ids via account relationship (EmailScan -> EmailAccount -> user_id)
    from app.models.email_account import EmailAccount

    user_counts_stmt = (
        select(EmailAccount.user_id, func.count(EmailScan.id).label("cnt"))
        .join(EmailScan, EmailScan.account_id == EmailAccount.id)
        .group_by(EmailAccount.user_id)
        .having(func.count(EmailScan.id) > settings.max_per_user)
    )
    user_counts = await db.execute(user_counts_stmt)

    for user_id, count in user_counts:
        excess = count - settings.max_per_user
        # Find the IDs of the oldest excess entries for this user
        oldest_ids_stmt = (
            select(EmailScan.id)
            .join(EmailAccount, EmailScan.account_id == EmailAccount.id)
            .where(EmailAccount.user_id == user_id)
            .order_by(EmailScan.created_at.asc())
            .limit(excess)
        )
        oldest_ids_result = await db.execute(oldest_ids_stmt)
        ids_to_delete = [row[0] for row in oldest_ids_result]

        if ids_to_delete:
            del_stmt = delete(EmailScan).where(EmailScan.id.in_(ids_to_delete))
            del_result = await db.execute(del_stmt)
            total_removed += del_result.rowcount

    await db.commit()

    if total_removed > 0:
        logger.info(f"Scan history cleanup: removed {total_removed} entries")
