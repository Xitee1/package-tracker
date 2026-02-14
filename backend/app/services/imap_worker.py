import asyncio
import email
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from enum import StrEnum

import html2text
from aioimaplib import IMAP4_SSL, STOP_WAIT_SERVER_PUSH
from sqlalchemy import select

from app.database import async_session
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.global_mail_config import GlobalMailConfig
from app.models.imap_settings import ImapSettings
from app.models.module_config import ModuleConfig
from app.models.processed_email import ProcessedEmail
from app.models.queue_item import QueueItem
from app.models.user_sender_address import UserSenderAddress

logger = logging.getLogger(__name__)
h2t = html2text.HTML2Text()
h2t.ignore_links = False

IDLE_TIMEOUT_SEC = 24 * 60  # 24 minutes, safely under RFC 2177's 29-minute limit
MAX_BACKOFF_SEC = 300  # 5 minutes max backoff

_running_tasks: dict[int, asyncio.Task] = {}


class WorkerMode(StrEnum):
    CONNECTING = "connecting"
    IDLE = "idle"
    POLLING = "polling"
    PROCESSING = "processing"
    ERROR_BACKOFF = "error_backoff"


@dataclass
class WorkerState:
    folder_id: int
    account_id: int
    mode: str = WorkerMode.CONNECTING
    last_scan_at: datetime | None = None
    next_scan_at: datetime | None = None
    last_activity_at: datetime | None = None
    queue_total: int = 0
    queue_position: int = 0
    current_email_subject: str | None = None
    current_email_sender: str | None = None
    error: str | None = None

    def clear_queue(self):
        self.queue_total = 0
        self.queue_position = 0
        self.current_email_subject = None
        self.current_email_sender = None


