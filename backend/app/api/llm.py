from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.llm_config import LLMConfig
from app.schemas.llm_config import LLMConfigRequest, LLMConfigResponse
from app.api.deps import get_admin_user
from app.services.llm_service import call_llm

router = APIRouter(prefix="/api/v1/llm", tags=["llm"], dependencies=[Depends(get_admin_user)])


@router.get("/config", response_model=LLMConfigResponse | None)
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None
    return LLMConfigResponse(
        id=config.id, provider=config.provider, model_name=config.model_name,
        api_base_url=config.api_base_url, is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
    )


@router.put("/config", response_model=LLMConfigResponse)
async def update_config(req: LLMConfigRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        config = LLMConfig(provider=req.provider, model_name=req.model_name)
        db.add(config)
    else:
        config.provider = req.provider
        config.model_name = req.model_name
    if req.api_key is not None:
        config.api_key_encrypted = encrypt_value(req.api_key)
    if req.api_base_url is not None:
        config.api_base_url = req.api_base_url
    config.is_active = True
    await db.commit()
    await db.refresh(config)
    return LLMConfigResponse(
        id=config.id, provider=config.provider, model_name=config.model_name,
        api_base_url=config.api_base_url, is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
    )


@router.post("/test")
async def test_llm(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=400, detail="No LLM configured")
    try:
        api_key = decrypt_value(config.api_key_encrypted) if config.api_key_encrypted else None
        text = await call_llm(
            config, api_key,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=5,
        )
        return {"success": True, "message": f"LLM responded: {text}"}
    except Exception as e:
        return {"success": False, "message": str(e)}
