from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.user import User
from app.models.worker_stats import WorkerStats
from app.services.imap_worker import _running_tasks, _worker_state

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

    return {
        "global": {
            "total_folders": total_folders,
            "running": running_count,
            "errors": error_count,
            "queue_total": queue_total_global,
            "processing_folders": processing_folders,
        },
        "users": users_out,
    }


@router.get("/stats")
async def system_stats(
    period: str = "hourly",
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    cutoff_4w = now - timedelta(weeks=4)

    # Cleanup rows older than 4 weeks
    await db.execute(delete(WorkerStats).where(WorkerStats.hour_bucket < cutoff_4w))
    await db.commit()

    if period == "hourly":
        since = now - timedelta(hours=24)
        group_expr = WorkerStats.hour_bucket
    elif period == "daily":
        since = now - timedelta(days=7)
        group_expr = func.date_trunc("day", WorkerStats.hour_bucket)
    elif period == "weekly":
        since = now - timedelta(weeks=4)
        group_expr = func.date_trunc("week", WorkerStats.hour_bucket)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}. Must be hourly, daily, or weekly.")

    stmt = (
        select(
            group_expr.label("bucket"),
            func.sum(WorkerStats.emails_processed).label("emails_processed"),
            func.sum(WorkerStats.errors_count).label("errors_count"),
        )
        .where(WorkerStats.hour_bucket >= since)
        .group_by("bucket")
        .order_by("bucket")
    )
    result = await db.execute(stmt)
    rows = result.all()

    buckets = [
        {
            "timestamp": row.bucket.isoformat() if isinstance(row.bucket, datetime) else str(row.bucket),
            "emails_processed": int(row.emails_processed or 0),
            "errors_count": int(row.errors_count or 0),
        }
        for row in rows
    ]

    return {"period": period, "buckets": buckets}
