import hashlib
import pytest
from datetime import datetime, timedelta, timezone

from app.models.api_key import ApiKey


async def _setup_user_and_key(client, db_session):
    """Create admin user via setup endpoint, then insert an API key directly."""
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    raw_key = "pt_abcdef1234567890abcdef1234567890"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        user_id=1,
        name="test-key",
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        expires_at=datetime.now(timezone.utc) + timedelta(days=3650),
    )
    db_session.add(api_key)
    await db_session.commit()
    return token, raw_key


@pytest.mark.asyncio
async def test_api_key_authenticates_orders(client, db_session):
    _, raw_key = await _setup_user_and_key(client, db_session)
    resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_expired_api_key_rejected(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    raw_key = "pt_expired01234567890expired01234"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    api_key = ApiKey(
        user_id=1,
        name="expired-key",
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(api_key)
    await db_session.commit()
    resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_key_rejected_on_users_endpoint(client, db_session):
    _, raw_key = await _setup_user_and_key(client, db_session)
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_jwt_still_works_on_orders(client, db_session):
    token, _ = await _setup_user_and_key(client, db_session)
    resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_api_key(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    resp = await client.post(
        "/api/v1/api-keys",
        json={"name": "my-key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my-key"
    assert data["key"].startswith("pt_")
    assert "key_prefix" in data


@pytest.mark.asyncio
async def test_list_api_keys(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    await client.post("/api/v1/api-keys", json={"name": "key-1"}, headers={"Authorization": f"Bearer {token}"})
    await client.post("/api/v1/api-keys", json={"name": "key-2"}, headers={"Authorization": f"Bearer {token}"})
    resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert "key" not in resp.json()[0]  # full key must not appear in list


@pytest.mark.asyncio
async def test_delete_api_key(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    create = await client.post("/api/v1/api-keys", json={"name": "to-delete"}, headers={"Authorization": f"Bearer {token}"})
    key_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
    list_resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {token}"})
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_cannot_delete_other_users_key(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    admin_token = setup.json()["access_token"]
    await client.post(
        "/api/v1/users",
        json={"username": "user2", "password": "pass123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user2_login = await client.post("/api/v1/auth/login", json={"username": "user2", "password": "pass123"})
    user2_token = user2_login.json()["access_token"]
    create = await client.post("/api/v1/api-keys", json={"name": "u2-key"}, headers={"Authorization": f"Bearer {user2_token}"})
    key_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/api-keys/{key_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_max_25_keys(client, db_session):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    for i in range(25):
        resp = await client.post("/api/v1/api-keys", json={"name": f"key-{i}"}, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
    resp = await client.post("/api/v1/api-keys", json={"name": "key-26"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_api_key_rejected_on_api_keys_endpoint(client, db_session):
    _, raw_key = await _setup_user_and_key(client, db_session)
    resp = await client.get("/api/v1/api-keys", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp.status_code == 403
