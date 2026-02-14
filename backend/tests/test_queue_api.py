"""Tests for queue API endpoints (app.api.queue)."""

import pytest

from app.core.encryption import encrypt_value
from app.models.email_account import EmailAccount
from app.models.queue_item import QueueItem


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "pass123"}
    )
    return resp.json()["access_token"]


@pytest.fixture
async def admin_user(client, admin_token):
    resp = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    return resp.json()


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "user1", "password": "pass"}
    )
    return login.json()["access_token"]


@pytest.fixture
async def user2_id(client, admin_token):
    """Create a second user and return their id."""
    await client.post(
        "/api/v1/users",
        json={"username": "user2", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "user2", "password": "pass"}
    )
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    return resp.json()["id"]


@pytest.fixture
async def queue_items(db_session, admin_user):
    """Create 5 queue items for the admin user."""
    items = []
    for i in range(5):
        status = ["queued", "queued", "completed", "failed", "completed"][i]
        item = QueueItem(
            user_id=admin_user["id"],
            status=status,
            source_type="email",
            source_info="INBOX",
            raw_data={
                "subject": f"Order #{i}",
                "sender": f"shop{i}@example.com",
                "body": f"Order body {i}",
            },
        )
        if status == "failed":
            item.error_message = "LLM error"
        db_session.add(item)
        items.append(item)

    await db_session.commit()
    for item in items:
        await db_session.refresh(item)

    return items


# --- List Queue Items ---


@pytest.mark.asyncio
async def test_list_queue_items(client, admin_token, queue_items):
    resp = await client.get("/api/v1/queue", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5
    assert data["page"] == 1
    assert data["per_page"] == 50


@pytest.mark.asyncio
async def test_list_queue_items_filter_status(client, admin_token, queue_items):
    resp = await client.get(
        "/api/v1/queue?status=queued", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(item["status"] == "queued" for item in data["items"])


@pytest.mark.asyncio
async def test_list_queue_items_pagination(client, admin_token, queue_items):
    resp = await client.get(
        "/api/v1/queue?page=1&per_page=2", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2


# --- Get Queue Item Detail ---


@pytest.mark.asyncio
async def test_get_queue_item_detail(client, admin_token, queue_items):
    item = queue_items[0]
    resp = await client.get(
        f"/api/v1/queue/{item.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == item.id
    assert data["status"] == item.status
    assert data["source_type"] == "email"
    assert data["raw_data"]["subject"] == "Order #0"


@pytest.mark.asyncio
async def test_get_queue_item_not_found(client, admin_token):
    resp = await client.get("/api/v1/queue/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Delete Queue Item ---


@pytest.mark.asyncio
async def test_delete_queue_item(client, admin_token, queue_items):
    item = queue_items[0]
    resp = await client.delete(
        f"/api/v1/queue/{item.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get(
        f"/api/v1/queue/{item.id}", headers=auth(admin_token)
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_queue_item_not_found(client, admin_token):
    resp = await client.delete("/api/v1/queue/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Retry Queue Item ---


@pytest.mark.asyncio
async def test_retry_queue_item(client, admin_token, queue_items):
    failed_item = queue_items[3]  # status=failed
    resp = await client.post(
        f"/api/v1/queue/{failed_item.id}/retry", headers=auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["cloned_from_id"] == failed_item.id
    assert data["error_message"] is None
    assert data["raw_data"] == failed_item.raw_data


# --- Queue Stats ---


@pytest.mark.asyncio
async def test_queue_stats(client, admin_token, queue_items):
    resp = await client.get("/api/v1/queue/stats", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] == 2
    assert data["completed"] == 2
    assert data["failed"] == 1
    assert data["processing"] == 0


@pytest.mark.asyncio
async def test_queue_stats_empty(client, admin_token):
    resp = await client.get("/api/v1/queue/stats", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["queued"] == 0
    assert data["completed"] == 0
    assert data["failed"] == 0
    assert data["processing"] == 0


# --- User Isolation ---


@pytest.mark.asyncio
async def test_user_isolation(client, db_session, admin_token, user_token, queue_items):
    """Users should only see their own queue items."""
    item = queue_items[0]

    # user1 should see empty list
    resp = await client.get("/api/v1/queue", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

    # user1 cannot access admin's item by ID
    resp = await client.get(
        f"/api/v1/queue/{item.id}", headers=auth(user_token)
    )
    assert resp.status_code == 404

    # user1 cannot delete admin's item
    resp = await client.delete(
        f"/api/v1/queue/{item.id}", headers=auth(user_token)
    )
    assert resp.status_code == 404

    # user1 cannot retry admin's item
    resp = await client.post(
        f"/api/v1/queue/{item.id}/retry", headers=auth(user_token)
    )
    assert resp.status_code == 404


# --- Unauthenticated ---


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    resp = await client.get("/api/v1/queue")
    assert resp.status_code in (401, 403)
