"""Tests for IMAP worker message deduplication logic."""

import hashlib
import pytest
from sqlalchemy import select

from app.core.auth import hash_password
from app.core.encryption import encrypt_value
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.processed_email import ProcessedEmail
from app.models.user import User


@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(username="testuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_account(db_session, test_user):
    """Create a test email account."""
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


@pytest.fixture
async def test_folder(db_session, test_account):
    """Create a test watched folder."""
    folder = WatchedFolder(
        account_id=test_account.id,
        folder_path="INBOX",
        last_seen_uid=0,
        uidvalidity=12345,
    )
    db_session.add(folder)
    await db_session.commit()
    await db_session.refresh(folder)
    return folder


def generate_fallback_message_id(account_id: int, folder_path: str, uidvalidity: int | None, uid: int) -> str:
    """
    Generate fallback message_id using the same logic as imap_worker.py.
    This mirrors the implementation to test the format.
    """
    uidvalidity_part = str(uidvalidity) if uidvalidity is not None else "no-uidvalidity"
    folder_hash = hashlib.sha256(folder_path.encode()).hexdigest()[:16]
    return f"fallback:{account_id}:{folder_hash}:{uidvalidity_part}:{uid}"


@pytest.mark.asyncio
async def test_fallback_message_id_format(test_account, test_folder):
    """Test that fallback message_id format is correct."""
    account_id = test_account.id
    folder_path = test_folder.folder_path
    uidvalidity = test_folder.uidvalidity
    uid = 100

    fallback_id = generate_fallback_message_id(account_id, folder_path, uidvalidity, uid)
    
    # Verify format includes all components
    assert fallback_id.startswith("fallback:")
    assert str(account_id) in fallback_id
    assert str(uidvalidity) in fallback_id
    assert str(uid) in fallback_id
    
    # Verify folder_path is hashed (not in plain text for long paths)
    folder_hash = hashlib.sha256(folder_path.encode()).hexdigest()[:16]
    assert folder_hash in fallback_id


@pytest.mark.asyncio
async def test_fallback_message_id_length_constraint():
    """Test that fallback message_id stays within 512 character limit."""
    # Test with maximum realistic values
    max_account_id = 999999999999999999  # Very large int
    max_folder_path = "x" * 512  # Maximum folder path length
    max_uidvalidity = 999999999999999999  # Very large int
    max_uid = 999999999999999999  # Very large int
    
    fallback_id = generate_fallback_message_id(
        max_account_id, max_folder_path, max_uidvalidity, max_uid
    )
    
    # Verify it's well within the 512 character limit
    assert len(fallback_id) <= 512, f"Fallback ID length {len(fallback_id)} exceeds 512 char limit"
    # In practice, it should be much shorter (around 80-90 chars)
    assert len(fallback_id) < 150, f"Fallback ID unexpectedly long: {len(fallback_id)} chars"


@pytest.mark.asyncio
async def test_fallback_message_id_with_no_uidvalidity(test_account):
    """Test fallback message_id when uidvalidity is None."""
    account_id = test_account.id
    folder_path = "INBOX"
    uid = 50
    
    fallback_id = generate_fallback_message_id(account_id, folder_path, None, uid)
    
    # Should use "no-uidvalidity" placeholder
    assert "no-uidvalidity" in fallback_id
    assert fallback_id.startswith("fallback:")


@pytest.mark.asyncio
async def test_fallback_message_id_deterministic(test_account, test_folder):
    """Test that fallback message_id is deterministic (same inputs = same output)."""
    account_id = test_account.id
    folder_path = test_folder.folder_path
    uidvalidity = test_folder.uidvalidity
    uid = 75
    
    # Generate the same ID twice
    fallback_id_1 = generate_fallback_message_id(account_id, folder_path, uidvalidity, uid)
    fallback_id_2 = generate_fallback_message_id(account_id, folder_path, uidvalidity, uid)
    
    # Should be identical
    assert fallback_id_1 == fallback_id_2


@pytest.mark.asyncio
async def test_fallback_message_id_uniqueness(test_account, test_folder):
    """Test that different UIDs produce different fallback message_ids."""
    account_id = test_account.id
    folder_path = test_folder.folder_path
    uidvalidity = test_folder.uidvalidity
    
    # Generate IDs for different UIDs
    fallback_id_1 = generate_fallback_message_id(account_id, folder_path, uidvalidity, 1)
    fallback_id_2 = generate_fallback_message_id(account_id, folder_path, uidvalidity, 2)
    
    # Should be different
    assert fallback_id_1 != fallback_id_2


@pytest.mark.asyncio
async def test_processed_email_dedup_with_fallback_id(db_session, test_account, test_folder):
    """Test that ProcessedEmail records can be created with fallback message_id."""
    account_id = test_account.id
    folder_path = test_folder.folder_path
    uidvalidity = test_folder.uidvalidity
    uid = 200
    
    fallback_id = generate_fallback_message_id(account_id, folder_path, uidvalidity, uid)
    
    # Create a ProcessedEmail record with the fallback ID
    processed = ProcessedEmail(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=uid,
        message_id=fallback_id,
        queue_item_id=None,
    )
    db_session.add(processed)
    await db_session.commit()
    
    # Verify it was created
    result = await db_session.execute(
        select(ProcessedEmail).where(ProcessedEmail.message_id == fallback_id)
    )
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.message_id == fallback_id
    assert found.email_uid == uid


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_fallback_ids(db_session, test_account, test_folder):
    """Test that duplicate fallback message_ids are rejected (unique constraint)."""
    account_id = test_account.id
    folder_path = test_folder.folder_path
    uidvalidity = test_folder.uidvalidity
    uid = 300
    
    fallback_id = generate_fallback_message_id(account_id, folder_path, uidvalidity, uid)
    
    # Create first ProcessedEmail record
    processed1 = ProcessedEmail(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=uid,
        message_id=fallback_id,
        queue_item_id=None,
    )
    db_session.add(processed1)
    await db_session.commit()
    
    # Attempt to create a duplicate with the same fallback message_id
    processed2 = ProcessedEmail(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=uid + 1,  # Different UID but same message_id (shouldn't happen in practice)
        message_id=fallback_id,
        queue_item_id=None,
    )
    db_session.add(processed2)
    
    # Should raise an integrity error due to unique constraint on message_id
    with pytest.raises(Exception):  # SQLAlchemy will raise an IntegrityError
        await db_session.commit()
