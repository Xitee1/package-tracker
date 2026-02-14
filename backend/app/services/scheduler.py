import logging
from datetime import datetime, timezone

from apscheduler import AsyncScheduler, ConflictPolicy
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import async_session, engine
from app.models.scan_history_settings import ScanHistorySettings

logger = logging.getLogger(__name__)

_job_metadata: dict[str, dict] = {}


async def _run_history_cleanup() -> None:
    """Wrapper that creates its own DB session and calls cleanup_scan_history."""
    from app.services.history_cleanup import cleanup_scan_history

    _job_metadata["history_cleanup"]["last_run"] = datetime.now(timezone.utc).isoformat()
    try:
        async with async_session() as db:
            await cleanup_scan_history(db)
        _job_metadata["history_cleanup"]["last_status"] = "success"
    except Exception as e:
        logger.error(f"History cleanup job failed: {e}")
        _job_metadata["history_cleanup"]["last_status"] = f"error: {e}"


async def create_scheduler() -> AsyncScheduler:
    """Create and configure the AsyncScheduler with cleanup job.

    The returned scheduler must be used as an async context manager
    (``async with scheduler:``) before calling ``start_in_background()``.
    The cleanup schedule is registered eagerly so that
    ``add_schedule`` runs inside the caller's ``async with`` block.
    """
    data_store = SQLAlchemyDataStore(engine)

    # Read cleanup interval from settings (default 1 hour)
    interval_hours = 1.0
    try:
        async with async_session() as db:
            result = await db.execute(select(ScanHistorySettings))
            settings = result.scalar_one_or_none()
            if settings:
                interval_hours = settings.cleanup_interval_hours
    except Exception:
        pass  # Use default if settings can't be read

    scheduler = AsyncScheduler(data_store)

    _job_metadata["history_cleanup"] = {
        "description": "Clean up old email scan history",
        "interval_hours": interval_hours,
        "last_run": None,
        "last_status": None,
    }

    logger.info(f"Scheduler created: history cleanup every {interval_hours}h")
    return scheduler


async def register_schedules(scheduler: AsyncScheduler) -> None:
    """Register all scheduled jobs. Must be called inside the scheduler context."""
    interval_hours = _job_metadata.get("history_cleanup", {}).get("interval_hours", 1.0)

    await scheduler.add_schedule(
        _run_history_cleanup,
        IntervalTrigger(hours=interval_hours),
        id="history-cleanup",
        conflict_policy=ConflictPolicy.replace,
    )
    logger.info("Registered history-cleanup schedule")


def get_job_metadata() -> dict[str, dict]:
    """Return metadata about scheduled jobs for the system status API."""
    return _job_metadata.copy()
