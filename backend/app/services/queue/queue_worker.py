import logging

from sqlalchemy import select

from app.database import async_session
from app.models.queue_item import QueueItem
from app.modules.analysers.llm.service import analyze
from app.services.orders.order_matcher import DefaultOrderMatcher
from app.services.orders.order_service import create_or_update_order
from app.core.module_registry import has_available_analyser
from app.services.notification_service import notify_user, NotificationEvent

logger = logging.getLogger(__name__)

_matcher = DefaultOrderMatcher()
_no_analyser_warned = False


async def process_next_item() -> None:
    """Pick one queued item and process it. Called by the scheduler every 5s."""
    global _no_analyser_warned

    if not await has_available_analyser():
        if not _no_analyser_warned:
            logger.warning("No analyser module is enabled and configured — queue processing paused")
            _no_analyser_warned = True
        return

    _no_analyser_warned = False

    async with async_session() as db:
        # Pick the oldest queued item
        result = await db.execute(
            select(QueueItem)
            .where(QueueItem.status == "queued")
            .order_by(QueueItem.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        item = result.scalar_one_or_none()
        if not item:
            return

        item.status = "processing"
        await db.commit()

        try:
            analysis, raw_response = await analyze(item.raw_data, db)

            item.extracted_data = raw_response

            if analysis is None or not analysis.is_relevant:
                item.status = "completed"
                await db.commit()
                return

            # Find matching order
            existing_order = await _matcher.find_match(analysis, item.user_id, db)

            # Create or update order
            order = await create_or_update_order(
                analysis=analysis,
                user_id=item.user_id,
                existing_order=existing_order,
                source_type=item.source_type,
                source_info=item.source_info,
                db=db,
            )

            item.order_id = order.id

            # Determine notification event type
            if existing_order:
                if order.status == "delivered":
                    notification_event = NotificationEvent.PACKAGE_DELIVERED
                else:
                    notification_event = NotificationEvent.TRACKING_UPDATE
            else:
                notification_event = NotificationEvent.NEW_ORDER

            # Send notifications (fire-and-forget, errors are logged)
            try:
                await notify_user(
                    user_id=item.user_id,
                    event_type=notification_event,
                    event_data={
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "tracking_number": order.tracking_number,
                        "vendor_name": order.vendor_name,
                        "status": order.status,
                        "carrier": order.carrier,
                        "items": [i.get("name", "") for i in (order.items or [])],
                    },
                )
            except Exception as e:
                logger.error(f"Notification dispatch failed for order {order.id}: {e}")

            item.status = "completed"
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to process queue item {item.id}: {e}")
            await db.rollback()
            async with async_session() as err_db:
                err_item = await err_db.get(QueueItem, item.id)
                if err_item:
                    err_item.status = "failed"
                    err_item.error_message = str(e)
                    await err_db.commit()
