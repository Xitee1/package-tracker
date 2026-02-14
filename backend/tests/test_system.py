import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.email_account import EmailAccount, WatchedFolder
from app.models.user import User
from app.models.worker_stats import WorkerStats
from app.core.auth import hash_password, create_access_token
from app.services.imap_worker import WorkerState, WorkerMode


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
# Helper to seed a user → account → folder chain in the DB
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

    # The admin user exists but has no email accounts, so the endpoint skips
    # users without accounts — the users list should be empty.
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
async def test_status_requires_admin(client, user_token):
    """Non-admin users should receive 403."""
    resp = await client.get("/api/v1/system/status", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_status_unauthenticated(client):
    """Unauthenticated requests should be rejected."""
    resp = await client.get("/api/v1/system/status")
    assert resp.status_code in (401, 403)


# ===========================================================================
# /api/v1/system/stats tests
# ===========================================================================


@pytest.mark.asyncio
async def test_stats_hourly(client, admin_token, db_session):
    """Insert WorkerStats rows and verify hourly aggregation."""
    # We need a folder to satisfy the FK, so seed one.
    _user, _account, folder = await _seed_user_account_folder(db_session)

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    # Insert three rows in the same hour bucket (same folder) — these should
    # NOT be aggregated because they share the same hour_bucket + folder_id
    # (UniqueConstraint). Instead, use distinct folder_ids or distinct hour
    # buckets. We'll use distinct hour buckets within the last 24 hours.
    stats_rows = [
        WorkerStats(
            folder_id=folder.id,
            hour_bucket=now - timedelta(hours=2),
            emails_processed=10,
            errors_count=1,
        ),
        WorkerStats(
            folder_id=folder.id,
            hour_bucket=now - timedelta(hours=1),
            emails_processed=5,
            errors_count=0,
        ),
        WorkerStats(
            folder_id=folder.id,
            hour_bucket=now,
            emails_processed=3,
            errors_count=2,
        ),
    ]
    for row in stats_rows:
        db_session.add(row)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "hourly"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "hourly"

    buckets = data["buckets"]
    assert len(buckets) == 3

    # Buckets should be ordered by timestamp ascending
    total_emails = sum(b["emails_processed"] for b in buckets)
    total_errors = sum(b["errors_count"] for b in buckets)
    assert total_emails == 18
    assert total_errors == 3

    # Verify each bucket has the expected keys
    for b in buckets:
        assert "timestamp" in b
        assert "emails_processed" in b
        assert "errors_count" in b


@pytest.mark.asyncio
async def test_stats_hourly_empty(client, admin_token):
    """Hourly stats with no data should return an empty buckets list."""
    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "hourly"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "hourly"
    assert data["buckets"] == []


@pytest.mark.asyncio
async def test_stats_invalid_period(client, admin_token):
    """An invalid period value should return 400."""
    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "yearly"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 400
    assert "Invalid period" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_stats_requires_admin(client, user_token):
    """Non-admin users should receive 403 on the stats endpoint."""
    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "hourly"},
        headers=auth(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stats_unauthenticated(client):
    """Unauthenticated requests to the stats endpoint should be rejected."""
    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "hourly"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_stats_old_rows_cleaned_up(client, admin_token, db_session):
    """Rows older than 4 weeks should be deleted by the stats endpoint."""
    _user, _account, folder = await _seed_user_account_folder(db_session)

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    # One row within range, one older than 4 weeks
    db_session.add(
        WorkerStats(
            folder_id=folder.id,
            hour_bucket=now - timedelta(hours=1),
            emails_processed=5,
            errors_count=0,
        )
    )
    db_session.add(
        WorkerStats(
            folder_id=folder.id,
            hour_bucket=now - timedelta(weeks=5),
            emails_processed=99,
            errors_count=10,
        )
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/system/stats",
        params={"period": "hourly"},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()

    # Only the recent bucket should appear
    assert len(data["buckets"]) == 1
    assert data["buckets"][0]["emails_processed"] == 5
