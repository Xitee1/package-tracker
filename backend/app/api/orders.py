from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.schemas.order import (
    OrderResponse,
    OrderDetailResponse,
    UpdateOrderRequest,
    LinkOrderRequest,
    CreateOrderRequest,
    OrderListResponse,
    OrderCountsResponse,
)
from app.api.deps import get_current_user
from app.services.orders.order_service import (
    create_order as svc_create_order,
    list_orders as svc_list_orders,
    get_order_counts as svc_get_order_counts,
    get_order_detail as svc_get_order_detail,
    update_order as svc_update_order,
    link_orders as svc_link_orders,
    delete_order as svc_delete_order,
    OrderNotFoundError,
    InvalidSortError,
)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    req: CreateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc_create_order(db, user.id, req)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("order_date"),
    sort_dir: str = Query("desc"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await svc_list_orders(
            db, user.id,
            page=page,
            per_page=per_page,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except InvalidSortError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return OrderListResponse(
        items=[OrderResponse.model_validate(i) for i in result.items],
        total=result.total,
        page=page,
        per_page=per_page,
    )


@router.get("/counts", response_model=OrderCountsResponse)
async def order_counts(
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    counts = await svc_get_order_counts(db, user.id, search)
    return OrderCountsResponse(**counts)


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc_get_order_detail(db, user.id, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    req: UpdateOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc_update_order(db, user.id, order_id, req)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")


@router.post("/{order_id}/link")
async def link_orders(
    order_id: int,
    req: LinkOrderRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        source = await svc_link_orders(db, user.id, order_id, req.target_order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"merged_into": source.id}


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await svc_delete_order(db, user.id, order_id)
    except OrderNotFoundError:
        raise HTTPException(status_code=404, detail="Order not found")
