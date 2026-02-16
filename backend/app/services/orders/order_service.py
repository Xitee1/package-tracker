from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import asc, desc, func, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.order_state import OrderState
from app.modules.analysers.llm.service import EmailAnalysis
from app.schemas.order import CreateOrderRequest, UpdateOrderRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


_SORTABLE_COLUMNS = {
    "order_number": Order.order_number,
    "vendor_name": Order.vendor_name,
    "carrier": Order.carrier,
    "status": Order.status,
    "order_date": Order.order_date,
    "total_amount": Order.total_amount,
    "updated_at": Order.updated_at,
}


def _apply_search_filter(query, search: str | None):
    """Apply multi-field ILIKE search filter to an order query."""
    if not search:
        return query
    pattern = f"%{search}%"
    return query.where(
        (Order.order_number.ilike(pattern))
        | (Order.vendor_name.ilike(pattern))
        | (Order.tracking_number.ilike(pattern))
        | (Order.carrier.ilike(pattern))
        | (Order.vendor_domain.ilike(pattern))
    )


class OrderNotFoundError(Exception):
    """Raised when an order does not exist or the user is not authorised."""


class InvalidSortError(ValueError):
    """Raised when a caller supplies an unrecognised sort column/direction."""


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class OrderListResult:
    items: list[Order]
    total: int


# ---------------------------------------------------------------------------
# Service functions – manual / API operations
# ---------------------------------------------------------------------------

async def create_order(
    db: AsyncSession,
    user_id: int,
    data: CreateOrderRequest,
) -> Order:
    """Create an order from manual user input (API / UI)."""
    order = Order(
        user_id=user_id,
        vendor_name=data.vendor_name,
        order_number=data.order_number,
        tracking_number=data.tracking_number,
        carrier=data.carrier,
        vendor_domain=data.vendor_domain,
        status=data.status,
        order_date=data.order_date,
        total_amount=data.total_amount,
        currency=data.currency,
        estimated_delivery=data.estimated_delivery,
        items=[item.model_dump() for item in data.items] if data.items else None,
    )
    db.add(order)
    await db.flush()

    state = OrderState(
        order_id=order.id,
        status=data.status,
        source_type="manual",
    )
    db.add(state)
    await db.commit()
    await db.refresh(order)
    return order


async def list_orders(
    db: AsyncSession,
    user_id: int,
    *,
    page: int = 1,
    per_page: int = 25,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "order_date",
    sort_dir: str = "desc",
) -> OrderListResult:
    """List a user's orders with filtering, sorting, and pagination."""
    if sort_by not in _SORTABLE_COLUMNS:
        raise InvalidSortError(
            f"Invalid sort_by. Must be one of: {', '.join(sorted(_SORTABLE_COLUMNS))}"
        )
    if sort_dir not in ("asc", "desc"):
        raise InvalidSortError("Invalid sort_dir. Must be 'asc' or 'desc'")

    query = select(Order).where(Order.user_id == user_id)

    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.where(Order.status.in_(statuses))

    query = _apply_search_filter(query, search)

    # Total count (before pagination)
    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar() or 0

    # Sorting + pagination
    column = _SORTABLE_COLUMNS[sort_by]
    direction = asc if sort_dir == "asc" else desc
    query = query.order_by(nullslast(direction(column)))
    query = query.offset((page - 1) * per_page).limit(per_page)

    items = list((await db.execute(query)).scalars().all())
    return OrderListResult(items=items, total=total)


async def get_order_counts(
    db: AsyncSession,
    user_id: int,
    search: Optional[str] = None,
) -> dict[str, int]:
    """Return order counts grouped by status."""
    query = select(Order.status, func.count()).where(Order.user_id == user_id)
    query = _apply_search_filter(query, search)
    query = query.group_by(Order.status)

    counts = dict((await db.execute(query)).all())
    total = sum(counts.values())
    return {
        "total": total,
        "ordered": counts.get("ordered", 0),
        "shipment_preparing": counts.get("shipment_preparing", 0),
        "shipped": counts.get("shipped", 0),
        "in_transit": counts.get("in_transit", 0),
        "out_for_delivery": counts.get("out_for_delivery", 0),
        "delivered": counts.get("delivered", 0),
    }


async def get_order_detail(
    db: AsyncSession,
    user_id: int,
    order_id: int,
) -> Order:
    """Fetch a single order with its state history.

    Raises OrderNotFoundError when the order does not exist or belongs to
    another user.
    """
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.states))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise OrderNotFoundError
    return order


async def update_order(
    db: AsyncSession,
    user_id: int,
    order_id: int,
    data: UpdateOrderRequest,
) -> Order:
    """Apply a partial update to an order.

    Creates an OrderState entry when the status changes.
    Raises OrderNotFoundError when the order does not exist or belongs to
    another user.
    """
    order = await db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise OrderNotFoundError

    old_status = order.status
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    if data.status and data.status != old_status:
        db.add(OrderState(
            order_id=order.id,
            status=data.status,
            source_type="manual",
        ))

    await db.commit()
    await db.refresh(order)
    return order


async def link_orders(
    db: AsyncSession,
    user_id: int,
    source_id: int,
    target_id: int,
) -> Order:
    """Merge *target* order into *source* order.

    Copies missing tracking/carrier info, moves all state history, then
    deletes the target order.
    Raises OrderNotFoundError when either order does not exist or belongs
    to another user.
    """
    source = await db.get(Order, source_id)
    target = await db.get(Order, target_id)
    if (
        not source or source.user_id != user_id
        or not target or target.user_id != user_id
    ):
        raise OrderNotFoundError

    if target.tracking_number and not source.tracking_number:
        source.tracking_number = target.tracking_number
    if target.carrier and not source.carrier:
        source.carrier = target.carrier
    if target.status and target.status != "ordered":
        source.status = target.status

    # Move states from target to source
    result = await db.execute(
        select(OrderState).where(OrderState.order_id == target.id)
    )
    for state in result.scalars().all():
        state.order_id = source.id

    await db.delete(target)
    await db.commit()
    await db.refresh(source)
    return source


async def delete_order(
    db: AsyncSession,
    user_id: int,
    order_id: int,
) -> None:
    """Delete an order.

    Raises OrderNotFoundError when the order does not exist or belongs to
    another user.
    """
    order = await db.get(Order, order_id)
    if not order or order.user_id != user_id:
        raise OrderNotFoundError
    await db.delete(order)
    await db.commit()


# ---------------------------------------------------------------------------
# Service function – email-pipeline / automated operations
# ---------------------------------------------------------------------------

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
