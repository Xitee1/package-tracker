from datetime import datetime, timedelta, timezone

import pytest

from sqlalchemy import select

from app.core.auth import hash_password
from app.core.encryption import encrypt_value
from app.models.email_account import EmailAccount
from app.models.email_scan import EmailScan
from app.models.scan_history_settings import ScanHistorySettings
from app.models.user import User
from app.services.history_cleanup import cleanup_scan_history


@pytest.fixture
async def cleanup_user(db_session):
    user = User(username="cleanupuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def cleanup_account(db_session, cleanup_user):
    account = EmailAccount(
        user_id=cleanup_user.id,
        name="Cleanup Account",
        imap_host="imap.example.com",
        imap_port=993,
        imap_user="cleanup@example.com",
        imap_password_encrypted=encrypt_value("password"),
        use_ssl=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


def _make_scan(account_id: int, uid: int, created_at: datetime) -> EmailScan:
    return EmailScan(
        account_id=account_id,
        folder_path="INBOX",
        email_uid=uid,
        message_id=f"<msg-cleanup-{uid}@example.com>",
        subject=f"Test email {uid}",
        sender="test@example.com",
        is_relevant=False,
        llm_raw_response={"is_relevant": False},
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_cleanup_removes_old_scans(db_session, cleanup_account):
    """Scans older than max_age_days should be removed."""
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    recent = now - timedelta(days=1)

    # 3 old scans + 2 recent scans
    for uid in [1, 2, 3]:
        db_session.add(_make_scan(cleanup_account.id, uid, old))
    for uid in [4, 5]:
        db_session.add(_make_scan(cleanup_account.id, uid, recent))

    settings = ScanHistorySettings(max_age_days=7, max_per_user=1000, cleanup_interval_hours=1.0)
    db_session.add(settings)
    await db_session.commit()

    await cleanup_scan_history(db_session)

    result = await db_session.execute(select(EmailScan))
    remaining = result.scalars().all()
    assert len(remaining) == 2
    remaining_uids = {s.email_uid for s in remaining}
    assert remaining_uids == {4, 5}


@pytest.mark.asyncio
async def test_cleanup_respects_max_per_user(db_session, cleanup_account):
    """When a user exceeds max_per_user, the oldest excess scans should be removed."""
    now = datetime.now(timezone.utc)

    # Create 5 scans with incrementing timestamps (all recent, so age filter won't catch them)
    for uid in range(1, 6):
        db_session.add(
            _make_scan(
                cleanup_account.id,
                uid,
                now - timedelta(hours=6 - uid),  # uid=1 oldest, uid=5 newest
            )
        )

    settings = ScanHistorySettings(max_age_days=30, max_per_user=3, cleanup_interval_hours=1.0)
    db_session.add(settings)
    await db_session.commit()

    await cleanup_scan_history(db_session)

    result = await db_session.execute(select(EmailScan))
    remaining = result.scalars().all()
    assert len(remaining) == 3
    remaining_uids = {s.email_uid for s in remaining}
    # The 3 newest should remain (uid 3, 4, 5)
    assert remaining_uids == {3, 4, 5}


@pytest.mark.asyncio
async def test_cleanup_no_settings(db_session, cleanup_account):
    """If no ScanHistorySettings exist, cleanup should do nothing and not crash."""
    now = datetime.now(timezone.utc)
    for uid in range(1, 4):
        db_session.add(_make_scan(cleanup_account.id, uid, now - timedelta(days=100)))
    await db_session.commit()

    # No ScanHistorySettings in DB
    await cleanup_scan_history(db_session)

    result = await db_session.execute(select(EmailScan))
    remaining = result.scalars().all()
    assert len(remaining) == 3  # Nothing removed