_worker_state: dict[int, WorkerState] = {}
_global_task: asyncio.Task | None = None
_global_state: WorkerState | None = None


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_email_from_header(from_header: str) -> str:
    """Extract bare email from 'Display Name <email@example.com>' format."""
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).lower()
    return from_header.strip().lower()


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return h2t.handle(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            return h2t.handle(text)
        return text
    return ""


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
    """Connect, login, check IDLE capability, select folder.

    Returns (imap_client, idle_supported). Updates account.idle_supported in DB.
    If IDLE not supported, forces account.use_polling = True.
    """
    from app.core.encryption import decrypt_value

    password = decrypt_value(account.imap_password_encrypted)
    imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
    await imap.wait_hello_from_server()
    await imap.login(account.imap_user, password)

    # Check IDLE capability (must check after login — some servers only advertise post-auth)
    idle_supported = imap.has_capability("IDLE")

    # Update idle_supported in DB; force use_polling if IDLE not supported
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

    # UIDVALIDITY check
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

        # aioimaplib returns a flat list: [b'header', bytearray(email_bytes), b')']
        raw_email = None
        for part in msg_data:
            if isinstance(part, bytearray):
                raw_email = bytes(part)
                break
        if raw_email is None:
            continue
        msg = email.message_from_bytes(raw_email)

        subject = _decode_header_value(msg.get("Subject", ""))
        sender = _decode_header_value(msg.get("From", ""))
        message_id = msg.get("Message-ID", "")
        body = _extract_body(msg)

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

        # Dedup check
        existing = await db.execute(
            select(ProcessedEmail).where(ProcessedEmail.message_id == message_id)
        )
        if existing.scalar_one_or_none():
            folder.last_seen_uid = uid
            await db.commit()
            continue

        queue_item = QueueItem(
            user_id=account.user_id,
            status="queued",
            source_type="email",
            source_info=f"{account.imap_user} / {folder.folder_path}",
            raw_data={
                "subject": subject,
                "sender": sender,
                "body": body,
                "message_id": message_id,
                "email_uid": uid,
                "email_date": email_date.isoformat() if email_date else None,
            },
        )
        db.add(queue_item)
        await db.flush()

        processed = ProcessedEmail(
            account_id=account.id,
            folder_path=folder.folder_path,
            email_uid=uid,
            message_id=message_id,
            queue_item_id=queue_item.id,
        )
        db.add(processed)

        folder.last_seen_uid = uid
        await db.commit()

    if state:
        state.last_scan_at = datetime.now(timezone.utc)
        state.clear_queue()


async def _fetch_global_emails(
    imap: IMAP4_SSL, config: GlobalMailConfig, db, state: WorkerState | None,
) -> None:
    """Fetch new emails from global inbox, gate on sender address."""
    max_age = 7
    result = await db.execute(select(ImapSettings))
    global_settings = result.scalar_one_or_none()
    if global_settings:
        max_age = global_settings.max_email_age_days

    since_date = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%d-%b-%Y")
    search_criteria = f"UID {config.last_seen_uid + 1}:* SINCE {since_date}"
    _, data = await imap.uid_search(search_criteria)
    uids = data[0].split() if data[0] else []

    if state:
        if uids:
            state.mode = WorkerMode.PROCESSING
            state.queue_total = len(uids)
        state.last_activity_at = datetime.now(timezone.utc)

    for i, uid_bytes in enumerate(uids):
        uid = int(uid_bytes)
        if uid <= config.last_seen_uid:
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

        sender = _decode_header_value(msg.get("From", ""))
        sender_email = _extract_email_from_header(sender)

        # Sender gate: look up in UserSenderAddress
        result = await db.execute(
            select(UserSenderAddress).where(UserSenderAddress.email_address == sender_email)
        )
        sender_addr = result.scalar_one_or_none()
        if not sender_addr:
            logger.info(f"Global mail: discarding email from unregistered sender: {sender_email}")
            config.last_seen_uid = uid
            await db.commit()
            continue

        subject = _decode_header_value(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        body = _extract_body(msg)

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

        # Dedup check
        existing = await db.execute(
            select(ProcessedEmail).where(ProcessedEmail.message_id == message_id)
        )
        if existing.scalar_one_or_none():
            config.last_seen_uid = uid
            await db.commit()
            continue

        queue_item = QueueItem(
            user_id=sender_addr.user_id,
            status="queued",
            source_type="email",
            source_info=f"global / {config.watched_folder_path}",
            raw_data={
                "subject": subject,
                "sender": sender,
                "body": body,
                "message_id": message_id,
                "email_uid": uid,
                "email_date": email_date.isoformat() if email_date else None,
            },
        )
        db.add(queue_item)
        await db.flush()

        processed = ProcessedEmail(
            account_id=None,
            folder_path=config.watched_folder_path,
            email_uid=uid,
            message_id=message_id,
            queue_item_id=queue_item.id,
            source="global_mail",
        )
        db.add(processed)

        config.last_seen_uid = uid
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
                # 24-minute timeout — re-issue IDLE (no new mail)
                imap.idle_done()
                await asyncio.wait_for(idle_task, timeout=5)
                continue

            # Got a real notification (EXISTS, EXPUNGE, etc.)
            imap.idle_done()
            await asyncio.wait_for(idle_task, timeout=5)

            # Check if it's an EXISTS notification (new mail)
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
            return  # Break to outer reconnect loop


async def _poll_loop(
    account_id: int, folder_id: int, polling_interval_sec: int,
    state: WorkerState | None,
) -> None:
    """Polling loop. Disconnects between cycles. Returns on connection error."""
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

                # Pick up any interval changes for next cycle
                interval = account.polling_interval_sec

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Poll cycle error for folder {folder_id}: {e}")
            return  # Break to outer reconnect loop


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

                # Initial fetch of new emails
                await _fetch_new_emails(imap, account, folder, db, state)

                # Reset backoff on successful connect + fetch
                backoff = 30

                if not account.use_polling and idle_supported:
                    # IDLE mode — persistent connection
                    await _idle_loop(imap, account, folder, db, state)
                else:
                    # Polling mode — disconnect first, then loop
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

        # Exponential backoff before reconnect
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_SEC)


async def _global_idle_loop(
    imap: IMAP4_SSL, config: GlobalMailConfig, db, state: WorkerState | None,
) -> None:
    """Persistent IDLE loop for global mail. Returns only on connection error."""
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
                await _fetch_global_emails(imap, config, db, state)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Global IDLE loop error: {e}")
            try:
                imap.idle_done()
            except Exception:
                pass
            return


async def _global_poll_loop(
    polling_interval_sec: int, state: WorkerState | None,
) -> None:
    """Polling loop for global mail. Disconnects between cycles."""
    from app.core.encryption import decrypt_value

    interval = polling_interval_sec
    while True:
        if state:
            state.mode = WorkerMode.POLLING
            state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=interval)

        await asyncio.sleep(interval)

        try:
            async with async_session() as db:
                result = await db.execute(select(GlobalMailConfig))
                config = result.scalar_one_or_none()
                if not config or not config.is_active:
                    return

                password = decrypt_value(config.imap_password_encrypted)
                imap = IMAP4_SSL(host=config.imap_host, port=config.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(config.imap_user, password)
                await imap.select(config.watched_folder_path)

                await _fetch_global_emails(imap, config, db, state)
                try:
                    await imap.logout()
                except Exception:
                    pass

                interval = config.polling_interval_sec

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Global poll cycle error: {e}")
            return


async def _watch_global_folder(config: GlobalMailConfig) -> None:
    """Watch the global IMAP folder using IDLE or polling."""
    from app.core.encryption import decrypt_value

    global _global_state
    backoff = 30

    while True:
        state = _global_state
        if state:
            state.mode = WorkerMode.CONNECTING
            state.next_scan_at = None
            state.clear_queue()
            state.error = None

        try:
            async with async_session() as db:
                # Re-fetch config from DB to pick up changes
                result = await db.execute(select(GlobalMailConfig))
                config = result.scalar_one_or_none()
                if not config or not config.is_active:
                    logger.info("Stopping global mail watcher: inactive or removed")
                    return

                password = decrypt_value(config.imap_password_encrypted)
                imap = IMAP4_SSL(host=config.imap_host, port=config.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(config.imap_user, password)

                # Check IDLE capability
                idle_supported = imap.has_capability("IDLE")
                if config.idle_supported != idle_supported:
                    config.idle_supported = idle_supported
                    if not idle_supported and not config.use_polling:
                        config.use_polling = True
                        logger.info("Global mail: IDLE not supported, forcing polling mode")
                    await db.commit()
                    await db.refresh(config)

                await imap.select(config.watched_folder_path)

                # Initial fetch
                await _fetch_global_emails(imap, config, db, state)

                # Reset backoff on successful connect + fetch
                backoff = 30

                if not config.use_polling and idle_supported:
                    await _global_idle_loop(imap, config, db, state)
                else:
                    try:
                        await imap.logout()
                    except Exception:
                        pass
                    await _global_poll_loop(config.polling_interval_sec, state)

        except asyncio.CancelledError:
            logger.info("Global mail watcher cancelled")
            return
        except Exception as e:
            logger.error(f"Error watching global mail folder: {e}")
            if state:
                state.mode = WorkerMode.ERROR_BACKOFF
                state.error = str(e)
                state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)

        # Exponential backoff before reconnect
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_SEC)


