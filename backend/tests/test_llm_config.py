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


LLM_CONFIG = {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "api_key": "sk-test-key-123",
    "api_base_url": "https://api.openai.com/v1",
}


@pytest.mark.asyncio
async def test_get_config_returns_null_when_none(client, admin_token):
    resp = await client.get("/api/v1/modules/analysers/llm/config", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_put_config_creates_new(client, admin_token):
    resp = await client.put("/api/v1/modules/analysers/llm/config", json=LLM_CONFIG, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["model_name"] == "gpt-4o-mini"
    assert data["api_base_url"] == "https://api.openai.com/v1"
    assert data["is_active"] is True
    assert data["has_api_key"] is True
    # API key should not be exposed
    assert "api_key" not in data
    assert "api_key_encrypted" not in data


@pytest.mark.asyncio
async def test_put_config_updates_existing(client, admin_token):
    await client.put("/api/v1/modules/analysers/llm/config", json=LLM_CONFIG, headers=auth(admin_token))
    updated = {
        "provider": "anthropic",
        "model_name": "claude-3-haiku",
    }
    resp = await client.put("/api/v1/modules/analysers/llm/config", json=updated, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "anthropic"
    assert data["model_name"] == "claude-3-haiku"
    assert data["api_base_url"] == "https://api.openai.com/v1"  # retained from first PUT
    # API key should still be present from first PUT
    assert data["has_api_key"] is True


@pytest.mark.asyncio
async def test_get_config_after_put(client, admin_token):
    await client.put("/api/v1/modules/analysers/llm/config", json=LLM_CONFIG, headers=auth(admin_token))
    resp = await client.get("/api/v1/modules/analysers/llm/config", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["model_name"] == "gpt-4o-mini"
    assert data["has_api_key"] is True


@pytest.mark.asyncio
async def test_non_admin_access_denied(client, user_token):
    resp = await client.get("/api/v1/modules/analysers/llm/config", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_put_config(client, user_token):
    resp = await client.put("/api/v1/modules/analysers/llm/config", json=LLM_CONFIG, headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_access_denied(client):
    resp = await client.get("/api/v1/modules/analysers/llm/config")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_config_includes_default_system_prompt(client, admin_token):
    """GET config response always includes default_system_prompt."""
    await client.put("/api/v1/modules/analysers/llm/config", json=LLM_CONFIG, headers=auth(admin_token))
    resp = await client.get("/api/v1/modules/analysers/llm/config", headers=auth(admin_token))
    data = resp.json()
    assert "default_system_prompt" in data
    assert len(data["default_system_prompt"]) > 50  # non-trivial prompt
    assert data["system_prompt"] is None  # no custom prompt set


@pytest.mark.asyncio
async def test_put_config_with_custom_system_prompt(client, admin_token):
    """PUT with system_prompt saves it; GET returns it back."""
    config_with_prompt = {**LLM_CONFIG, "system_prompt": "You are a custom analyser."}
    resp = await client.put("/api/v1/modules/analysers/llm/config", json=config_with_prompt, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["system_prompt"] == "You are a custom analyser."

    # Verify round-trip via GET
    resp = await client.get("/api/v1/modules/analysers/llm/config", headers=auth(admin_token))
    data = resp.json()
    assert data["system_prompt"] == "You are a custom analyser."
    assert "default_system_prompt" in data


@pytest.mark.asyncio
async def test_put_config_null_system_prompt_resets_to_default(client, admin_token):
    """PUT with system_prompt=null clears custom prompt (uses default)."""
    # First set a custom prompt
    config_with_prompt = {**LLM_CONFIG, "system_prompt": "Custom prompt"}
    await client.put("/api/v1/modules/analysers/llm/config", json=config_with_prompt, headers=auth(admin_token))

    # Then reset to default by sending null
    config_reset = {**LLM_CONFIG, "system_prompt": None}
    resp = await client.put("/api/v1/modules/analysers/llm/config", json=config_reset, headers=auth(admin_token))
    data = resp.json()
    assert data["system_prompt"] is None
