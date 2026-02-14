import asyncio
import email
import logging
from datetime import datetime, timedelta, timezone

from aioimaplib import IMAP4_SSL, STOP_WAIT_SERVER_PUSH
from sqlalchemy import select

from app.database import async_session
from app.models.imap_settings import ImapSettings
from app.models.module_config import ModuleConfig
from app.modules._shared.email.imap_client import decode_header_value, extract_email_from_header, extract_body
from app.modules._shared.email.imap_watcher import WorkerMode, WorkerState, IDLE_TIMEOUT_SEC, MAX_BACKOFF_SEC
from app.modules._shared.email.email_fetcher import check_dedup_and_enqueue
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress

logger = logging.getLogger(__name__)

_global_task: asyncio.Task | None = None
_global_state: WorkerState | None = None


def get_global_state() -> WorkerState | None:
    return _global_state


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

        sender = decode_header_value(msg.get("From", ""))
        sender_email = extract_email_from_header(sender)

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

        subject = decode_header_value(msg.get("Subject", ""))
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
            user_id=sender_addr.user_id,
            source_info=f"global / {config.watched_folder_path}",
            account_id=None,
            folder_path=config.watched_folder_path,
            source="global_mail",
            db=db,
        )

        config.last_seen_uid = uid
        await db.commit()

    if state:
        state.last_scan_at = datetime.now(timezone.utc)
        state.clear_queue()


async def _global_idle_loop(
    imap: IMAP4_SSL, config: GlobalMailConfig, db, state: WorkerState | None,
) -> None:
    """Persistent IDLE loop for global mail."""
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
    """Polling loop for global mail."""
    from app.core.encryption import decrypt_value

    interval = polling_interval_sec
    while True:
        if state:
            state.mode = WorkerMode.POLLING
            state.next_scan_at = datetime.now(timezone.utc) + timedelta(seconds=interval)

        await asyncio.sleep(interval)

        try:
            async with async_session() as db:
                mod_result = await db.execute(
                    select(ModuleConfig).where(ModuleConfig.module_key == "email-global")
                )
                module = mod_result.scalar_one_or_none()
                if not module or not module.enabled:
                    logger.info("Stopping global poll loop: module disabled")
                    return

                result = await db.execute(select(GlobalMailConfig))
                config = result.scalar_one_or_none()
                if not config:
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
                mod_result = await db.execute(
                    select(ModuleConfig).where(ModuleConfig.module_key == "email-global")
                )
                module = mod_result.scalar_one_or_none()
                if not module or not module.enabled:
                    logger.info("Stopping global mail watcher: module disabled")
                    return

                result = await db.execute(select(GlobalMailConfig))
                config = result.scalar_one_or_none()
                if not config:
                    logger.info("Stopping global mail watcher: inactive or removed")
                    return

                password = decrypt_value(config.imap_password_encrypted)
                imap = IMAP4_SSL(host=config.imap_host, port=config.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(config.imap_user, password)

                idle_supported = imap.has_capability("IDLE")
                if config.idle_supported != idle_supported:
                    config.idle_supported = idle_supported
                    if not idle_supported and not config.use_polling:
                        config.use_polling = True
                        logger.info("Global mail: IDLE not supported, forcing polling mode")
                    await db.commit()
                    await db.refresh(config)

                await imap.select(config.watched_folder_path)

                await _fetch_global_emails(imap, config, db, state)

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


async def start_global_watcher():
    """Startup hook: start global mail watcher if configured."""
    async with async_session() as db:
        result = await db.execute(select(GlobalMailConfig))
        config = result.scalar_one_or_none()
        if config:
            _start_global_watcher(config)
            logger.info("Global mail watcher started")


async def stop_global_watcher():
    """Shutdown hook: stop global mail watcher."""
    global _global_task, _global_state
    if _global_task and not _global_task.done():
        _global_task.cancel()
        try:
            await _global_task
        except asyncio.CancelledError:
            pass
    _global_task = None
    _global_state = None


async def get_status(db) -> dict | None:
    """Status hook: return global mail watcher state."""
    result = await db.execute(select(GlobalMailConfig))
    config = result.scalar_one_or_none()
    if not config:
        return None

    state = _global_state
    task = _global_task

    is_running = task is not None and not task.done()

    if state:
        mode = state.mode
    elif not is_running:
        mode = "stopped"
    else:
        mode = "unknown"

    from sqlalchemy import func
    sender_result = await db.execute(
        select(func.count()).select_from(UserSenderAddress)
    )
    registered_senders = sender_result.scalar() or 0

    return {
        "watching": config.watched_folder_path,
        "running": is_running,
        "mode": mode,
        "registered_senders": registered_senders,
        "last_scan_at": state.last_scan_at.isoformat() if state and state.last_scan_at else None,
        "next_scan_at": state.next_scan_at.isoformat() if state and state.next_scan_at else None,
        "last_activity_at": state.last_activity_at.isoformat() if state and state.last_activity_at else None,
        "error": state.error if state else None,
    }
