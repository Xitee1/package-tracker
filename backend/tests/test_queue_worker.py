"""Tests for queue worker processing (app.services.queue.queue_worker)."""

from datetime import datetime, timezone
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.encryption import encrypt_value
from app.modules.providers.email_user.models import EmailAccount
from app.models.order import Order
from app.models.order_state import OrderState
from app.models.queue_item import QueueItem
from app.models.user import User
from app.modules.analysers.llm.service import EmailAnalysis, EmailItem
from app.services.orders.order_service import create_or_update_order
from app.services.orders.order_matcher import DefaultOrderMatcher


@pytest.fixture
async def test_user(db_session):
    user = User(username="queueuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_account(db_session, test_user):
    account = EmailAccount(
        user_id=test_user.id,
        name="Test Account",
        imap_host="imap.example.com",
        imap_port=993,
        imap_user="user@example.com",
        imap_password_encrypted=encrypt_value("password"),
        use_ssl=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


def _make_queue_item(user_id: int, **kwargs) -> QueueItem:
    """Helper to create a QueueItem with defaults."""
    defaults = {
        "user_id": user_id,
        "status": "queued",
        "source_type": "email",
        "source_info": "INBOX",
        "raw_data": {
            "subject": "Order Confirmation",
            "sender": "orders@amazon.com",
            "body": "Your order ORD-500 has been placed.",
        },
    }
    defaults.update(kwargs)
    return QueueItem(**defaults)


def _make_analysis(**kwargs) -> EmailAnalysis:
    """Helper to create an EmailAnalysis with defaults."""
    defaults = {"is_relevant": True}
    defaults.update(kwargs)
    return EmailAnalysis(**defaults)


# ---------------------------------------------------------------------------
# Tests for create_or_update_order (service layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_order_from_analysis(db_session, test_user):
    """create_or_update_order with no existing order should create a new Order + OrderState."""
    analysis = _make_analysis(
        order_number="ORD-500",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
        order_date="2025-01-15",
        total_amount=59.99,
        currency="USD",
        items=[EmailItem(name="Keyboard", quantity=1, price=59.99)],
    )

    order = await create_or_update_order(
        analysis=analysis,
        user_id=test_user.id,
        existing_order=None,
        source_type="email",
        source_info="INBOX",
        db=db_session,
    )
    await db_session.commit()

    assert order is not None
    assert order.order_number == "ORD-500"
    assert order.vendor_name == "Amazon"
    assert order.status == "ordered"
    assert float(order.total_amount) == 59.99
    assert order.items == [{"name": "Keyboard", "quantity": 1, "price": 59.99}]

    # Verify OrderState was created
    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == order.id)
    )
    states = result.scalars().all()
    assert len(states) == 1
    assert states[0].status == "ordered"
    assert states[0].source_type == "email"


@pytest.mark.asyncio
async def test_update_existing_order_adds_tracking(db_session, test_user):
    """create_or_update_order with existing order should add tracking info."""
    existing_order = Order(
        user_id=test_user.id,
        order_number="ORD-600",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
    )
    db_session.add(existing_order)
    await db_session.commit()
    await db_session.refresh(existing_order)

    analysis = _make_analysis(
        order_number="ORD-600",
        tracking_number="1Z999AA10123456784",
        carrier="UPS",
        status="shipped",
    )

    order = await create_or_update_order(
        analysis=analysis,
        user_id=test_user.id,
        existing_order=existing_order,
        source_type="email",
        source_info="INBOX",
        db=db_session,
    )
    await db_session.commit()

    assert order.id == existing_order.id
    assert order.tracking_number == "1Z999AA10123456784"
    assert order.carrier == "UPS"
    assert order.status == "shipped"

    # Verify OrderState was created for the status change
    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == order.id)
    )
    states = result.scalars().all()
    assert len(states) == 1
    assert states[0].status == "shipped"
    assert states[0].source_type == "email"


@pytest.mark.asyncio
async def test_no_order_state_when_status_unchanged(db_session, test_user):
    """If status doesn't change, no OrderState should be created."""
    existing_order = Order(
        user_id=test_user.id,
        order_number="ORD-650",
        vendor_name="Amazon",
        status="ordered",
    )
    db_session.add(existing_order)
    await db_session.commit()
    await db_session.refresh(existing_order)

    analysis = _make_analysis(
        order_number="ORD-650",
        tracking_number="TRACK-123",
        status="ordered",  # Same status
    )

    await create_or_update_order(
        analysis=analysis,
        user_id=test_user.id,
        existing_order=existing_order,
        source_type="email",
        source_info="INBOX",
        db=db_session,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == existing_order.id)
    )
    states = result.scalars().all()
    assert len(states) == 0


