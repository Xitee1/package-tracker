import pytest
from unittest.mock import AsyncMock, patch

from app.services.notification_service import notify_user, NotificationEvent


@pytest.mark.asyncio
async def test_notify_user_no_modules():
    """Should do nothing when no notifier modules exist."""
    with patch("app.services.notification_service.get_modules_by_type", return_value={}):
        await notify_user(1, NotificationEvent.NEW_ORDER, {"order_id": 1})
