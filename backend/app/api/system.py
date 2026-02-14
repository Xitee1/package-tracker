from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.module_registry import get_all_modules
from app.database import get_db
from app.models.module_config import ModuleConfig
from app.models.queue_item import QueueItem
from app.services.scheduler import get_job_metadata

router = APIRouter(prefix="/api/v1/system", tags=["system"], dependencies=[Depends(get_admin_user)])


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    # --- Queue stats ---
    queue_stats = {}
    for s in ("queued", "processing", "completed", "failed"):
        result = await db.execute(
            select(func.count()).select_from(QueueItem).where(QueueItem.status == s)
        )
        queue_stats[s] = result.scalar() or 0

    # --- Scheduled jobs ---
    scheduled_jobs = []
    for job_id, meta in get_job_metadata().items():
        interval_seconds = meta.get("interval_seconds")
        last_run_at = meta.get("last_run")

        next_run_at = None
        if last_run_at is not None and interval_seconds is not None:
            if isinstance(last_run_at, str):
                last_run_dt = datetime.fromisoformat(last_run_at)
            else:
                last_run_dt = last_run_at
            next_run_at = (last_run_dt + timedelta(seconds=interval_seconds)).isoformat()

        scheduled_jobs.append({
            "id": job_id,
            "description": meta.get("description"),
            "interval_seconds": interval_seconds,
            "last_run_at": last_run_at,
            "last_status": meta.get("last_status"),
            "next_run_at": next_run_at,
        })

    # --- Module statuses ---
    all_modules = get_all_modules()
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.priority, ModuleConfig.module_key))
    configs = {c.module_key: c for c in result.scalars().all()}

    modules_out = []
    for key, info in all_modules.items():
        config = configs.get(key)
        enabled = config.enabled if config else False

        configured = True
        if info.is_configured:
            try:
                configured = await info.is_configured()
            except Exception:
                configured = False

        module_status = None
        if enabled and info.status:
            try:
                module_status = await info.status(db)
            except Exception:
                module_status = None

        modules_out.append({
            "key": info.key,
            "name": info.name,
            "type": info.type,
            "version": info.version,
            "description": info.description,
            "enabled": enabled,
            "configured": configured,
            "status": module_status,
        })

    return {
        "system": {
            "queue": queue_stats,
            "scheduled_jobs": scheduled_jobs,
        },
        "modules": modules_out,
    }
