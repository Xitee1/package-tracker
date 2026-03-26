from app.core.module_base import ModuleInfo
from app.modules.notifiers.notify_webhook.router import router
from app.modules.notifiers.notify_webhook.user_router import user_router
from app.modules.notifiers.notify_webhook.service import send_notification

MODULE_INFO = ModuleInfo(
    key="notify-webhook",
    name="Webhook Notifications",
    type="notifier",
    version="1.0.0",
    description="Send webhook notifications for order events. Warning: users can target any URL, including internal network addresses. Only enable if you trust all users.",
    router=router,
    user_router=user_router,
    models=[],
    notify=send_notification,
)
