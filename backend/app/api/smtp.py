import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.encryption import encrypt_value
from app.database import get_db
from app.models.smtp_config import SmtpConfig
from app.schemas.smtp import SmtpConfigRequest, SmtpConfigResponse, SmtpTestRequest
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/smtp", tags=["smtp"], dependencies=[Depends(get_admin_user)])


async def _get_config(db: AsyncSession) -> SmtpConfig | None:
    result = await db.execute(select(SmtpConfig))
    return result.scalar_one_or_none()


@router.get("", response_model=SmtpConfigResponse | None)
async def get_smtp_config(db: AsyncSession = Depends(get_db)):
    return await _get_config(db)


@router.put("", response_model=SmtpConfigResponse)
async def save_smtp_config(req: SmtpConfigRequest, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if not config:
        config = SmtpConfig(
            host=req.host,
            port=req.port,
            username=req.username,
            password_encrypted=encrypt_value(req.password) if req.password else None,
            security=req.security,
            sender_address=req.sender_address,
            sender_name=req.sender_name,
        )
        db.add(config)
    else:
        config.host = req.host
        config.port = req.port
        config.username = req.username
        if req.password:
            config.password_encrypted = encrypt_value(req.password)
        config.security = req.security
        config.sender_address = req.sender_address
        config.sender_name = req.sender_name
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/test")
async def test_smtp(req: SmtpTestRequest, db: AsyncSession = Depends(get_db)):
    try:
        await send_email(
            to=req.recipient,
            subject="Package Tracker — SMTP Test",
            html_body="<p>This is a test email from Package Tracker. If you received this, SMTP is configured correctly.</p>",
            db=db,
        )
        return {"status": "ok"}
    except Exception as e:
        logger.warning("SMTP test failed for recipient %s: %s", req.recipient, e)
        raise HTTPException(status_code=502, detail="Failed to send test email")
