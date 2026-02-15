from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.order import Order
from app.models.order_state import OrderState
from app.schemas.order import OrderResponse, OrderDetailResponse, UpdateOrderRequest, LinkOrderRequest, CreateOrderRequest, OrderListResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    req: CreateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    order = Order(
        user_id=user.id,
        vendor_name=req.vendor_name,
        order_number=req.order_number,
        tracking_number=req.tracking_number,
        carrier=req.carrier,
        vendor_domain=req.vendor_domain,
        status=req.status,
        order_date=req.order_date,
        total_amount=req.total_amount,
        currency=req.currency,
        estimated_delivery=req.estimated_delivery,
        items=[item.model_dump() for item in req.items] if req.items else None,
    )
    db.add(order)
    await db.flush()

    state = OrderState(
        order_id=order.id,
        status=req.status,
        source_type="manual",
    )
    db.add(state)
    await db.commit()
    await db.refresh(order)
    return order


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).where(Order.user_id == user.id)

    if status:
        statuses = [s.strip() for s in status.split(",")]
        query = query.where(Order.status.in_(statuses))
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Order.order_number.ilike(search_filter))
            | (Order.vendor_name.ilike(search_filter))
            | (Order.tracking_number.ilike(search_filter))
            | (Order.carrier.ilike(search_filter))
            | (Order.vendor_domain.ilike(search_filter))
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Order.updated_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return OrderListResponse(
        items=[OrderResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id).options(selectinload(Order.states))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: int, req: UpdateOrderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    old_status = order.status
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(order, field, value)

    # Create OrderState if status changed
    if req.status and req.status != old_status:
        state = OrderState(
            order_id=order.id,
            status=req.status,
            source_type="manual",
        )
        db.add(state)

    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/link")
async def link_orders(order_id: int, req: LinkOrderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    source = await db.get(Order, order_id)
    target = await db.get(Order, req.target_order_id)
    if not source or source.user_id != user.id or not target or target.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    if target.tracking_number and not source.tracking_number:
        source.tracking_number = target.tracking_number
    if target.carrier and not source.carrier:
        source.carrier = target.carrier
    if target.status and target.status != "ordered":
        source.status = target.status
    # Move states from target to source
    result = await db.execute(select(OrderState).where(OrderState.order_id == target.id))
    for state in result.scalars().all():
        state.order_id = source.id
    await db.delete(target)
    await db.commit()
    await db.refresh(source)
    return {"merged_into": source.id}


@router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