def _start_global_watcher(config: GlobalMailConfig) -> None:
    global _global_task, _global_state
    if _global_task and not _global_task.done():
        _global_task.cancel()
    _global_state = WorkerState(
        folder_id=0,
        account_id=0,
        mode=WorkerMode.CONNECTING,
    )
    _global_task = asyncio.create_task(_watch_global_folder(config))


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

    # Start global mail watcher if enabled
    async with async_session() as db:
        result = await db.execute(select(ModuleConfig).where(ModuleConfig.module_key == "email-global"))
        module = result.scalar_one_or_none()
        if module and module.enabled:
            result = await db.execute(select(GlobalMailConfig))
            config = result.scalar_one_or_none()
            if config and config.is_active:
                _start_global_watcher(config)
                logger.info("Global mail watcher started")


async def stop_all_watchers():
    """Stop all running watchers."""
    for key, task in _running_tasks.items():
        task.cancel()
    _running_tasks.clear()
    _worker_state.clear()

    global _global_task, _global_state
    if _global_task and not _global_task.done():
        _global_task.cancel()
        try:
            await _global_task
        except asyncio.CancelledError:
            pass
    _global_task = None
    _global_state = None


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


def is_folder_scanning(folder_id: int) -> bool:
    """Check if a folder is currently mid-scan (processing emails)."""
    state = _worker_state.get(folder_id)
    return state is not None and state.mode == WorkerMode.PROCESSING
