"""Tests for queue retention cleanup (app.services.queue.queue_retention)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.auth import hash_password
from app.models.queue_item import QueueItem
from app.models.queue_settings import QueueSettings
from app.models.user import User
from app.services.queue.queue_retention import cleanup_queue


@pytest.fixture
async def cleanup_user(db_session):
    user = User(username="cleanupuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _make_item(user_id: int, uid: int, created_at: datetime) -> QueueItem:
    return QueueItem(
        user_id=user_id,
        status="completed",
        source_type="email",
        source_info="INBOX",
        raw_data={"subject": f"Test email {uid}", "sender": "test@example.com", "body": "body"},
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_cleanup_removes_old_items(db_session, cleanup_user):
    """Items older than max_age_days should be removed."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    recent = now - timedelta(days=1)

    # 3 old items + 2 recent items
    for uid in [1, 2, 3]:
        db_session.add(_make_item(cleanup_user.id, uid, old))
    for uid in [4, 5]:
        db_session.add(_make_item(cleanup_user.id, uid, recent))

    settings = QueueSettings(max_age_days=7, max_per_user=1000)
    db_session.add(settings)
    await db_session.commit()

    await cleanup_queue(db_session)

    result = await db_session.execute(select(QueueItem))
    remaining = result.scalars().all()
    assert len(remaining) == 2


@pytest.mark.asyncio
async def test_cleanup_respects_max_per_user(db_session, cleanup_user):
    """When a user exceeds max_per_user, the oldest excess items should be removed."""
    now = datetime.now(timezone.utc)

    # Create 5 items with incrementing timestamps (all recent)
    for uid in range(1, 6):
        db_session.add(
            _make_item(
                cleanup_user.id,
                uid,
                now - timedelta(hours=6 - uid),  # uid=1 oldest, uid=5 newest
            )
        )

    settings = QueueSettings(max_age_days=30, max_per_user=3)
    db_session.add(settings)
    await db_session.commit()

    await cleanup_queue(db_session)

    result = await db_session.execute(select(QueueItem))
    remaining = result.scalars().all()
    assert len(remaining) == 3


@pytest.mark.asyncio
async def test_cleanup_no_settings(db_session, cleanup_user):
    """If no QueueSettings exist, cleanup should do nothing and not crash."""
    now = datetime.now(timezone.utc)
    for uid in range(1, 4):
        db_session.add(_make_item(cleanup_user.id, uid, now - timedelta(days=100)))
    await db_session.commit()

    # No QueueSettings in DB
    await cleanup_queue(db_session)

    result = await db_session.execute(select(QueueItem))
    remaining = result.scalars().all()
    assert len(remaining) == 3  # Nothing removed
