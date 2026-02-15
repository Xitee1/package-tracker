import imaplib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.encryption import decrypt_value, encrypt_value
from app.database import get_db
from app.modules.providers.email_global.models import GlobalMailConfig
from app.modules.providers.email_global.schemas import (
    GlobalMailConfigRequest,
    GlobalMailConfigResponse,
    GlobalMailFoldersResponse,
)

router = APIRouter(tags=["email-global"], dependencies=[Depends(get_admin_user)])


async def _get_config(db: AsyncSession) -> GlobalMailConfig | None:
    result = await db.execute(select(GlobalMailConfig))
    return result.scalar_one_or_none()


@router.get("/config", response_model=GlobalMailConfigResponse | None)
async def get_global_mail_config(
    db: AsyncSession = Depends(get_db),
):
    return await _get_config(db)


@router.patch("/config", response_model=GlobalMailConfigResponse)
async def update_global_mail_config(
    req: GlobalMailConfigRequest,
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
