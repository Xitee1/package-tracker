import asyncio
import logging
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.imap_settings import ImapSettings
from app.modules._shared.email.imap_watcher import WorkerMode, WorkerState
from app.modules._shared.email.imap_watch_loop import (
    ConnectResult,
    FetchContext,
    ImapWatcherCallbacks,
    watch_loop,
)
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder

logger = logging.getLogger(__name__)

_running_tasks: dict[int, asyncio.Task] = {}
_worker_state: dict[int, WorkerState] = {}


def get_worker_states() -> dict[int, WorkerState]:
    return dict(_worker_state)


def is_folder_scanning(folder_id: int) -> bool:
    """Check if a folder is currently mid-scan (processing emails)."""
    state = _worker_state.get(folder_id)
    return state is not None and state.mode == WorkerMode.PROCESSING


async def _get_effective_settings(db, folder: WatchedFolder) -> tuple[int, bool]:
    """Return (max_email_age_days, check_uidvalidity) for a folder."""
    result = await db.execute(select(ImapSettings))
    global_settings = result.scalar_one_or_none()

    max_age = folder.max_email_age_days
    if max_age is None:
        max_age = global_settings.max_email_age_days if global_settings else 7

    check_uid = global_settings.check_uidvalidity if global_settings else True

    return max_age, check_uid


def _build_callbacks(account_id: int, folder_id: int) -> ImapWatcherCallbacks:
    """Build provider-specific callbacks for a user email account folder."""

    async def connect(db: AsyncSession) -> ConnectResult | None:
        from aioimaplib import IMAP4_SSL
        from app.core.encryption import decrypt_value

        account = await db.get(EmailAccount, account_id)
        folder = await db.get(WatchedFolder, folder_id)
        if not account or not folder or not account.is_active:
            return None

        password = decrypt_value(account.imap_password_encrypted)
        imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
        await imap.wait_hello_from_server()
        await imap.login(account.imap_user, password)

        idle_supported = imap.has_capability("IDLE")
        if account.idle_supported != idle_supported:
            account.idle_supported = idle_supported
            if not idle_supported and not account.use_polling:
                account.use_polling = True
                logger.info(
                    f"Account {account.id}: IDLE not supported, forcing polling mode"
                )
            await db.commit()
            await db.refresh(account)

        select_response = await imap.select(folder.folder_path)

        _, check_uid = await _get_effective_settings(db, folder)
        if check_uid:
            current_uidvalidity = None
            if select_response and len(select_response) > 1:
                for line in select_response[1]:
                    line_str = line.decode() if isinstance(line, bytes) else str(line)
                    match = re.search(r"UIDVALIDITY\s+(\d+)", line_str)
                    if match:
                        current_uidvalidity = int(match.group(1))
                        break

            if current_uidvalidity is not None:
                if folder.uidvalidity is None:
                    folder.uidvalidity = current_uidvalidity
                    await db.commit()
                elif folder.uidvalidity != current_uidvalidity:
                    logger.warning(
                        f"UIDVALIDITY changed for folder {folder.id}: "
                        f"{folder.uidvalidity} -> {current_uidvalidity}. Resetting."
                    )
                    folder.uidvalidity = current_uidvalidity
                    folder.last_seen_uid = 0
                    await db.commit()

        return ConnectResult(
            imap=imap,
            idle_supported=idle_supported,
            use_polling=account.use_polling,
            polling_interval_sec=account.polling_interval_sec,
        )

    async def load_fetch_context(db: AsyncSession) -> FetchContext | None:
        account = await db.get(EmailAccount, account_id)
        folder = await db.get(WatchedFolder, folder_id)
        if not account or not folder:
            return None

        max_age, _ = await _get_effective_settings(db, folder)

        return FetchContext(
            last_seen_uid=folder.last_seen_uid,
            folder_path=folder.folder_path,
            uidvalidity=folder.uidvalidity,
            max_email_age_days=max_age,
            source_info=f"{account.imap_user} / {folder.folder_path}",
            source_label=f"folder {folder_id}",
            account_id=account.id,
        )

    async def route_email(sender: str, db: AsyncSession):
        account = await db.get(EmailAccount, account_id)
        if not account:
            return None
        return (account.user_id, "user_account")

    async def save_uid(uid: int, db: AsyncSession) -> None:
        folder = await db.get(WatchedFolder, folder_id)
        if folder:
            folder.last_seen_uid = uid
            await db.commit()

    return ImapWatcherCallbacks(
        connect=connect,
        load_fetch_context=load_fetch_context,
        route_email=route_email,
        save_uid=save_uid,
        log_label=f"folder {folder_id}",
    )


async def start_all_watchers():
    """Start watchers for all active accounts and their watched folders."""
    async with async_session() as db:
        result = await db.execute(
            select(WatchedFolder)
            .join(EmailAccount)
            .where(EmailAccount.is_active == True)
        )
        folders = result.scalars().all()
        for folder in folders:
            key = folder.id
            if key not in _running_tasks:
                _worker_state[key] = WorkerState(folder_id=folder.id, account_id=folder.account_id)
                callbacks = _build_callbacks(folder.account_id, folder.id)
                task = asyncio.create_task(watch_loop(callbacks, _worker_state[key]))
                _running_tasks[key] = task
                logger.info(f"Started watcher for folder {folder.id} (account {folder.account_id})")


async def stop_all_watchers():
    """Stop all running user watchers."""
    for key, task in _running_tasks.items():
        task.cancel()
    _running_tasks.clear()
    _worker_state.clear()


async def restart_watchers():
    """Restart all watchers (call after account/folder changes)."""
    await stop_all_watchers()
    await start_all_watchers()


async def restart_single_watcher(folder_id: int):
    """Restart watcher for a single folder to trigger immediate scan."""
    if folder_id in _running_tasks:
        task = _running_tasks.pop(folder_id)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        _worker_state.pop(folder_id, None)

    async with async_session() as db:
        folder = await db.get(WatchedFolder, folder_id)
        if not folder:
            return
        account = await db.get(EmailAccount, folder.account_id)
        if not account or not account.is_active:
            return
        _worker_state[folder_id] = WorkerState(folder_id=folder_id, account_id=folder.account_id)
        callbacks = _build_callbacks(folder.account_id, folder_id)
        task = asyncio.create_task(watch_loop(callbacks, _worker_state[folder_id]))
        _running_tasks[folder_id] = task
        logger.info(f"Restarted watcher for folder {folder_id} (manual scan)")


async def get_status(db: AsyncSession) -> dict:
    """Status hook: return per-user/account/folder worker state."""
    from app.models.user import User

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.email_accounts)
            .selectinload(EmailAccount.watched_folders)
        )
    )
    all_users = result.scalars().all()

    total_folders = 0
    running_count = 0
    error_count = 0

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

                if state:
                    mode = state.mode
                elif not is_running:
                    mode = "stopped"
                else:
                    mode = "unknown"

                last_scan_at = state.last_scan_at.isoformat() if state and state.last_scan_at else None
                next_scan_at = state.next_scan_at.isoformat() if state and state.next_scan_at else None
                last_activity_at = state.last_activity_at.isoformat() if state and state.last_activity_at else None
                q_total = state.queue_total if state else 0
                q_position = state.queue_position if state else 0
                current_subject = state.current_email_subject if state else None
                current_sender = state.current_email_sender if state else None
                error = state.error if state else task_error

                total_folders += 1
                if is_running:
                    running_count += 1
                if error:
                    error_count += 1

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
        "total_folders": total_folders,
        "running": running_count,
        "errors": error_count,
        "users": users_out,
    }
