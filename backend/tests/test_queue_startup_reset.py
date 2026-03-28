"""Tests for queue startup reset (stuck 'processing' items reset to 'queued')."""

from sqlalchemy import select, update

from app.core.auth import hash_password
from app.models.queue_item import QueueItem
from app.models.user import User
from app.main import reset_stuck_queue_items


import pytest


@pytest.fixture
async def test_user(db_session):
    user = User(username="resetuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _make_queue_item(user_id: int, status: str = "queued") -> QueueItem:
    return QueueItem(
        user_id=user_id,
        status=status,
        source_type="email",
        source_info="test",
        raw_data={"subject": "Test"},
    )


async def test_reset_stuck_processing_items(db_session, test_user):
    """Items stuck at 'processing' should be reset to 'queued'."""
    stuck = _make_queue_item(test_user.id, status="processing")
    db_session.add(stuck)
    await db_session.commit()
    await db_session.refresh(stuck)

    count = await reset_stuck_queue_items(db_session)

    assert count == 1
    await db_session.refresh(stuck)
    assert stuck.status == "queued"


async def test_reset_does_not_touch_other_statuses(db_session, test_user):
    """Items with status queued/completed/failed must not be changed."""
    items = [
        _make_queue_item(test_user.id, status="queued"),
        _make_queue_item(test_user.id, status="completed"),
        _make_queue_item(test_user.id, status="failed"),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    for item in items:
        await db_session.refresh(item)

    count = await reset_stuck_queue_items(db_session)

    assert count == 0
    for item, expected in zip(items, ["queued", "completed", "failed"]):
        await db_session.refresh(item)
        assert item.status == expected


async def test_reset_returns_zero_when_nothing_stuck(db_session):
    """Returns 0 when no items are stuck."""
    count = await reset_stuck_queue_items(db_session)
    assert count == 0
