from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.module_config import ModuleConfig


async def _check_module(module_key: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if module and not module.enabled:
        raise HTTPException(status_code=403, detail=f"Module '{module_key}' is disabled")


async def require_email_imap(db: AsyncSession = Depends(get_db)) -> None:
    await _check_module("email-imap", db)


async def require_email_global(db: AsyncSession = Depends(get_db)) -> None:
    await _check_module("email-global", db)
