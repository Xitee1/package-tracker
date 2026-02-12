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
