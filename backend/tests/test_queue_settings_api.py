"""Tests for queue settings API endpoints (app.api.queue_settings)."""

import pytest


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_token(client):
    resp = await client.post(
        "/api/v1/auth/setup", json={"username": "admin", "password": "pass123"}
    )
    return resp.json()["access_token"]


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


# --- Get Queue Settings ---


@pytest.mark.asyncio
async def test_get_queue_settings(client, admin_token):
    """Admin can get queue settings."""
    resp = await client.get("/api/v1/settings/queue/", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "max_age_days" in data
    assert "max_per_user" in data
    # Default values
    assert data["max_age_days"] == 7
    assert data["max_per_user"] == 5000


@pytest.mark.asyncio
async def test_get_queue_settings_non_admin(client, user_token):
    """Non-admin users cannot get queue settings."""
    resp = await client.get("/api/v1/settings/queue/", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_queue_settings_unauthenticated(client):
    """Unauthenticated users cannot get queue settings."""
    resp = await client.get("/api/v1/settings/queue/")
    assert resp.status_code in (401, 403)


# --- Update Queue Settings ---


@pytest.mark.asyncio
async def test_update_queue_settings(client, admin_token):
    """Admin can update queue settings."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 14, "max_per_user": 10000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_age_days"] == 14
    assert data["max_per_user"] == 10000

    # Verify persistence
    resp = await client.get("/api/v1/settings/queue/", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_age_days"] == 14
    assert data["max_per_user"] == 10000


@pytest.mark.asyncio
async def test_update_queue_settings_non_admin(client, user_token):
    """Non-admin users cannot update queue settings."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 30, "max_per_user": 1000},
        headers=auth(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_queue_settings_unauthenticated(client):
    """Unauthenticated users cannot update queue settings."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 30, "max_per_user": 1000},
    )
    assert resp.status_code in (401, 403)


# --- Validation Tests ---


@pytest.mark.asyncio
async def test_update_queue_settings_zero_max_age_days(client, admin_token):
    """Zero max_age_days should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 0, "max_per_user": 5000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_negative_max_age_days(client, admin_token):
    """Negative max_age_days should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": -7, "max_per_user": 5000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_zero_max_per_user(client, admin_token):
    """Zero max_per_user should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 7, "max_per_user": 0},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_negative_max_per_user(client, admin_token):
    """Negative max_per_user should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 7, "max_per_user": -1000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_both_zero(client, admin_token):
    """Both fields being zero should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 0, "max_per_user": 0},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_both_negative(client, admin_token):
    """Both fields being negative should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": -7, "max_per_user": -1000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_queue_settings_minimum_valid_values(client, admin_token):
    """Minimum valid values (1) should be accepted."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 1, "max_per_user": 1},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_age_days"] == 1
    assert data["max_per_user"] == 1


@pytest.mark.asyncio
async def test_update_queue_settings_missing_fields(client, admin_token):
    """Missing required fields should be rejected."""
    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_age_days": 7},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422

    resp = await client.put(
        "/api/v1/settings/queue/",
        json={"max_per_user": 5000},
        headers=auth(admin_token),
    )
    assert resp.status_code == 422
