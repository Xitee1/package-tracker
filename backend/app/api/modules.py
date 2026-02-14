from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_user
from app.database import get_db
from app.models.module_config import ModuleConfig
from app.schemas.module_config import ModuleResponse, UpdateModuleRequest
from app.core.module_registry import (
    get_all_modules, enable_module, disable_module,
)

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.priority, ModuleConfig.module_key))
    configs = result.scalars().all()
    all_modules = get_all_modules()
    response = []
    for config in configs:
        info = all_modules.get(config.module_key)
        configured = True
        if info and info.is_configured:
            try:
                configured = await info.is_configured()
            except Exception:
                configured = False
        response.append(ModuleResponse(
            module_key=config.module_key,
            enabled=config.enabled,
            configured=configured,
            priority=config.priority,
            name=info.name if info else None,
            type=info.type if info else None,
            description=info.description if info else None,
        ))
    return response


@router.put("/{module_key}", response_model=ModuleResponse)
async def update_module(
    module_key: str,
    req: UpdateModuleRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if module_key not in get_all_modules():
        raise HTTPException(status_code=404, detail="Unknown module")
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    was_enabled = module.enabled
    module.enabled = req.enabled
    await db.commit()
    await db.refresh(module)

    # Lifecycle hooks
    if req.enabled and not was_enabled:
        await enable_module(module_key)
    elif not req.enabled and was_enabled:
        await disable_module(module_key)

    all_modules = get_all_modules()
    info = all_modules.get(module_key)
    return ModuleResponse(
        module_key=module.module_key,
        enabled=module.enabled,
        priority=module.priority,
        name=info.name if info else None,
        type=info.type if info else None,
        description=info.description if info else None,
    )
