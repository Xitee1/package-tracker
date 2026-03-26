"""Shared IMAP watch loop logic used by both user and global email watchers.

Provides generic async functions for IDLE/poll loops, email fetching, and
reconnection with exponential backoff. Provider-specific behavior is injected
via the ImapWatcherCallbacks dataclass.
"""

import asyncio
import email as email_mod
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

from aioimaplib import IMAP4_SSL, STOP_WAIT_SERVER_PUSH
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.modules._shared.email.imap_client import decode_header_value, extract_body
from app.modules._shared.email.imap_watcher import (
    IDLE_TIMEOUT_SEC,
    MAX_BACKOFF_SEC,
    WorkerMode,
    WorkerState,
)
from app.modules._shared.email.email_fetcher import check_dedup_and_enqueue

logger = logging.getLogger(__name__)


def generate_fallback_message_id(
    account_id: int, folder_path: str, uidvalidity: int | None, uid: int,
) -> str:
    """Generate a deterministic fallback Message-ID for emails missing one."""
    uidvalidity_part = str(uidvalidity) if uidvalidity is not None else "no-uidvalidity"
    folder_hash = hashlib.sha256(folder_path.encode()).hexdigest()[:16]
    return f"fallback:{account_id}:{folder_hash}:{uidvalidity_part}:{uid}"


@dataclass
class ConnectResult:
    """Result from a successful connect callback."""
    imap: IMAP4_SSL
    idle_supported: bool
    use_polling: bool
    polling_interval_sec: int


@dataclass
class FetchContext:
    """Per-cycle context for email fetching, loaded fresh each cycle."""
    last_seen_uid: int
    folder_path: str
    uidvalidity: int | None
    max_email_age_days: int
    source_info: str
    source_label: str
    account_id: int | None


# Type aliases for callbacks
RouteResult = tuple[int, str] | None  # (user_id, source) or None to skip


@dataclass
class ImapWatcherCallbacks:
    """Provider-specific behavior injected into the generic watch loop.

    connect:           Open a DB session, validate liveness, connect to IMAP,
                       return ConnectResult or None to stop.
    load_fetch_context: Given a DB session, return FetchContext for the current cycle.
    route_email:       Given sender email, DB session, return (user_id, source)
                       or None to skip the email.
    save_uid:          Persist the new last_seen_uid after processing an email.
    log_label:         Human-readable label for log messages (e.g. "folder 5").
    """
    connect: Callable[[AsyncSession], Awaitable[ConnectResult | None]]
    load_fetch_context: Callable[[AsyncSession], Awaitable[FetchContext | None]]
    route_email: Callable[[str, AsyncSession], Awaitable[RouteResult]]
    save_uid: Callable[[int, AsyncSession], Awaitable[None]]
    log_label: str


async def fetch_new_emails(
    imap: IMAP4_SSL,
    ctx: FetchContext,
    callbacks: ImapWatcherCallbacks,
    db: AsyncSession,
    state: WorkerState | None,
) -> None:
    """UID-search for new emails, process and enqueue them."""
    since_date = (
        datetime.now(timezone.utc) - timedelta(days=ctx.max_email_age_days)
    ).strftime("%d-%b-%Y")
    search_criteria = f"UID {ctx.last_seen_uid + 1}:* SINCE {since_date}"
    _, data = await imap.uid_search(search_criteria)
    uids = data[0].split() if data[0] else []

    if state:
        if uids:
            state.mode = WorkerMode.PROCESSING
            state.queue_total = len(uids)
        state.last_activity_at = datetime.now(timezone.utc)

    for i, uid_bytes in enumerate(uids):
        uid = int(uid_bytes)
        if uid <= ctx.last_seen_uid:
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
        msg = email_mod.message_from_bytes(raw_email)

        subject = decode_header_value(msg.get("Subject", ""))
        sender = decode_header_value(msg.get("From", ""))
        message_id = msg.get("Message-ID", "")
        if not message_id or not message_id.strip():
            message_id = generate_fallback_message_id(
                ctx.account_id or 0, ctx.folder_path, ctx.uidvalidity, uid,
            )
        body = extract_body(msg)

        email_date = None
        try:
            date_str = msg.get("Date", "")
            if date_str:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
        except Exception:
            pass

        # Route: determine user_id + source, or skip
        route = await callbacks.route_email(sender, db)
        if route is None:
            await callbacks.save_uid(uid, db)
            continue
        user_id, source = route

        if state:
            state.queue_position = i + 1
            state.current_email_subject = subject
            state.current_email_sender = sender
            state.last_activity_at = datetime.now(timezone.utc)

        await check_dedup_and_enqueue(
            message_id=message_id,
            subject=subject,
            sender=sender,
            body=body,
            email_date=email_date,
            email_uid=uid,
            user_id=user_id,
            source_info=ctx.source_info,
            account_id=ctx.account_id,
            folder_path=ctx.folder_path,
            source=source,
            db=db,
        )

        await callbacks.save_uid(uid, db)

    if state:
        state.last_scan_at = datetime.now(timezone.utc)
        state.clear_queue()


