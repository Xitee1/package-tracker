import asyncio
import email
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from enum import StrEnum

import html2text
from aioimaplib import IMAP4_SSL
from sqlalchemy import select

from app.database import async_session
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.imap_settings import ImapSettings
from app.models.processed_email import ProcessedEmail
from app.models.queue_item import QueueItem

logger = logging.getLogger(__name__)
h2t = html2text.HTML2Text()
h2t.ignore_links = False

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


async def _get_effective_settings(db, folder: WatchedFolder) -> tuple[int, float, bool]:
    """Return (max_email_age_days, processing_delay_sec, check_uidvalidity) for a folder."""
    result = await db.execute(select(ImapSettings))
    global_settings = result.scalar_one_or_none()

    max_age = folder.max_email_age_days
    if max_age is None:
        max_age = global_settings.max_email_age_days if global_settings else 7

    delay = folder.processing_delay_sec
    if delay is None:
        delay = global_settings.processing_delay_sec if global_settings else 2.0

    check_uid = global_settings.check_uidvalidity if global_settings else True

    return max_age, delay, check_uid


async def _watch_folder(account_id: int, folder_id: int):
    """Watch a single IMAP folder for new messages using IDLE + polling fallback."""
    while True:
        # Update state: entering connection phase
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
                    logger.info(f"Stopping watcher for folder {folder_id}: account/folder removed or inactive")
                    return

                from app.core.encryption import decrypt_value
                password = decrypt_value(account.imap_password_encrypted)

                imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(account.imap_user, password)
                select_response = await imap.select(folder.folder_path)

                max_age, delay, check_uid = await _get_effective_settings(db, folder)

                # UIDVALIDITY check — parse from SELECT response
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
                                f"UIDVALIDITY changed for folder {folder_id}: "
                                f"{folder.uidvalidity} -> {current_uidvalidity}. Resetting."
                            )
                            folder.uidvalidity = current_uidvalidity
                            folder.last_seen_uid = 0
                            strict_age_sec = account.polling_interval_sec + 30
                            max_age = max(1, strict_age_sec // 86400) if strict_age_sec >= 86400 else 1
                            await db.commit()

                # Fetch new messages with age filter
                since_date = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%d-%b-%Y")
                search_criteria = f"UID {folder.last_seen_uid + 1}:* SINCE {since_date}"
                _, data = await imap.uid_search(search_criteria)
                uids = data[0].split() if data[0] else []

                # Update state: processing or skip to idle
                if state:
                    if uids:
                        state.mode = WorkerMode.PROCESSING
                        state.queue_total = len(uids)
                    else:
                        state.mode = WorkerMode.IDLE

                for i, uid_bytes in enumerate(uids):
                    uid = int(uid_bytes)
                    if uid <= folder.last_seen_uid:
                        continue

                    _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue

                    # aioimaplib typically returns a list of response lines, for example:
                    #   [b'1 FETCH (UID 1 RFC822 {size}', bytearray(email_bytes), b')', ...]
                    # or, depending on version/configuration, nested list/tuple structures.
                    # Find the literal data (bytearray/bytes) which contains the actual email.
                    def _extract_raw_email(parts):
                        for part in parts:
                            # Direct literal payload
                            if isinstance(part, (bytearray, bytes)):
                                return bytes(part)
                            # Nested structures (list/tuple) as in some aioimaplib responses
                            if isinstance(part, (list, tuple)):
                                nested = _extract_raw_email(part)
                                if nested is not None:
                                    return nested
                        return None

                    raw_email = _extract_raw_email(msg_data)
                    if raw_email is None:
                        continue
                    msg = email.message_from_bytes(raw_email)

                    subject = _decode_header_value(msg.get("Subject", ""))
                    sender = _decode_header_value(msg.get("From", ""))
                    message_id = msg.get("Message-ID", "")
                    
                    # Fallback for missing Message-ID: use deterministic dedup key
                    if not message_id:
                        uidvalidity_part = folder.uidvalidity if folder.uidvalidity is not None else "0"
                        message_id = f"fallback:{account_id}:{folder.folder_path}:{uidvalidity_part}:{uid}"
                    
                    body = _extract_body(msg)

                    email_date = None
                    try:
                        date_str = msg.get("Date", "")
                        if date_str:
                            from email.utils import parsedate_to_datetime
                            email_date = parsedate_to_datetime(date_str)
                    except Exception:
                        pass

                    # Update state: processing individual email
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

                    # Create queue item
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

                    # Record dedup entry
                    processed = ProcessedEmail(
                        account_id=account_id,
                        folder_path=folder.folder_path,
                        email_uid=uid,
                        message_id=message_id,
                        queue_item_id=queue_item.id,
                    )
                    db.add(processed)

                    folder.last_seen_uid = uid
                    await db.commit()

                    if delay > 0:
                        await asyncio.sleep(delay)

                # Update state: scan complete
                if state:
                    state.last_scan_at = datetime.now(timezone.utc)
                    state.clear_queue()

                # Try IDLE, fall back to polling
                try:
                    # Update state: entering IDLE
                    if state:
                        state.mode = WorkerMode.IDLE
                        state.last_activity_at = datetime.now(timezone.utc)
                    idle_task = await imap.idle_start(timeout=account.polling_interval_sec)
                    await asyncio.wait_for(idle_task, timeout=account.polling_interval_sec)
                except (asyncio.TimeoutError, Exception):
                    # Update state: falling back to polling
                    if state:
                        state.mode = WorkerMode.POLLING
                        state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=account.polling_interval_sec)
                finally:
                    try:
                        await imap.idle_done()
                    except Exception:
                        pass
                    try:
                        await imap.logout()
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info(f"Watcher cancelled for folder {folder_id}")
            return
        except Exception as e:
            logger.error(f"Error watching folder {folder_id}: {e}")
            # Update state: error backoff
            state = _worker_state.get(folder_id)
            if state:
                state.mode = WorkerMode.ERROR_BACKOFF
                state.error = str(e)
                state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            await asyncio.sleep(30)


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
    """Stop all running watchers."""
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


def is_folder_scanning(folder_id: int) -> bool:
    """Check if a folder is currently mid-scan (processing emails)."""
    state = _worker_state.get(folder_id)
    return state is not None and state.mode == WorkerMode.PROCESSING
