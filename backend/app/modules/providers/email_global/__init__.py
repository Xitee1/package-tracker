from sqlalchemy import select

from app.core.module_base import ModuleInfo
from app.modules.providers.email_global.router import router
from app.modules.providers.email_global.user_router import user_router
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress
from app.modules.providers.email_global.service import start_global_watcher, stop_global_watcher
from app.database import async_session


async def check_configured() -> bool:
    async with async_session() as db:
        result = await db.execute(select(GlobalMailConfig))
        return result.scalar_one_or_none() is not None


MODULE_INFO = ModuleInfo(
    key="email-global",
    name="Email - Global/Redirect",
    type="provider",
    version="1.0.0",
    description="Shared global email inbox with sender-based routing",
    router=router,
    user_router=user_router,
    models=[GlobalMailConfig, UserSenderAddress],
    startup=start_global_watcher,
    shutdown=stop_global_watcher,
    is_configured=check_configured,
)
