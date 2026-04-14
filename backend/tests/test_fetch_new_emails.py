"""Tests for fetch_new_emails keeping ctx.last_seen_uid in sync."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules._shared.email.imap_watch_loop import (
    FetchContext,
    ImapWatcherCallbacks,
    fetch_new_emails,
)
from app.modules._shared.email.imap_watcher import WorkerState


def _make_callbacks(route_result=None) -> ImapWatcherCallbacks:
    """Build mock callbacks for testing."""
    return ImapWatcherCallbacks(
        connect=AsyncMock(),
        load_fetch_context=AsyncMock(),
        route_email=AsyncMock(return_value=route_result),
        save_uid=AsyncMock(),
        log_label="test",
    )


def _make_imap(uids: list[int], email_bytes: bytes = b"From: a@b.c\nSubject: test\n\nBody"):
    """Build a mock IMAP client that returns the given UIDs and a fixed email."""
    imap = AsyncMock()
    uid_str = " ".join(str(u) for u in uids).encode()
    imap.uid_search = AsyncMock(return_value=("OK", [uid_str] if uids else [b""]))
    imap.uid = AsyncMock(return_value=("OK", [bytearray(email_bytes)]))
    return imap


@pytest.mark.asyncio
async def test_ctx_last_seen_uid_updated_after_processing():
    """ctx.last_seen_uid must advance as emails are processed."""
    ctx = FetchContext(
        last_seen_uid=10,
        folder_path="INBOX",
        uidvalidity=123,
        max_email_age_days=7,
        source_info="test",
        source_label="test",
        account_id=1,
    )
    callbacks = _make_callbacks(route_result=(1, "test"))
    imap = _make_imap([11, 12, 13])
    db = AsyncMock()

    with patch(
        "app.modules._shared.email.imap_watch_loop.check_dedup_and_enqueue",
        new_callable=AsyncMock,
        return_value=True,
    ):
        await fetch_new_emails(imap, ctx, callbacks, db, state=None)

    assert ctx.last_seen_uid == 13


@pytest.mark.asyncio
async def test_ctx_last_seen_uid_updated_on_skipped_route():
    """ctx.last_seen_uid must advance even when route_email returns None (email skipped)."""
    ctx = FetchContext(
        last_seen_uid=5,
        folder_path="INBOX",
        uidvalidity=123,
        max_email_age_days=7,
        source_info="test",
        source_label="test",
        account_id=1,
    )
    callbacks = _make_callbacks(route_result=None)  # all emails skipped
    imap = _make_imap([6, 7])
    db = AsyncMock()

    await fetch_new_emails(imap, ctx, callbacks, db, state=None)

    assert ctx.last_seen_uid == 7


@pytest.mark.asyncio
async def test_ctx_last_seen_uid_unchanged_when_no_new_emails():
    """ctx.last_seen_uid stays the same when there are no new UIDs."""
    ctx = FetchContext(
        last_seen_uid=10,
        folder_path="INBOX",
        uidvalidity=123,
        max_email_age_days=7,
        source_info="test",
        source_label="test",
        account_id=1,
    )
    callbacks = _make_callbacks()
    imap = _make_imap([])
    db = AsyncMock()

    await fetch_new_emails(imap, ctx, callbacks, db, state=None)

    assert ctx.last_seen_uid == 10
