import asyncio
import email
import logging
import re
from datetime import datetime, timedelta, timezone

from aioimaplib import IMAP4_SSL, STOP_WAIT_SERVER_PUSH
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models.imap_settings import ImapSettings
from app.modules._shared.email.imap_client import decode_header_value, extract_body
from app.modules._shared.email.imap_watcher import WorkerMode, WorkerState, IDLE_TIMEOUT_SEC, MAX_BACKOFF_SEC
from app.modules._shared.email.email_fetcher import check_dedup_and_enqueue
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


async def _connect_and_select(
    account, folder, db,
) -> tuple[IMAP4_SSL, bool]:
    """Connect, login, check IDLE capability, select folder."""
    from app.core.encryption import decrypt_value

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

    return imap, idle_supported


async def _fetch_new_emails(
    imap: IMAP4_SSL, account, folder, db, state: WorkerState | None,
) -> None:
    """UID search for new emails, process and enqueue them."""
    max_age, _ = await _get_effective_settings(db, folder)
    since_date = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%d-%b-%Y")
    search_criteria = f"UID {folder.last_seen_uid + 1}:* SINCE {since_date}"
    _, data = await imap.uid_search(search_criteria)
    uids = data[0].split() if data[0] else []

    if state:
        if uids:
            state.mode = WorkerMode.PROCESSING
            state.queue_total = len(uids)
        state.last_activity_at = datetime.now(timezone.utc)

    for i, uid_bytes in enumerate(uids):
        uid = int(uid_bytes)
        if uid <= folder.last_seen_uid:
            continue

        _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue

        raw_email = None
        for part in msg_data:
            if isinstance(part, bytearray):
                raw_email = bytes(part)
                break
        if raw_email is None:
            continue
        msg = email.message_from_bytes(raw_email)

        subject = decode_header_value(msg.get("Subject", ""))
        sender = decode_header_value(msg.get("From", ""))
        message_id = msg.get("Message-ID", "")
        body = extract_body(msg)

        email_date = None
        try:
            date_str = msg.get("Date", "")
            if date_str:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
        except Exception:
            pass

        if state:
            state.queue_position = i + 1
            state.current_email_subject = subject
            state.current_email_sender = sender
            state.last_activity_at = datetime.now(timezone.utc)

        enqueued = await check_dedup_and_enqueue(
            message_id=message_id,
            subject=subject,
            sender=sender,
            body=body,
            email_date=email_date,
            email_uid=uid,
            user_id=account.user_id,
            source_info=f"{account.imap_user} / {folder.folder_path}",
            account_id=account.id,
            folder_path=folder.folder_path,
            source="user_account",
            db=db,
        )

        folder.last_seen_uid = uid
        await db.commit()

    if state:
        state.last_scan_at = datetime.now(timezone.utc)
        state.clear_queue()


async def _idle_loop(
    imap: IMAP4_SSL, account, folder, db, state: WorkerState | None,
) -> None:
    """Persistent IDLE loop. Returns only on connection error (to trigger reconnect)."""
    while True:
        if state:
            state.mode = WorkerMode.IDLE
            state.next_scan_at = None
            state.last_activity_at = datetime.now(timezone.utc)

        try:
            idle_task = await imap.idle_start(timeout=IDLE_TIMEOUT_SEC)

            msg = await imap.wait_server_push()

            if msg == STOP_WAIT_SERVER_PUSH:
                imap.idle_done()
                await asyncio.wait_for(idle_task, timeout=5)
                continue

            imap.idle_done()
            await asyncio.wait_for(idle_task, timeout=5)

            has_new = False
            if isinstance(msg, list):
                for line in msg:
                    line_str = line.decode() if isinstance(line, bytes) else str(line)
                    if "EXISTS" in line_str:
                        has_new = True
                        break

            if has_new:
                await _fetch_new_emails(imap, account, folder, db, state)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"IDLE loop error for folder {folder.id}: {e}")
            try:
                imap.idle_done()
            except Exception:
                pass
            return


async def _poll_loop(
    account_id: int, folder_id: int, polling_interval_sec: int,
    state: WorkerState | None,
) -> None:
    """Polling loop. Disconnects between cycles."""
    interval = polling_interval_sec
    while True:
        if state:
            state.mode = WorkerMode.POLLING
            state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=interval)

        await asyncio.sleep(interval)

        try:
            async with async_session() as db:
                account = await db.get(EmailAccount, account_id)
                folder = await db.get(WatchedFolder, folder_id)
                if not account or not folder or not account.is_active:
                    return

                imap, _ = await _connect_and_select(account, folder, db)
                await _fetch_new_emails(imap, account, folder, db, state)
                try:
                    await imap.logout()
                except Exception:
                    pass

                interval = account.polling_interval_sec

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Poll cycle error for folder {folder_id}: {e}")
            return


async def _watch_folder(account_id: int, folder_id: int):
    """Watch a single IMAP folder using IDLE (persistent) or polling (periodic)."""
    backoff = 30

    while True:
        state = _worker_state.get(folder_id)
        if state:
            state.mode = WorkerMode.CONNECTING
            state.next_scan_at = None
            state.clear_queue()
            state.error = None

        try:
            async with async_session() as db:
                account = await db.get(EmailAccount, account_id)
                folder = await db.get(WatchedFolder, folder_id)
                if not account or not folder or not account.is_active:
                    logger.info(f"Stopping watcher for folder {folder_id}: inactive or removed")
                    return

                imap, idle_supported = await _connect_and_select(account, folder, db)

                await _fetch_new_emails(imap, account, folder, db, state)

                backoff = 30

                if not account.use_polling and idle_supported:
                    await _idle_loop(imap, account, folder, db, state)
                else:
                    try:
                        await imap.logout()
                    except Exception:
                        pass
                    await _poll_loop(account_id, folder_id, account.polling_interval_sec, state)

        except asyncio.CancelledError:
            logger.info(f"Watcher cancelled for folder {folder_id}")
            return
        except Exception as e:
            logger.error(f"Error watching folder {folder_id}: {e}")
            if state:
                state.mode = WorkerMode.ERROR_BACKOFF
                state.error = str(e)
                state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_SEC)


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
                task = asyncio.create_task(_watch_folder(folder.account_id, folder.id))
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
        task = asyncio.create_task(_watch_folder(folder.account_id, folder_id))
        _running_tasks[folder_id] = task
        logger.info(f"Restarted watcher for folder {folder_id} (manual scan)")


async def get_status(db) -> dict:
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
