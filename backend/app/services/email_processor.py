from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_scan import EmailScan
from app.models.order import Order, OrderEvent
from app.services.llm_service import analyze_email, EmailAnalysis
from app.services.order_matcher import find_matching_order


def _parse_date(value: str | None) -> date | None:
    """Parse a YYYY-MM-DD string into a date object, returning None on failure."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def process_email(
    subject: str,
    sender: str,
    body: str,
    message_id: str,
    email_uid: int,
    folder_path: str,
    account_id: int,
    user_id: int,
    db: AsyncSession,
    email_date: datetime | None = None,
) -> Order | None:
    """Process a single email: analyze with LLM, match/create order, log event."""

    # Dedup: check if this message_id was already scanned
    existing = await db.execute(
        select(EmailScan).where(EmailScan.message_id == message_id)
    )
    if existing.scalar_one_or_none():
        return None

    # Analyze with LLM
    analysis, raw_response = await analyze_email(subject, sender, body, db)

    # Determine relevance
    is_relevant = analysis is not None and analysis.is_relevant

    # Create EmailScan row for every email (relevant or not)
    scan = EmailScan(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=email_uid,
        message_id=message_id,
        subject=subject,
        sender=sender,
        email_date=email_date,
        is_relevant=is_relevant,
        llm_raw_response=raw_response,
    )
    db.add(scan)

    if not is_relevant:
        await db.commit()
        return None

    # Find matching order or create new one
    order = await find_matching_order(analysis, user_id, db)
    old_status = order.status if order else None

    if order:
        # Update existing order
        event_type = "status_update"
        if analysis.tracking_number and not order.tracking_number:
            order.tracking_number = analysis.tracking_number
            event_type = "shipment_added"
        if analysis.carrier and not order.carrier:
            order.carrier = analysis.carrier
        if analysis.estimated_delivery:
            order.estimated_delivery = _parse_date(analysis.estimated_delivery)
        if analysis.status:
            order.status = analysis.status
    else:
        # Create new order
        event_type = "order_confirmed"
        order = Order(
            user_id=user_id,
            order_number=analysis.order_number,
            tracking_number=analysis.tracking_number,
            carrier=analysis.carrier,
            vendor_name=analysis.vendor_name,
            vendor_domain=analysis.vendor_domain,
            status=analysis.status or "ordered",
            order_date=_parse_date(analysis.order_date),
            total_amount=analysis.total_amount,
            currency=analysis.currency,
            items=[item.model_dump() for item in analysis.items] if analysis.items else None,
            estimated_delivery=_parse_date(analysis.estimated_delivery),
        )
        db.add(order)
        await db.flush()

    # Link the scan to the matched/created order
    scan.order_id = order.id

    # Log event
    event = OrderEvent(
        order_id=order.id,
        event_type=event_type,
        old_status=old_status,
        new_status=order.status,
        source_email_message_id=message_id,
        source_email_uid=email_uid,
        source_folder=folder_path,
        source_account_id=account_id,
        llm_raw_response=raw_response,
    )
    db.add(event)
    await db.commit()
    await db.refresh(order)
    return order
