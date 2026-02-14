import imaplib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.encryption import decrypt_value, encrypt_value
from app.database import get_db
from app.models.global_mail_config import GlobalMailConfig
from app.models.module_config import ModuleConfig
from app.schemas.global_mail_config import (
    GlobalMailConfigRequest,
    GlobalMailConfigResponse,
    GlobalMailFoldersResponse,
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
        config.watched_folder_path = req.watched_folder_path
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/folders", response_model=GlobalMailFoldersResponse)
async def list_global_mail_folders(
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Global mail not configured")
    try:
        password = decrypt_value(config.imap_password_encrypted)
        if config.use_ssl:
            mail = imaplib.IMAP4_SSL(config.imap_host, config.imap_port)
        else:
            mail = imaplib.IMAP4(config.imap_host, config.imap_port)
        mail.login(config.imap_user, password)
        try:
            _, caps = mail.capability()
            capabilities = caps[0].decode().upper().split() if caps else []
            idle_supported = "IDLE" in capabilities

            _, folder_list = mail.list()
        finally:
            try:
                mail.logout()
            except Exception:
                pass
        folders = []
        for item in folder_list:
            decoded = item.decode() if isinstance(item, bytes) else item
            parts = decoded.rsplit('" "', 1)
            if len(parts) == 2:
                folders.append(parts[1].strip('"'))
            else:
                parts = decoded.rsplit(" ", 1)
                folders.append(parts[-1].strip('"'))
        return GlobalMailFoldersResponse(folders=folders, idle_supported=idle_supported)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {e}")


@router.get("/info", response_model=GlobalMailInfoResponse)
async def get_global_mail_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if module is enabled
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == "email-global")
    )
    module = result.scalar_one_or_none()
    if not module or not module.enabled:
        return GlobalMailInfoResponse(configured=False)

    config = await _get_config(db)
    if not config:
        return GlobalMailInfoResponse(configured=False)
    return GlobalMailInfoResponse(configured=True, email_address=config.imap_user)
