import asyncio
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.imap_settings import ImapSettings
from app.models.module_config import ModuleConfig
from app.modules._shared.email.imap_client import extract_email_from_header
from app.modules._shared.email.imap_watcher import WorkerMode, WorkerState
from app.modules._shared.email.imap_watch_loop import (
    ConnectResult,
    FetchContext,
    ImapWatcherCallbacks,
    watch_loop,
)
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress

logger = logging.getLogger(__name__)

_global_task: asyncio.Task | None = None
_global_state: WorkerState | None = None


def get_global_state() -> WorkerState | None:
    return _global_state


def _build_global_callbacks() -> ImapWatcherCallbacks:
    """Build provider-specific callbacks for the global mail watcher."""

    async def connect(db: AsyncSession) -> ConnectResult | None:
        from aioimaplib import IMAP4_SSL
        from app.core.encryption import decrypt_value

        mod_result = await db.execute(
            select(ModuleConfig).where(ModuleConfig.module_key == "email-global")
        )
        module = mod_result.scalar_one_or_none()
        if not module or not module.enabled:
            logger.info("Stopping global mail watcher: module disabled")
            return None

        result = await db.execute(select(GlobalMailConfig))
        config = result.scalar_one_or_none()
        if not config:
            logger.info("Stopping global mail watcher: inactive or removed")
            return None

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

        return ConnectResult(
            imap=imap,
            idle_supported=idle_supported,
            use_polling=config.use_polling,
            polling_interval_sec=config.polling_interval_sec,
        )

    async def load_fetch_context(db: AsyncSession) -> FetchContext | None:
        result = await db.execute(select(GlobalMailConfig))
        config = result.scalar_one_or_none()
        if not config:
            return None

        max_age = 7
        settings_result = await db.execute(select(ImapSettings))
        global_settings = settings_result.scalar_one_or_none()
        if global_settings:
            max_age = global_settings.max_email_age_days

        return FetchContext(
            last_seen_uid=config.last_seen_uid,
            folder_path=config.watched_folder_path,
            uidvalidity=config.uidvalidity,
            max_email_age_days=max_age,
            source_info=f"global / {config.watched_folder_path}",
            source_label="global mail",
            account_id=None,
        )

    async def route_email(sender: str, db: AsyncSession):
        sender_email = extract_email_from_header(sender)
        result = await db.execute(
            select(UserSenderAddress).where(
                UserSenderAddress.email_address == sender_email
            )
        )
        sender_addr = result.scalar_one_or_none()
        if not sender_addr:
            logger.info(
                f"Global mail: discarding email from unregistered sender: {sender_email}"
            )
            return None
        return (sender_addr.user_id, "global_mail")

    async def save_uid(uid: int, db: AsyncSession) -> None:
        result = await db.execute(select(GlobalMailConfig))
        config = result.scalar_one_or_none()
        if config:
            config.last_seen_uid = uid
            await db.commit()

    return ImapWatcherCallbacks(
        connect=connect,
        load_fetch_context=load_fetch_context,
        route_email=route_email,
        save_uid=save_uid,
        log_label="global mail",
    )


def _start_global_watcher(config: GlobalMailConfig) -> None:
    global _global_task, _global_state
    if _global_task and not _global_task.done():
        _global_task.cancel()
    _global_state = WorkerState(
        folder_id=0,
        account_id=0,
        mode=WorkerMode.CONNECTING,
    )
    callbacks = _build_global_callbacks()
    _global_task = asyncio.create_task(watch_loop(callbacks, _global_state))


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


async def get_status(db: AsyncSession) -> dict | None:
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
