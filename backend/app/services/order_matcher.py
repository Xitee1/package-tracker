from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.services.llm_service import EmailAnalysis


async def find_matching_order(analysis: EmailAnalysis, user_id: int, db: AsyncSession) -> Order | None:
    """Find an existing order that matches the email analysis result."""

    # Priority 1: exact order_number match
    if analysis.order_number:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id, Order.order_number == analysis.order_number)
        )
        order = result.scalar_one_or_none()
        if order:
            return order

    # Priority 2: exact tracking_number match
    if analysis.tracking_number:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id, Order.tracking_number == analysis.tracking_number)
        )
        order = result.scalar_one_or_none()
        if order:
            return order

    # Priority 3: fuzzy match - same vendor_domain + item name overlap
    if analysis.vendor_domain:
        result = await db.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.vendor_domain == analysis.vendor_domain,
            ).order_by(Order.created_at.desc()).limit(5)
        )
        candidates = result.scalars().all()

        if analysis.items and candidates:
            email_item_names = {item.name.lower() for item in analysis.items if item.name}
            for candidate in candidates:
                if candidate.items:
                    order_item_names = {item.get("name", "").lower() for item in candidate.items}
                    overlap = email_item_names & order_item_names
                    if overlap:
                        return candidate

    return None
