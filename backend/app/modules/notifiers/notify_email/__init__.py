from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_base import ModuleInfo
from app.modules.notifiers.notify_email.router import router
from app.modules.notifiers.notify_email.user_router import user_router
from app.modules.notifiers.notify_email.service import send_notification
from app.services.email_service import is_smtp_configured


async def check_configured(db: AsyncSession) -> bool:
    return await is_smtp_configured(db)


MODULE_INFO = ModuleInfo(
    key="notify-email",
    name="Email Notifications",
    type="notifier",
    version="1.0.0",
    description="Send email notifications for order events",
    router=router,
    user_router=user_router,
    models=[],
    is_configured=check_configured,
    notify=send_notification,
)