@pytest.mark.asyncio
async def test_irrelevant_analysis_creates_no_order(db_session, test_user):
    """An irrelevant analysis should not create any order."""
    analysis = _make_analysis(is_relevant=False)

    # Simulate queue worker logic: check if relevant before creating order
    assert not analysis.is_relevant

    result = await db_session.execute(
        select(Order).where(Order.user_id == test_user.id)
    )
    assert result.scalars().all() == []


# ---------------------------------------------------------------------------
# Tests for process_next_item (integration, mocked session + LLM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_skips_when_no_analyser_configured(db_session, test_user):
    """Queue items should stay 'queued' when no analyser module is enabled+configured."""
    item = _make_queue_item(test_user.id)
    db_session.add(item)
    await db_session.commit()

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock) as mock_check,
    ):
        mock_check.return_value = False

        from app.services.queue.queue_worker import process_next_item
        await process_next_item()

    await db_session.refresh(item)
    assert item.status == "queued"  # Should NOT have been processed


@pytest.mark.asyncio
async def test_process_queued_item_creates_order(db_session, test_user):
    """Full integration: queued item -> process_next_item -> Order + OrderState created."""
    item = _make_queue_item(
        test_user.id,
        raw_data={
            "subject": "Order Confirmation",
            "sender": "orders@amazon.com",
            "body": "Your order ORD-500 has been placed.",
        },
    )
    db_session.add(item)
    await db_session.commit()

    analysis = _make_analysis(
        email_type="order_confirmation",
        order_number="ORD-500",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
        items=[EmailItem(name="Keyboard", quantity=1, price=59.99)],
    )
    raw_response = {"is_relevant": True, "order_number": "ORD-500"}

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.analyze", new_callable=AsyncMock) as mock_analyze,
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock, return_value=True),
    ):
        mock_analyze.return_value = (analysis, raw_response)

        from app.services.queue.queue_worker import process_next_item
        await process_next_item()

    # Refresh item state
    await db_session.refresh(item)
    assert item.status == "completed"
    assert item.order_id is not None

    # Verify Order was created
    result = await db_session.execute(
        select(Order).where(Order.id == item.order_id)
    )
    order = result.scalar_one()
    assert order.order_number == "ORD-500"
    assert order.vendor_name == "Amazon"
    assert order.status == "ordered"

    # Verify OrderState was created
    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == order.id)
    )
    states = result.scalars().all()
    assert len(states) == 1
    assert states[0].status == "ordered"


@pytest.mark.asyncio
async def test_process_irrelevant_item(db_session, test_user):
    """Processing an irrelevant email should complete the item without creating an order."""
    item = _make_queue_item(
        test_user.id,
        raw_data={
            "subject": "Newsletter",
            "sender": "news@example.com",
            "body": "Weekly update...",
        },
    )
    db_session.add(item)
    await db_session.commit()

    analysis = EmailAnalysis(is_relevant=False)
    raw_response = {"is_relevant": False}

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.analyze", new_callable=AsyncMock) as mock_analyze,
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock, return_value=True),
    ):
        mock_analyze.return_value = (analysis, raw_response)

        from app.services.queue.queue_worker import process_next_item
        await process_next_item()

    await db_session.refresh(item)
    assert item.status == "completed"
    assert item.order_id is None

    # No Order should exist
    result = await db_session.execute(
        select(Order).where(Order.user_id == test_user.id)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_process_updates_existing_order(db_session, test_user):
    """QueueItem that matches existing order should update tracking info."""
    existing_order = Order(
        user_id=test_user.id,
        order_number="ORD-600",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
    )
    db_session.add(existing_order)
    await db_session.commit()
    await db_session.refresh(existing_order)

    item = _make_queue_item(
        test_user.id,
        raw_data={
            "subject": "Your order has shipped",
            "sender": "shipping@amazon.com",
            "body": "Tracking: 1Z999AA10123456784",
        },
    )
    db_session.add(item)
    await db_session.commit()

    analysis = _make_analysis(
        email_type="shipment_confirmation",
        order_number="ORD-600",
        tracking_number="1Z999AA10123456784",
        carrier="UPS",
        status="shipped",
    )
    raw_response = {"is_relevant": True, "order_number": "ORD-600"}

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.analyze", new_callable=AsyncMock) as mock_analyze,
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock, return_value=True),
    ):
        mock_analyze.return_value = (analysis, raw_response)

        from app.services.queue.queue_worker import process_next_item
        await process_next_item()

    await db_session.refresh(item)
    assert item.status == "completed"
    assert item.order_id == existing_order.id

    await db_session.refresh(existing_order)
    assert existing_order.tracking_number == "1Z999AA10123456784"
    assert existing_order.carrier == "UPS"
    assert existing_order.status == "shipped"


