from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_state import OrderState
from app.services.llm_service import EmailAnalysis


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def create_or_update_order(
    analysis: EmailAnalysis,
    user_id: int,
    existing_order: Order | None,
    *,
    source_type: str | None = None,
    source_info: str | None = None,
    db: AsyncSession,
) -> Order:
    """Create a new order or update an existing one based on LLM analysis.

    Also inserts an OrderState entry if the status changed or a new order was created.
    Returns the created/updated Order.
    """
    if existing_order:
        order = existing_order
        old_status = order.status

        if analysis.tracking_number and not order.tracking_number:
            order.tracking_number = analysis.tracking_number
        if analysis.carrier and not order.carrier:
            order.carrier = analysis.carrier
        if analysis.estimated_delivery:
            order.estimated_delivery = _parse_date(analysis.estimated_delivery)
        if analysis.status:
            order.status = analysis.status

        # Only insert OrderState if status actually changed
        if order.status != old_status:
            state = OrderState(
                order_id=order.id,
                status=order.status,
                source_type=source_type,
                source_info=source_info,
            )
            db.add(state)
    else:
        status = analysis.status or "ordered"
        order = Order(
            user_id=user_id,
            order_number=analysis.order_number,
            tracking_number=analysis.tracking_number,
            carrier=analysis.carrier,
            vendor_name=analysis.vendor_name,
            vendor_domain=analysis.vendor_domain,
            status=status,
            order_date=_parse_date(analysis.order_date),
            total_amount=analysis.total_amount,
            currency=analysis.currency,
            items=[item.model_dump() for item in analysis.items] if analysis.items else None,
            estimated_delivery=_parse_date(analysis.estimated_delivery),
        )
        db.add(order)
        await db.flush()

        # Initial state entry
        state = OrderState(
            order_id=order.id,
            status=status,
            source_type=source_type,
            source_info=source_info,
        )
        db.add(state)

    return order
