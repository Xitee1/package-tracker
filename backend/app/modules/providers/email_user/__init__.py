from app.core.module_base import ModuleInfo
from app.modules.providers.email_user.router import router
from app.modules.providers.email_user.user_router import user_router
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.modules.providers.email_user.service import start_all_watchers, stop_all_watchers, get_status

MODULE_INFO = ModuleInfo(
    key="email-user",
    name="Email - User IMAP",
    type="provider",
    version="1.0.0",
    description="Allow users to connect their own IMAP email accounts",
    router=router,
    user_router=user_router,
    models=[EmailAccount, WatchedFolder],
    startup=start_all_watchers,
    shutdown=stop_all_watchers,
    status=get_status,
)
