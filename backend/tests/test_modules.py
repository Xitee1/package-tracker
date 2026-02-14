import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_modules_as_user(client, user_token):
    resp = await client.get("/api/v1/modules", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    keys = {m["module_key"] for m in data}
    assert "llm" in keys
    assert "email-user" in keys
    assert "email-global" in keys
    # Verify new response fields are present
    for m in data:
        assert "name" in m
        assert "type" in m
        assert "description" in m


@pytest.mark.asyncio
async def test_list_modules_as_admin(client, admin_token):
    resp = await client.get("/api/v1/modules", headers=auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_modules_unauthenticated(client):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_module_as_admin(client, admin_token):
    resp = await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    # Verify persistence
    resp = await client.get("/api/v1/modules", headers=auth(admin_token))
    modules = {m["module_key"]: m["enabled"] for m in resp.json()}
    assert modules["email-global"] is True


@pytest.mark.asyncio
async def test_update_module_as_user_denied(client, user_token):
    resp = await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_unknown_module(client, admin_token):
    resp = await client.put(
        "/api/v1/modules/nonexistent",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reorder_module_priority(client, admin_token):
    """PATCH /modules/priority should update priority values."""
    resp = await client.patch(
        "/api/v1/modules/priority",
        json={"module_keys": ["email-global", "llm", "email-user"]},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200

    # Verify ordering
    resp = await client.get("/api/v1/modules", headers=auth(admin_token))
    modules = resp.json()
    keys_in_order = [m["module_key"] for m in modules]
    assert keys_in_order == ["email-global", "llm", "email-user"]


@pytest.mark.asyncio
async def test_reorder_module_priority_requires_admin(client, user_token):
    resp = await client.patch(
        "/api/v1/modules/priority",
        json={"module_keys": ["llm", "email-user", "email-global"]},
        headers=auth(user_token),
    )
    assert resp.status_code == 403
