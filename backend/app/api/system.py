from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.email_account import EmailAccount
from app.models.user import User
from app.models.queue_item import QueueItem
from app.services.imap_worker import _running_tasks, _worker_state
from app.services.scheduler import get_job_metadata

router = APIRouter(prefix="/api/v1/system", tags=["system"], dependencies=[Depends(get_admin_user)])


@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User)
        .options(selectinload(User.email_accounts).selectinload(EmailAccount.watched_folders))
    )
    all_users = result.scalars().all()

    total_folders = 0
    running_count = 0
    error_count = 0
    queue_total_global = 0
    processing_folders = 0

    users_out = []
    for user in all_users:
        if not user.email_accounts:
            continue

        accounts_out = []
        for account in user.email_accounts:
            folders_out = []
            for folder in account.watched_folders:
                fid = folder.id
                task = _running_tasks.get(fid)
                state = _worker_state.get(fid)

                is_running = task is not None and not task.done()
                task_error = None
                if task is not None and task.done():
                    try:
                        exc = task.exception()
                        if exc:
                            task_error = str(exc)
                    except Exception:
                        pass

                # Determine mode
                if state:
                    mode = state.mode
                elif not is_running:
                    mode = "stopped"
                else:
                    mode = "unknown"

                # Extract state fields
                last_scan_at = state.last_scan_at.isoformat() if state and state.last_scan_at else None
                next_scan_at = state.next_scan_at.isoformat() if state and state.next_scan_at else None
                last_activity_at = state.last_activity_at.isoformat() if state and state.last_activity_at else None
                q_total = state.queue_total if state else 0
                q_position = state.queue_position if state else 0
                current_subject = state.current_email_subject if state else None
                current_sender = state.current_email_sender if state else None
                error = state.error if state else task_error

                # Remaining emails in queue for this folder
                remaining = max(0, q_total - q_position)

                # Update global counters
                total_folders += 1
                if is_running:
                    running_count += 1
                if error:
                    error_count += 1
                queue_total_global += remaining
                if mode == "processing":
                    processing_folders += 1

                folders_out.append({
                    "folder_id": fid,
                    "folder_path": folder.folder_path,
                    "running": is_running,
                    "mode": mode,
                    "last_scan_at": last_scan_at,
                    "next_scan_at": next_scan_at,
                    "last_activity_at": last_activity_at,
                    "queue_total": q_total,
                    "queue_position": q_position,
                    "current_email_subject": current_subject,
                    "current_email_sender": current_sender,
                    "error": error,
                })

            accounts_out.append({
                "account_id": account.id,
                "account_name": account.name,
                "is_active": account.is_active,
                "folders": folders_out,
            })

        users_out.append({
            "user_id": user.id,
            "username": user.username,
            "accounts": accounts_out,
        })

    # Build scheduled jobs list from scheduler metadata
    scheduled_jobs = []
    for job_id, meta in get_job_metadata().items():
        interval_seconds = meta.get("interval_seconds")
        last_run_at = meta.get("last_run")

        # Compute next_run_at from last_run + interval
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

    # Add queue stats
    queue_stats = {}
    for s in ("queued", "processing", "completed", "failed"):
        result = await db.execute(
            select(func.count()).select_from(QueueItem).where(QueueItem.status == s)
        )
        queue_stats[s] = result.scalar() or 0

    return {
        "global": {
            "total_folders": total_folders,
            "running": running_count,
            "errors": error_count,
            "queue_total": queue_total_global,
            "processing_folders": processing_folders,
        },
        "queue": queue_stats,
        "users": users_out,
        "scheduled_jobs": scheduled_jobs,
    }
