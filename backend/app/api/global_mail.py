from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.encryption import encrypt_value
from app.database import get_db
from app.models.global_mail_config import GlobalMailConfig
from app.schemas.global_mail_config import (
    GlobalMailConfigRequest,
    GlobalMailConfigResponse,
    GlobalMailInfoResponse,
)

router = APIRouter(prefix="/api/v1/settings/global-mail", tags=["settings"])


async def _get_config(db: AsyncSession) -> GlobalMailConfig | None:
    result = await db.execute(select(GlobalMailConfig))
    return result.scalar_one_or_none()


@router.get("", response_model=GlobalMailConfigResponse | None)
async def get_global_mail_config(
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_config(db)


@router.put("", response_model=GlobalMailConfigResponse)
async def update_global_mail_config(
    req: GlobalMailConfigRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if not config:
        config = GlobalMailConfig(
            imap_host=req.imap_host,
            imap_port=req.imap_port,
            imap_user=req.imap_user,
            imap_password_encrypted=encrypt_value(req.imap_password) if req.imap_password else "",
            use_ssl=req.use_ssl,
            polling_interval_sec=req.polling_interval_sec,
            use_polling=req.use_polling,
            is_active=req.is_active,
            watched_folder_path=req.watched_folder_path,
        )
        db.add(config)
    else:
        config.imap_host = req.imap_host
        config.imap_port = req.imap_port
        config.imap_user = req.imap_user
        if req.imap_password:
            config.imap_password_encrypted = encrypt_value(req.imap_password)
        config.use_ssl = req.use_ssl
        config.polling_interval_sec = req.polling_interval_sec
        config.use_polling = req.use_polling
        config.is_active = req.is_active
        config.watched_folder_path = req.watched_folder_path
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/info", response_model=GlobalMailInfoResponse)
async def get_global_mail_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if not config or not config.is_active:
        return GlobalMailInfoResponse(configured=False)
    return GlobalMailInfoResponse(configured=True, email_address=config.imap_user)
