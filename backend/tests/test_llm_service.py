import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.analysers.llm.models import LLMConfig
from app.core.encryption import encrypt_value
from app.modules.analysers.llm.service import analyze, AnalysisResult


def _make_llm_response(content: str):
    """Create a mock litellm response object."""
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
async def llm_config(db_session):
    """Insert an active LLM config into the test DB."""
    config = LLMConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        api_key_encrypted=encrypt_value("sk-test-key"),
        api_base_url="",
        is_active=True,
    )
    db_session.add(config)
    await db_session.commit()
    return config


@pytest.mark.asyncio
async def test_analyze_relevant_order_email(db_session, llm_config):
    """Test that a relevant order confirmation email is parsed correctly."""
    raw = {
        "is_relevant": True,
        "document_type": "order_confirmation",
        "order_number": "ORD-12345",
        "tracking_number": None,
        "carrier": None,
        "vendor_name": "Amazon",
        "vendor_domain": "amazon.com",
        "status": "ordered",
        "order_date": "2025-01-15",
        "estimated_delivery": "2025-01-20",
        "total_amount": 49.99,
        "currency": "USD",
        "items": [{"name": "USB-C Cable", "quantity": 2, "price": 12.99}],
    }

    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(json.dumps(raw))

        analysis, raw_resp = await analyze(
            {"subject": "Your order has been placed", "sender": "orders@amazon.com", "body": "Thank you for your order ORD-12345..."},
            db=db_session,
        )

    assert analysis is not None
    assert analysis.is_relevant is True
    assert analysis.order_number == "ORD-12345"
    assert analysis.vendor_name == "Amazon"
    assert analysis.vendor_domain == "amazon.com"
    assert analysis.status == "ordered"
    assert analysis.total_amount == 49.99
    assert len(analysis.items) == 1
    assert analysis.items[0].name == "USB-C Cable"
    assert analysis.items[0].quantity == 2
    assert raw_resp == raw


@pytest.mark.asyncio
async def test_analyze_irrelevant_email(db_session, llm_config):
    """Test that an irrelevant email returns is_relevant=False."""
    raw = {"is_relevant": False}

    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(json.dumps(raw))

        analysis, raw_resp = await analyze(
            {"subject": "Weekly newsletter", "sender": "news@example.com", "body": "Here are this week's top stories..."},
            db=db_session,
        )

    assert analysis is not None
    assert analysis.is_relevant is False
    assert analysis.order_number is None
    assert raw_resp == raw


@pytest.mark.asyncio
async def test_analyze_malformed_json_retry(db_session, llm_config):
    """Test that malformed JSON on first attempt triggers a retry."""
    good_response = {
        "is_relevant": True,
        "document_type": "shipment_confirmation",
        "order_number": "ORD-999",
        "tracking_number": "1Z999AA10123456784",
        "carrier": "UPS",
        "vendor_name": "Newegg",
        "vendor_domain": "newegg.com",
        "status": "shipped",
    }

    call_count = 0

    async def mock_completion(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_llm_response("Not valid JSON {{{")
        return _make_llm_response(json.dumps(good_response))

    with patch("app.modules.analysers.llm.service.litellm.acompletion", side_effect=mock_completion):
        analysis, raw_resp = await analyze(
            {"subject": "Your package has shipped", "sender": "shipping@newegg.com", "body": "Tracking: 1Z999AA10123456784"},
            db=db_session,
        )

    assert call_count == 2
    assert analysis is not None
    assert analysis.is_relevant is True
    assert analysis.tracking_number == "1Z999AA10123456784"
    assert analysis.carrier == "UPS"


@pytest.mark.asyncio
async def test_analyze_malformed_json_both_attempts_fail(db_session, llm_config):
    """Test that two consecutive malformed JSON responses return None."""
    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response("not json at all")

        analysis, raw_resp = await analyze(
            {"subject": "Order update", "sender": "orders@shop.com", "body": "Some body text"},
            db=db_session,
        )

    assert analysis is None
    assert "error" in raw_resp
    assert "Failed to parse" in raw_resp["error"]


@pytest.mark.asyncio
async def test_analyze_no_llm_config(db_session):
    """Test that missing LLM config returns None with error."""
    analysis, raw_resp = await analyze(
        {"subject": "Your order", "sender": "shop@example.com", "body": "Order details..."},
        db=db_session,
    )

    assert analysis is None
    assert raw_resp == {"error": "No LLM configured"}


@pytest.mark.asyncio
async def test_analyze_llm_api_error(db_session, llm_config):
    """Test that an LLM API exception returns None with error message."""
    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = Exception("API rate limit exceeded")

        analysis, raw_resp = await analyze(
            {"subject": "Your order", "sender": "shop@example.com", "body": "Order details..."},
            db=db_session,
        )

    assert analysis is None
    assert raw_resp == {"error": "API rate limit exceeded"}


@pytest.mark.asyncio
async def test_analyze_uses_custom_system_prompt(db_session, llm_config):
    """When config has a custom system_prompt, it should be used instead of default."""
    llm_config.system_prompt = "You are a custom analyser. Return JSON."
    await db_session.commit()

    raw = {"is_relevant": False}

    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(json.dumps(raw))

        await analyze(
            {"subject": "Test email", "sender": "test@example.com", "body": "Test body"},
            db=db_session,
        )

    # Verify the system message used the custom prompt
    call_args = mock_llm.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    system_msg = messages[0]
    assert system_msg["role"] == "system"
    assert system_msg["content"] == "You are a custom analyser. Return JSON."


@pytest.mark.asyncio
async def test_analyze_uses_default_prompt_when_none(db_session, llm_config):
    """When config.system_prompt is None, the hardcoded SYSTEM_PROMPT is used."""
    from app.modules.analysers.llm.service import SYSTEM_PROMPT

    assert llm_config.system_prompt is None

    raw = {"is_relevant": False}

    with patch("app.modules.analysers.llm.service.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = _make_llm_response(json.dumps(raw))

        await analyze(
            {"subject": "Test email", "sender": "test@example.com", "body": "Test body"},
            db=db_session,
        )

    call_args = mock_llm.call_args
    messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
    system_msg = messages[0]
    assert system_msg["role"] == "system"
    assert system_msg["content"] == SYSTEM_PROMPT
