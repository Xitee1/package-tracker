import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules._shared.email.models import ProcessedEmail
from app.models.queue_item import QueueItem

logger = logging.getLogger(__name__)


async def check_dedup_and_enqueue(
    message_id: str,
    subject: str,
    sender: str,
    body: str,
    email_date: datetime | None,
    email_uid: int,
    user_id: int,
    source_info: str,
    account_id: int | None,
    folder_path: str,
    source: str,
    db: AsyncSession,
) -> bool:
    """Check for duplicate, enqueue if new. Returns True if enqueued."""
    existing = await db.execute(
        select(ProcessedEmail).where(ProcessedEmail.message_id == message_id)
    )
    if existing.scalar_one_or_none():
        return False

    queue_item = QueueItem(
        user_id=user_id,
        status="queued",
        source_type="email",
        source_info=source_info,
        raw_data={
            "subject": subject,
            "sender": sender,
            "body": body,
            "message_id": message_id,
            "email_uid": email_uid,
            "email_date": email_date.isoformat() if email_date else None,
        },
    )
    db.add(queue_item)
    await db.flush()

    processed = ProcessedEmail(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=email_uid,
        message_id=message_id,
        queue_item_id=queue_item.id,
        source=source,
    )
    db.add(processed)

    return True