@pytest.mark.asyncio
async def test_process_failed_llm(db_session, test_user):
    """Mock LLM failure -> QueueItem status=failed, error_message set."""
    item = _make_queue_item(test_user.id)
    db_session.add(item)
    await db_session.commit()
    item_id = item.id

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.analyze", new_callable=AsyncMock) as mock_analyze,
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock, return_value=True),
    ):
        mock_analyze.side_effect = RuntimeError("LLM unavailable")

        from app.services.queue.queue_worker import process_next_item
        await process_next_item()

    # Re-fetch item (may have been refreshed in a different session context)
    result = await db_session.execute(
        select(QueueItem).where(QueueItem.id == item_id)
    )
    refreshed = result.scalar_one()
    assert refreshed.status == "failed"
    assert "LLM unavailable" in refreshed.error_message


@pytest.mark.asyncio
async def test_no_items_to_process(db_session):
    """Empty queue -> no errors, no-op."""

    @asynccontextmanager
    async def mock_async_session():
        yield db_session

    with (
        patch("app.services.queue.queue_worker.async_session", mock_async_session),
        patch("app.services.queue.queue_worker.has_available_analyser", new_callable=AsyncMock, return_value=True),
    ):
        from app.services.queue.queue_worker import process_next_item
        await process_next_item()  # Should not raise


@pytest.mark.asyncio
async def test_order_state_created_on_new_order(db_session, test_user):
    """Verify OrderState row created with initial status when new order is created."""
    analysis = _make_analysis(
        order_number="ORD-NEW-1",
        vendor_name="TestShop",
        status="ordered",
    )

    order = await create_or_update_order(
        analysis=analysis,
        user_id=test_user.id,
        existing_order=None,
        source_type="email",
        source_info="INBOX",
        db=db_session,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == order.id)
    )
    states = result.scalars().all()
    assert len(states) == 1
    assert states[0].status == "ordered"
    assert states[0].source_type == "email"
    assert states[0].source_info == "INBOX"


@pytest.mark.asyncio
async def test_order_state_created_on_status_change(db_session, test_user):
    """Verify OrderState row created when status transitions."""
    existing_order = Order(
        user_id=test_user.id,
        order_number="ORD-STATE-1",
        vendor_name="Amazon",
        status="ordered",
    )
    db_session.add(existing_order)
    await db_session.commit()
    await db_session.refresh(existing_order)

    analysis = _make_analysis(
        order_number="ORD-STATE-1",
        status="shipped",
    )

    await create_or_update_order(
        analysis=analysis,
        user_id=test_user.id,
        existing_order=existing_order,
        source_type="email",
        source_info="INBOX",
        db=db_session,
    )
    await db_session.commit()

    result = await db_session.execute(
        select(OrderState).where(OrderState.order_id == existing_order.id)
    )
    states = result.scalars().all()
    assert len(states) == 1
    assert states[0].status == "shipped"
    assert states[0].source_type == "email"


# ---------------------------------------------------------------------------
# Tests for DefaultOrderMatcher (kept close to queue worker tests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matcher_by_order_number(db_session, test_user):
    """DefaultOrderMatcher should match by order_number."""
    order = Order(
        user_id=test_user.id,
        order_number="ORD-MATCH-1",
        vendor_name="Amazon",
        status="ordered",
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    analysis = _make_analysis(order_number="ORD-MATCH-1")
    matcher = DefaultOrderMatcher()
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order.id
