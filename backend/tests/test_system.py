import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.models.user import User
from app.models.module_config import ModuleConfig
from app.core.auth import hash_password
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


async def _enable_module(db_session, module_key: str):
    """Enable a module in the ModuleConfig table."""
    result = await db_session.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    config = result.scalar_one_or_none()
    if config:
        config.enabled = True
    else:
        db_session.add(ModuleConfig(module_key=module_key, enabled=True))
    await db_session.commit()


# ===========================================================================
# /api/v1/system/status tests
# ===========================================================================


@pytest.mark.asyncio
async def test_status_empty(client, admin_token):
    """With no module status hooks, response should have system and modules sections."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200

    data = resp.json()

    # System section
    assert "system" in data
    q = data["system"]["queue"]
    assert q["queued"] == 0
    assert q["processing"] == 0
    assert q["completed"] == 0
    assert q["failed"] == 0
    assert "scheduled_jobs" in data["system"]

    # Modules section
    assert "modules" in data
    assert isinstance(data["modules"], list)


@pytest.mark.asyncio
async def test_status_modules_have_metadata(client, admin_token):
    """Each module entry should have key, name, type, version, description, enabled, configured."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200

    data = resp.json()
    for mod in data["modules"]:
        assert "key" in mod
        assert "name" in mod
        assert "type" in mod
        assert "version" in mod
        assert "description" in mod
        assert "enabled" in mod
        assert "configured" in mod
        assert "status" in mod


@pytest.mark.asyncio
async def test_status_email_user_with_folders(client, admin_token, db_session):
    """The email-user module status should include user/account/folder hierarchy."""
    user, account, folder = await _seed_user_account_folder(db_session)

    # Enable the email-user module so the status hook is invoked
    await _enable_module(db_session, "email-user")

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
        patch(
            "app.modules.providers.email_user.service._running_tasks",
            {folder.id: mock_task},
        ),
        patch(
            "app.modules.providers.email_user.service._worker_state",
            {folder.id: state},
        ),
    ):
        resp = await client.get("/api/v1/system/status", headers=auth(admin_token))

    assert resp.status_code == 200
    data = resp.json()

    # Find email-user module
    email_user_mod = next((m for m in data["modules"] if m["key"] == "email-user"), None)
    assert email_user_mod is not None
    assert email_user_mod["status"] is not None

    status = email_user_mod["status"]
    assert status["total_folders"] == 1
    assert status["running"] == 1
    assert status["errors"] == 0

    assert len(status["users"]) >= 1
    u = next(u for u in status["users"] if u["user_id"] == user.id)
    assert u["username"] == user.username

    assert len(u["accounts"]) == 1
    a = u["accounts"][0]
    assert a["account_id"] == account.id
    assert a["account_name"] == account.name

    assert len(a["folders"]) == 1
    f = a["folders"][0]
    assert f["folder_id"] == folder.id
    assert f["folder_path"] == "INBOX"
    assert f["running"] is True
    assert f["mode"] == "processing"
    assert f["queue_total"] == 5
    assert f["queue_position"] == 2
    assert f["current_email_subject"] == "Your order shipped"


@pytest.mark.asyncio
async def test_status_has_queue_section(client, admin_token):
    """System status should include a queue section with status counts."""
    resp = await client.get("/api/v1/system/status", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()

    q = data["system"]["queue"]
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
    assert "scheduled_jobs" in data["system"]
    assert isinstance(data["system"]["scheduled_jobs"], list)


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
