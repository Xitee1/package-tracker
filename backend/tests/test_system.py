import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.models.user import User
from app.core.auth import hash_password, create_access_token
from app.modules._shared.email.imap_watcher import WorkerState, WorkerMode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "pass123"},
    )
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "regular", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "regular", "password": "pass"},
    )
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helper to seed a user -> account -> folder chain in the DB
# ---------------------------------------------------------------------------

async def _seed_user_account_folder(db_session, *, username="worker_user", folder_path="INBOX"):
    """Create a User, EmailAccount, and WatchedFolder; return (user, account, folder)."""
    user = User(
        username=username,
        password_hash=hash_password("pw"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()

    account = EmailAccount(
        user_id=user.id,
        name="Test Mail",
        imap_host="imap.test.com",
        imap_port=993,
        imap_user="u@test.com",
        imap_password_encrypted="enc",
        use_ssl=True,
        polling_interval_sec=120,
        is_active=True,
    )
    db_session.add(account)
    await db_session.flush()

    folder = WatchedFolder(
        account_id=account.id,
        folder_path=folder_path,
        last_seen_uid=0,
    )
    db_session.add(folder)
    await db_session.flush()
    await db_session.commit()

    return user, account, folder


# ===========================================================================
# /api/v1/system/status tests
# ===========================================================================


@pytest.mark.asyncio
async def test_status_empty(client, admin_token):
    """With no email accounts/folders the response should have an empty users list and zero global counts."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200

    data = resp.json()

    # Global counters should all be zero
    g = data["global"]
    assert g["total_folders"] == 0
    assert g["running"] == 0
    assert g["errors"] == 0
    assert g["queue_total"] == 0
    assert g["processing_folders"] == 0

    # Queue stats should exist with all zeros
    q = data["queue"]
    assert q["queued"] == 0
    assert q["processing"] == 0
    assert q["completed"] == 0
    assert q["failed"] == 0

    # The admin user exists but has no email accounts, so the endpoint skips
    # users without accounts -- the users list should be empty.
    assert data["users"] == []


@pytest.mark.asyncio
async def test_status_with_folders(client, admin_token, db_session):
    """Create a user with an account and folder, mock worker dicts, verify full response structure."""
    user, account, folder = await _seed_user_account_folder(db_session)

    # Build mock asyncio.Task that looks "running"
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False

    now = datetime.now(timezone.utc)
    state = WorkerState(
        folder_id=folder.id,
        account_id=account.id,
        mode=WorkerMode.PROCESSING,
        last_scan_at=now - timedelta(minutes=1),
        next_scan_at=now + timedelta(minutes=1),
        last_activity_at=now,
        queue_total=5,
        queue_position=2,
        current_email_subject="Your order shipped",
        current_email_sender="shop@example.com",
        error=None,
    )

    with (
        patch("app.api.system._running_tasks", {folder.id: mock_task}),
        patch("app.api.system._worker_state", {folder.id: state}),
    ):
        resp = await client.get("/api/v1/system/status", headers=auth(admin_token))

    assert resp.status_code == 200
    data = resp.json()

    # Global counters
    g = data["global"]
    assert g["total_folders"] == 1
    assert g["running"] == 1
    assert g["errors"] == 0
    assert g["queue_total"] == 3  # remaining = max(0, 5 - 2) = 3
    assert g["processing_folders"] == 1

    # Queue section should exist
    assert "queue" in data

    # User hierarchy
    assert len(data["users"]) == 1
    u = data["users"][0]
    assert u["user_id"] == user.id
    assert u["username"] == user.username

    assert len(u["accounts"]) == 1
    a = u["accounts"][0]
    assert a["account_id"] == account.id
    assert a["account_name"] == account.name
    assert a["is_active"] is True

    assert len(a["folders"]) == 1
    f = a["folders"][0]
    assert f["folder_id"] == folder.id
    assert f["folder_path"] == "INBOX"
    assert f["running"] is True
    assert f["mode"] == "processing"
    assert f["queue_total"] == 5
    assert f["queue_position"] == 2
    assert f["current_email_subject"] == "Your order shipped"
    assert f["current_email_sender"] == "shop@example.com"
    assert f["error"] is None
    # Timestamps should be non-null ISO strings
    assert f["last_scan_at"] is not None
    assert f["next_scan_at"] is not None
    assert f["last_activity_at"] is not None


@pytest.mark.asyncio
async def test_status_with_errored_task(client, admin_token, db_session):
    """A finished task with an exception should surface the error in the response."""
    _user, _account, folder = await _seed_user_account_folder(db_session)

    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = True
    mock_task.exception.return_value = RuntimeError("IMAP connection refused")

    with (
        patch("app.api.system._running_tasks", {folder.id: mock_task}),
        patch("app.api.system._worker_state", {}),
    ):
        resp = await client.get("/api/v1/system/status", headers=auth(admin_token))

    assert resp.status_code == 200
    data = resp.json()

    g = data["global"]
    assert g["errors"] == 1
    assert g["running"] == 0

    f = data["users"][0]["accounts"][0]["folders"][0]
    assert f["running"] is False
    assert f["mode"] == "stopped"
    assert "IMAP connection refused" in f["error"]


@pytest.mark.asyncio
async def test_status_has_queue_section(client, admin_token):
    """System status should include a queue section with status counts."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()

    assert "queue" in data
    q = data["queue"]
    assert "queued" in q
    assert "processing" in q
    assert "completed" in q
    assert "failed" in q


@pytest.mark.asyncio
async def test_status_has_scheduled_jobs(client, admin_token):
    """System status should include a scheduled_jobs list."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "scheduled_jobs" in data
    assert isinstance(data["scheduled_jobs"], list)


@pytest.mark.asyncio
async def test_status_requires_admin(client, user_token):
    """Non-admin users should receive 403."""
    resp = await client.get("/api/v1/system/status", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_status_unauthenticated(client):
    """Unauthenticated requests should be rejected."""
    resp = await client.get("/api/v1/system/status")
    assert resp.status_code in (401, 403)