async def idle_loop(
    imap: IMAP4_SSL,
    ctx: FetchContext,
    callbacks: ImapWatcherCallbacks,
    db: AsyncSession,
    state: WorkerState | None,
) -> None:
    """Persistent IDLE loop. Returns only on connection error (to trigger reconnect)."""
    while True:
        if state:
            state.mode = WorkerMode.IDLE
            state.next_scan_at = None
            state.last_activity_at = datetime.now(timezone.utc)

        try:
            idle_task = await imap.idle_start(timeout=IDLE_TIMEOUT_SEC)
            server_msg = await imap.wait_server_push()

            if server_msg == STOP_WAIT_SERVER_PUSH:
                imap.idle_done()
                await asyncio.wait_for(idle_task, timeout=5)
                continue

            imap.idle_done()
            await asyncio.wait_for(idle_task, timeout=5)

            has_new = False
            if isinstance(server_msg, list):
                for line in server_msg:
                    line_str = line.decode() if isinstance(line, bytes) else str(line)
                    if "EXISTS" in line_str:
                        has_new = True
                        break

            if has_new:
                await fetch_new_emails(imap, ctx, callbacks, db, state)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"IDLE loop error for {callbacks.log_label}: {e}")
            try:
                imap.idle_done()
            except Exception:
                pass
            return


async def poll_loop(
    callbacks: ImapWatcherCallbacks,
    polling_interval_sec: int,
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
                connect_result = await callbacks.connect(db)
                if connect_result is None:
                    return

                ctx = await callbacks.load_fetch_context(db)
                if ctx is None:
                    return

                await fetch_new_emails(
                    connect_result.imap, ctx, callbacks, db, state,
                )
                try:
                    await connect_result.imap.logout()
                except Exception:
                    pass

                interval = connect_result.polling_interval_sec

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Poll cycle error for {callbacks.log_label}: {e}")
            return


async def watch_loop(
    callbacks: ImapWatcherCallbacks,
    state: WorkerState | None,
) -> None:
    """Top-level watch loop with exponential backoff on errors."""
    backoff = 30

    while True:
        if state:
            state.mode = WorkerMode.CONNECTING
            state.next_scan_at = None
            state.clear_queue()
            state.error = None

        try:
            async with async_session() as db:
                connect_result = await callbacks.connect(db)
                if connect_result is None:
                    logger.info(
                        f"Stopping watcher for {callbacks.log_label}: "
                        "inactive or removed"
                    )
                    return

                ctx = await callbacks.load_fetch_context(db)
                if ctx is None:
                    return

                await fetch_new_emails(
                    connect_result.imap, ctx, callbacks, db, state,
                )

                backoff = 30

                if not connect_result.use_polling and connect_result.idle_supported:
                    await idle_loop(
                        connect_result.imap, ctx, callbacks, db, state,
                    )
                else:
                    try:
                        await connect_result.imap.logout()
                    except Exception:
                        pass
                    await poll_loop(
                        callbacks, connect_result.polling_interval_sec, state,
                    )

        except asyncio.CancelledError:
            logger.info(f"Watcher cancelled for {callbacks.log_label}")
            return
        except Exception as e:
            logger.error(f"Error watching {callbacks.log_label}: {e}")
            if state:
                state.mode = WorkerMode.ERROR_BACKOFF
                state.error = str(e)
                state.next_scan_at = datetime.now(timezone.utc) + timedelta(
                    seconds=backoff
                )

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_SEC)
