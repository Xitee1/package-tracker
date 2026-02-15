"""Tests for queue settings API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_queue_settings_creates_defaults(client: AsyncClient, admin_token):
    """GET /settings/queue/ returns defaults if not configured."""
    response = await client.get("/api/v1/settings/queue/", headers=auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert "max_age_days" in data
    assert "max_per_user" in data


@pytest.mark.asyncio
async def test_patch_queue_settings_full_update(client: AsyncClient, admin_token):
    """PATCH with all fields updates all settings."""
    response = await client.patch(
        "/api/v1/settings/queue/",
        headers=auth(admin_token),
        json={"max_age_days": 14, "max_per_user": 2000}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_age_days"] == 14
    assert data["max_per_user"] == 2000


@pytest.mark.asyncio
async def test_patch_queue_settings_partial_update_max_age(client: AsyncClient, admin_token):
    """PATCH with only max_age_days updates only that field."""
    # First set both values
    await client.patch(
        "/api/v1/settings/queue/",
        headers=auth(admin_token),
        json={"max_age_days": 10, "max_per_user": 1500}
    )
    
    # Then update only max_age_days
    response = await client.patch(
        "/api/v1/settings/queue/",
        headers=auth(admin_token),
        json={"max_age_days": 30}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_age_days"] == 30
    assert data["max_per_user"] == 1500  # Should remain unchanged


@pytest.mark.asyncio
async def test_patch_queue_settings_partial_update_max_per_user(client: AsyncClient, admin_token):
    """PATCH with only max_per_user updates only that field."""
    # First set both values
    await client.patch(
        "/api/v1/settings/queue/",
        headers=auth(admin_token),
        json={"max_age_days": 20, "max_per_user": 3000}
    )
    
    # Then update only max_per_user
    response = await client.patch(
        "/api/v1/settings/queue/",
        headers=auth(admin_token),
        json={"max_per_user": 500}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["max_age_days"] == 20  # Should remain unchanged
    assert data["max_per_user"] == 500


@pytest.mark.asyncio
async def test_patch_queue_settings_requires_admin(client: AsyncClient):
    """Unauthenticated users cannot update queue settings."""
    response = await client.patch(
        "/api/v1/settings/queue/",
        json={"max_age_days": 10}
    )
    assert response.status_code == 403
