from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.queue_item import QueueItem
from app.schemas.queue_item import QueueItemResponse, QueueItemSummaryResponse, QueueItemListResponse, QueueStatsResponse
from app.api.deps import get_current_user, get_admin_user

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.get("", response_model=QueueItemListResponse)
async def list_queue_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(QueueItem).where(QueueItem.user_id == user.id)

    if status:
        query = query.where(QueueItem.status == status)
    if source_type:
        query = query.where(QueueItem.source_type == source_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(QueueItem.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return QueueItemListResponse(
        items=[QueueItemSummaryResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", response_model=QueueStatsResponse)
async def queue_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    counts = {}
    for s in ("queued", "processing", "completed", "failed"):
        result = await db.execute(
            select(func.count())
            .select_from(QueueItem)
            .where(QueueItem.user_id == user.id, QueueItem.status == s)
        )
        counts[s] = result.scalar() or 0
    return QueueStatsResponse(**counts)


@router.get("/{item_id}", response_model=QueueItemResponse)
async def get_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")
    await db.delete(item)
    await db.commit()


@router.post("/{item_id}/retry", response_model=QueueItemResponse)
async def retry_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")

    clone = QueueItem(
        user_id=item.user_id,
        status="queued",
        source_type=item.source_type,
        source_info=item.source_info,
        raw_data=item.raw_data,
        extracted_data=None,
        error_message=None,
        order_id=None,
        cloned_from_id=item.id,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return clone
