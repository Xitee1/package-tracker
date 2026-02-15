from app.models.user import User
from app.models.order import Order
from app.models.order_state import OrderState
from app.models.api_key import ApiKey
from app.models.imap_settings import ImapSettings
from app.models.queue_item import QueueItem
from app.models.queue_settings import QueueSettings
from app.models.module_config import ModuleConfig
from app.models.smtp_config import SmtpConfig

# Module models (imported so Alembic discovers them)
from app.modules._shared.email.models import ProcessedEmail
from app.modules.analysers.llm.models import LLMConfig
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress

__all__ = [
    "User", "Order", "OrderState", "ApiKey", "ImapSettings",
    "QueueItem", "QueueSettings", "ModuleConfig", "SmtpConfig",
    "ProcessedEmail", "LLMConfig", "EmailAccount", "WatchedFolder",
    "GlobalMailConfig", "UserSenderAddress",
]
