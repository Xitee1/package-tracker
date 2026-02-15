import enum
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_registry import get_modules_by_type
from app.database import async_session
from app.models.module_config import ModuleConfig
from app.models.notification import UserNotificationConfig

logger = logging.getLogger(__name__)


class NotificationEvent(str, enum.Enum):
    NEW_ORDER = "new_order"
    TRACKING_UPDATE = "tracking_update"
    PACKAGE_DELIVERED = "package_delivered"


async def notify_user(
    user_id: int,
    event_type: NotificationEvent,
    event_data: dict,
) -> None:
    """Send notifications to a user via all their enabled notification channels."""
    notifier_modules = get_modules_by_type("notifier")
    if not notifier_modules:
        return

    async with async_session() as db:
        # Get enabled notifier module keys
        result = await db.execute(
            select(ModuleConfig).where(
                ModuleConfig.module_key.in_(notifier_modules.keys()),
                ModuleConfig.enabled == True,
            )
        )
        enabled_keys = {m.module_key for m in result.scalars().all()}

        if not enabled_keys:
            return

        # Get user's notification configs
        result = await db.execute(
            select(UserNotificationConfig).where(
                UserNotificationConfig.user_id == user_id,
                UserNotificationConfig.module_key.in_(enabled_keys),
                UserNotificationConfig.enabled == True,
            )
        )
        user_configs = result.scalars().all()

        for config in user_configs:
            # Check if user subscribed to this event
            if config.events and event_type.value not in config.events:
                continue

            module_info = notifier_modules.get(config.module_key)
            if not module_info or not module_info.notify:
                continue

            try:
                await module_info.notify(user_id, event_type.value, event_data, config.config, db)
                logger.info(f"Notification sent via {config.module_key} to user {user_id} for {event_type.value}")
            except Exception as e:
                logger.error(f"Failed to send notification via {config.module_key} to user {user_id}: {e}")
