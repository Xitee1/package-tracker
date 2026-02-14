import logging
from datetime import datetime, timezone

from apscheduler import AsyncScheduler, ConflictPolicy
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger

from app.database import async_session, engine

logger = logging.getLogger(__name__)

_job_metadata: dict[str, dict] = {}


async def _run_queue_worker() -> None:
    """Wrapper that calls process_next_item."""
    from app.services.queue.queue_worker import process_next_item

    _job_metadata["queue_worker"]["last_run"] = datetime.now(timezone.utc).isoformat()
    try:
        await process_next_item()
        _job_metadata["queue_worker"]["last_status"] = "success"
    except Exception as e:
        logger.error(f"Queue worker job failed: {e}")
        _job_metadata["queue_worker"]["last_status"] = f"error: {e}"


async def _run_retention_cleanup() -> None:
    """Wrapper that calls cleanup_queue."""
    from app.services.queue.queue_retention import cleanup_queue

    _job_metadata["retention_cleanup"]["last_run"] = datetime.now(timezone.utc).isoformat()
    try:
        async with async_session() as db:
            await cleanup_queue(db)
        _job_metadata["retention_cleanup"]["last_status"] = "success"
    except Exception as e:
        logger.error(f"Retention cleanup job failed: {e}")
        _job_metadata["retention_cleanup"]["last_status"] = f"error: {e}"


async def create_scheduler() -> AsyncScheduler:
    """Create and configure the AsyncScheduler."""
    data_store = SQLAlchemyDataStore(engine)
    scheduler = AsyncScheduler(data_store)

    _job_metadata["queue_worker"] = {
        "description": "Process next queued item",
        "interval_seconds": 5,
        "last_run": None,
        "last_status": None,
    }
    _job_metadata["retention_cleanup"] = {
        "description": "Clean up old queue items",
        "interval_seconds": 600,
        "last_run": None,
        "last_status": None,
    }

    logger.info("Scheduler created: queue worker every 5s, retention cleanup every 10min")
    return scheduler


async def register_schedules(scheduler: AsyncScheduler) -> None:
    """Register all scheduled jobs."""
    await scheduler.add_schedule(
        _run_queue_worker,
        IntervalTrigger(seconds=5),
        id="queue-worker",
        conflict_policy=ConflictPolicy.replace,
    )
    await scheduler.add_schedule(
        _run_retention_cleanup,
        IntervalTrigger(seconds=600),
        id="retention-cleanup",
        conflict_policy=ConflictPolicy.replace,
    )
    logger.info("Registered queue-worker and retention-cleanup schedules")


def get_job_metadata() -> dict[str, dict]:
    """Return metadata about scheduled jobs for the system status API."""
    return _job_metadata.copy()
