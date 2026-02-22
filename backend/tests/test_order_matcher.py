import pytest

from app.models.user import User
from app.models.order import Order
from app.schemas.analysis import AnalysisResult, ExtractedItem
from app.services.orders.order_matcher import DefaultOrderMatcher
from app.core.auth import hash_password


@pytest.fixture
async def test_user(db_session):
    """Create a test user in the DB."""
    user = User(username="matchuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def order_with_order_number(db_session, test_user):
    """Create an order with an order number."""
    order = Order(
        user_id=test_user.id,
        order_number="ORD-100",
        vendor_name="Amazon",
        vendor_domain="amazon.com",
        status="ordered",
        items=[{"name": "Wireless Mouse", "quantity": 1}],
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.fixture
async def order_with_tracking(db_session, test_user):
    """Create an order with a tracking number but no order number."""
    order = Order(
        user_id=test_user.id,
        tracking_number="1Z999AA10123456784",
        carrier="UPS",
        vendor_name="Newegg",
        vendor_domain="newegg.com",
        status="shipped",
        items=[{"name": "Graphics Card", "quantity": 1}],
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


@pytest.fixture
def matcher():
    return DefaultOrderMatcher()


@pytest.mark.asyncio
async def test_match_by_order_number(db_session, test_user, order_with_order_number, matcher):
    """Priority 1: exact order_number match."""
    analysis = AnalysisResult(
        is_relevant=True,
        order_number="ORD-100",
        vendor_domain="amazon.com",
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order_with_order_number.id
    assert matched.order_number == "ORD-100"


@pytest.mark.asyncio
async def test_match_by_tracking_number(db_session, test_user, order_with_tracking, matcher):
    """Priority 2: exact tracking_number match."""
    analysis = AnalysisResult(
        is_relevant=True,
        tracking_number="1Z999AA10123456784",
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order_with_tracking.id
    assert matched.tracking_number == "1Z999AA10123456784"


@pytest.mark.asyncio
async def test_match_by_vendor_and_items(db_session, test_user, order_with_order_number, matcher):
    """Priority 3: fuzzy match by vendor_domain + item name overlap."""
    analysis = AnalysisResult(
        is_relevant=True,
        vendor_domain="amazon.com",
        items=[ExtractedItem(name="Wireless Mouse", quantity=1)],
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order_with_order_number.id


@pytest.mark.asyncio
async def test_no_match_returns_none(db_session, test_user, order_with_order_number, matcher):
    """When nothing matches, return None."""
    analysis = AnalysisResult(
        is_relevant=True,
        order_number="ORD-NONEXISTENT",
        vendor_domain="bestbuy.com",
        items=[ExtractedItem(name="Laptop Stand", quantity=1)],
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is None


@pytest.mark.asyncio
async def test_no_match_different_user(db_session, test_user, order_with_order_number, matcher):
    """Orders from a different user should not match."""
    other_user = User(username="otheruser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    analysis = AnalysisResult(
        is_relevant=True,
        order_number="ORD-100",
    )
    matched = await matcher.find_match(analysis, other_user.id, db_session)
    assert matched is None


@pytest.mark.asyncio
async def test_fuzzy_match_case_insensitive(db_session, test_user, order_with_order_number, matcher):
    """Fuzzy item name matching should be case-insensitive."""
    analysis = AnalysisResult(
        is_relevant=True,
        vendor_domain="amazon.com",
        items=[ExtractedItem(name="wireless mouse", quantity=1)],
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order_with_order_number.id


@pytest.mark.asyncio
async def test_order_number_takes_priority_over_tracking(db_session, test_user, order_with_order_number, order_with_tracking, matcher):
    """Order number match should take priority even if tracking also matches a different order."""
    analysis = AnalysisResult(
        is_relevant=True,
        order_number="ORD-100",
        tracking_number="1Z999AA10123456784",
    )
    matched = await matcher.find_match(analysis, test_user.id, db_session)
    assert matched is not None
    assert matched.id == order_with_order_number.id
