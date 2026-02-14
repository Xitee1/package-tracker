from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_user
from app.database import get_db
from app.models.module_config import ModuleConfig
from app.schemas.module_config import ModuleResponse, UpdateModuleRequest

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])

KNOWN_MODULES = {"email-imap", "email-global"}


async def _ensure_modules_exist(db: AsyncSession) -> None:
    """Create module rows if they don't exist (first-run without migration seed)."""
    result = await db.execute(select(ModuleConfig))
    existing = {m.module_key for m in result.scalars().all()}
    for key in KNOWN_MODULES:
        if key not in existing:
            db.add(ModuleConfig(module_key=key, enabled=(key == "email-imap")))
    if KNOWN_MODULES - existing:
        await db.commit()


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_modules_exist(db)
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.module_key))
    return result.scalars().all()


@router.put("/{module_key}", response_model=ModuleResponse)
async def update_module(
    module_key: str,
    req: UpdateModuleRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if module_key not in KNOWN_MODULES:
        raise HTTPException(status_code=404, detail="Unknown module")
    await _ensure_modules_exist(db)
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    module.enabled = req.enabled
    await db.commit()
    await db.refresh(module)
    return module
