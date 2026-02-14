from datetime import datetime, timezone
from decimal import Decimal

import pytest
from unittest.mock import patch, AsyncMock

from sqlalchemy import select

from app.models.email_account import EmailAccount
from app.models.email_scan import EmailScan
from app.models.user import User
from app.models.order import Order, OrderEvent
from app.services.llm_service import EmailAnalysis, EmailItem
from app.services.email_processor import process_email
from app.core.auth import hash_password
from app.core.encryption import encrypt_value


@pytest.fixture
async def test_user(db_session):
    user = User(username="procuser", password_hash=hash_password("pass"), is_admin=False)
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


def _make_analysis(**kwargs) -> EmailAnalysis:
    """Helper to create an EmailAnalysis with defaults."""
    defaults = {"is_relevant": True}
    defaults.update(kwargs)
    return EmailAnalysis(**defaults)


@pytest.mark.asyncio
async def test_new_order_creation(db_session, test_user, test_account):
    """A relevant email with no matching order should create a new order."""
    analysis = _make_analysis(
        email_type="order_confirmation",
        order_number="ORD-500",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
        order_date="2025-01-15",
        total_amount=59.99,
        currency="USD",
        items=[EmailItem(name="Keyboard", quantity=1, price=59.99)],
    )
    raw_response = {"is_relevant": True, "order_number": "ORD-500"}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Order Confirmation",
            sender="orders@amazon.com",
            body="Your order ORD-500 has been placed.",
            message_id="<msg-001@amazon.com>",
            email_uid=100,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is not None
    assert order.order_number == "ORD-500"
    assert order.vendor_name == "Amazon"
    assert order.status == "ordered"
    assert order.total_amount == Decimal("59.99")
    assert order.items == [{"name": "Keyboard", "quantity": 1, "price": 59.99}]

    # Verify event was created
    result = await db_session.execute(
        select(OrderEvent).where(OrderEvent.order_id == order.id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "order_confirmed"
    assert events[0].old_status is None
    assert events[0].new_status == "ordered"
    assert events[0].source_email_message_id == "<msg-001@amazon.com>"


@pytest.mark.asyncio
async def test_order_update_adds_tracking(db_session, test_user, test_account):
    """A shipment email for an existing order should update tracking info."""
    # Create an existing order
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
        email_type="shipment_confirmation",
        order_number="ORD-600",
        tracking_number="1Z999AA10123456784",
        carrier="UPS",
        status="shipped",
    )
    raw_response = {"is_relevant": True, "order_number": "ORD-600"}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Your order has shipped",
            sender="shipping@amazon.com",
            body="Tracking: 1Z999AA10123456784",
            message_id="<msg-002@amazon.com>",
            email_uid=101,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is not None
    assert order.id == existing_order.id
    assert order.tracking_number == "1Z999AA10123456784"
    assert order.carrier == "UPS"
    assert order.status == "shipped"

    # Verify event
    result = await db_session.execute(
        select(OrderEvent).where(OrderEvent.order_id == order.id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "shipment_added"
    assert events[0].old_status == "ordered"
    assert events[0].new_status == "shipped"


@pytest.mark.asyncio
async def test_dedup_same_message_id(db_session, test_user, test_account):
    """Processing the same message_id twice should return None the second time."""
    analysis = _make_analysis(
        order_number="ORD-700",
        vendor_name="Shop",
        status="ordered",
    )
    raw_response = {"is_relevant": True}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        # First processing
        order1 = await process_email(
            subject="Order",
            sender="shop@example.com",
            body="Order details",
            message_id="<msg-dedup@example.com>",
            email_uid=200,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order1 is not None

    # Second processing with same message_id - should be deduped (no mock needed; it should return before calling analyze)
    order2 = await process_email(
        subject="Order",
        sender="shop@example.com",
        body="Order details",
        message_id="<msg-dedup@example.com>",
        email_uid=200,
        folder_path="INBOX",
        account_id=test_account.id,
        user_id=test_user.id,
        db=db_session,
    )

    assert order2 is None


@pytest.mark.asyncio
async def test_irrelevant_email_returns_none(db_session, test_user, test_account):
    """An irrelevant email should return None without creating any order."""
    analysis = EmailAnalysis(is_relevant=False)
    raw_response = {"is_relevant": False}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Newsletter",
            sender="news@example.com",
            body="Weekly update...",
            message_id="<msg-irrel@example.com>",
            email_uid=300,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is None

    # Verify no orders were created
    result = await db_session.execute(
        select(Order).where(Order.user_id == test_user.id)
    )
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_llm_failure_returns_none(db_session, test_user, test_account):
    """If analyze_email returns None (LLM failure), process_email returns None."""
    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (None, {"error": "LLM unavailable"})

        order = await process_email(
            subject="Order",
            sender="shop@example.com",
            body="Order...",
            message_id="<msg-fail@example.com>",
            email_uid=400,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is None


@pytest.mark.asyncio
async def test_status_update_existing_order(db_session, test_user, test_account):
    """An update email for an order that already has tracking should log status_update."""
    existing_order = Order(
        user_id=test_user.id,
        order_number="ORD-800",
        tracking_number="EXISTING-TRACK",
        carrier="FedEx",
        vendor_name="BestBuy",
        vendor_domain="bestbuy.com",
        status="shipped",
    )
    db_session.add(existing_order)
    await db_session.commit()
    await db_session.refresh(existing_order)

    analysis = _make_analysis(
        email_type="shipment_update",
        order_number="ORD-800",
        status="out_for_delivery",
    )
    raw_response = {"is_relevant": True}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Your package is out for delivery",
            sender="tracking@bestbuy.com",
            body="Delivery today",
            message_id="<msg-status@bestbuy.com>",
            email_uid=500,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is not None
    assert order.id == existing_order.id
    assert order.status == "out_for_delivery"
    # Tracking should remain unchanged
    assert order.tracking_number == "EXISTING-TRACK"
    assert order.carrier == "FedEx"

    result = await db_session.execute(
        select(OrderEvent).where(OrderEvent.order_id == order.id)
    )
    events = result.scalars().all()
    assert len(events) == 1
    assert events[0].event_type == "status_update"
    assert events[0].old_status == "shipped"
    assert events[0].new_status == "out_for_delivery"


# --- New EmailScan-specific tests ---


@pytest.mark.asyncio
async def test_creates_email_scan_for_relevant_email(db_session, test_user, test_account):
    """Verify EmailScan is created with correct fields and order_id is set for relevant emails."""
    analysis = _make_analysis(
        email_type="order_confirmation",
        order_number="ORD-SCAN-1",
        vendor_name="TestShop",
        vendor_domain="testshop.com",
        status="ordered",
    )
    raw_response = {"is_relevant": True, "order_number": "ORD-SCAN-1"}
    email_dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Your order is confirmed",
            sender="orders@testshop.com",
            body="Order ORD-SCAN-1 confirmed.",
            message_id="<msg-scan-rel@testshop.com>",
            email_uid=600,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
            email_date=email_dt,
        )

    assert order is not None

    # Verify EmailScan was created
    result = await db_session.execute(
        select(EmailScan).where(EmailScan.message_id == "<msg-scan-rel@testshop.com>")
    )
    scan = result.scalar_one()
    assert scan.account_id == test_account.id
    assert scan.folder_path == "INBOX"
    assert scan.email_uid == 600
    assert scan.subject == "Your order is confirmed"
    assert scan.sender == "orders@testshop.com"
    # SQLite drops timezone info, so compare naive datetimes
    assert scan.email_date.replace(tzinfo=None) == email_dt.replace(tzinfo=None)
    assert scan.is_relevant is True
    assert scan.llm_raw_response == raw_response
    assert scan.order_id == order.id


@pytest.mark.asyncio
async def test_creates_email_scan_for_irrelevant_email(db_session, test_user, test_account):
    """Verify EmailScan is created with is_relevant=False and order_id=None for irrelevant emails."""
    analysis = EmailAnalysis(is_relevant=False)
    raw_response = {"is_relevant": False}

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = (analysis, raw_response)

        order = await process_email(
            subject="Weekly Newsletter",
            sender="newsletter@example.com",
            body="Check out our latest deals!",
            message_id="<msg-scan-irrel@example.com>",
            email_uid=700,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

    assert order is None

    # Verify EmailScan was created even for irrelevant email
    result = await db_session.execute(
        select(EmailScan).where(EmailScan.message_id == "<msg-scan-irrel@example.com>")
    )
    scan = result.scalar_one()
    assert scan.account_id == test_account.id
    assert scan.folder_path == "INBOX"
    assert scan.email_uid == 700
    assert scan.subject == "Weekly Newsletter"
    assert scan.sender == "newsletter@example.com"
    assert scan.is_relevant is False
    assert scan.llm_raw_response == raw_response
    assert scan.order_id is None


@pytest.mark.asyncio
async def test_dedup_via_email_scan(db_session, test_user, test_account):
    """Pre-create an EmailScan, verify process_email skips it without calling LLM."""
    # Pre-create an EmailScan record
    existing_scan = EmailScan(
        account_id=test_account.id,
        folder_path="INBOX",
        email_uid=800,
        message_id="<msg-prescan@example.com>",
        subject="Already scanned",
        sender="shop@example.com",
        is_relevant=True,
        llm_raw_response={"is_relevant": True},
    )
    db_session.add(existing_scan)
    await db_session.commit()

    with patch("app.services.email_processor.analyze_email", new_callable=AsyncMock) as mock_analyze:
        order = await process_email(
            subject="Already scanned",
            sender="shop@example.com",
            body="Some body",
            message_id="<msg-prescan@example.com>",
            email_uid=800,
            folder_path="INBOX",
            account_id=test_account.id,
            user_id=test_user.id,
            db=db_session,
        )

        # LLM should NOT have been called
        mock_analyze.assert_not_called()

    assert order is None

    # Verify no additional EmailScan was created
    result = await db_session.execute(
        select(EmailScan).where(EmailScan.message_id == "<msg-prescan@example.com>")
    )
    scans = result.scalars().all()
    assert len(scans) == 1
