import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.api.deps import get_current_user
from app.database import get_db
from app.models.notification import UserNotificationConfig, EmailVerification
from app.services.email_service import send_email, is_smtp_configured
from app.modules.notifiers.notify_email.schemas import (
    NotifyEmailConfigRequest,
    NotifyEmailConfigResponse,
    NotifyEmailEventsRequest,
    NotifyEmailToggleRequest,
)

user_router = APIRouter(tags=["notify-email"])


async def _get_user_config(user_id: int, db: AsyncSession) -> UserNotificationConfig | None:
    result = await db.execute(
        select(UserNotificationConfig).where(
            UserNotificationConfig.user_id == user_id,
            UserNotificationConfig.module_key == "notify-email",
        )
    )
    return result.scalar_one_or_none()


@user_router.get("/config", response_model=NotifyEmailConfigResponse)
async def get_config(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        return NotifyEmailConfigResponse(enabled=False)
    email = config.config.get("email") if config.config else None
    verified = config.config.get("verified", False) if config.config else False
    return NotifyEmailConfigResponse(enabled=config.enabled, email=email, verified=verified, events=config.events or [])


@user_router.post("/config/email")
async def set_email(req: NotifyEmailConfigRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        if not await is_smtp_configured(db):
            raise HTTPException(status_code=400, detail="SMTP is not configured")
        config = await _get_user_config(user.id, db)
        if not config:
            config = UserNotificationConfig(user_id=user.id, module_key="notify-email", enabled=False, config={"email": req.email, "verified": False}, events=[])
            db.add(config)
        else:
            config.config = {"email": req.email, "verified": False}
        token = str(uuid.uuid4())
        verification = EmailVerification(user_id=user.id, email=req.email, token=token, expires_at=datetime.utcnow() + timedelta(hours=24))
        db.add(verification)
        await db.commit()
        verify_link = f"/verify-email/{token}"
        await send_email(to=req.email, subject="Package Tracker — Verify your email", html_body=f'<div style="font-family: sans-serif; max-width: 600px;"><h2>Verify your email address</h2><p>Click the link below to verify your email for Package Tracker notifications:</p><p><a href="{verify_link}">{verify_link}</a></p><p>This link expires in 24 hours.</p></div>', db=db)
        return {"status": "verification_sent"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to send verification email")
        raise HTTPException(status_code=500, detail="Failed to send verification email")


@user_router.post("/verify/{token}")
async def verify_email(token: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailVerification).where(EmailVerification.token == token, EmailVerification.user_id == user.id))
    verification = result.scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    now = datetime.utcnow()
    if verification.expires_at < now:
        raise HTTPException(status_code=400, detail="Verification link expired")
    if verification.verified_at:
        raise HTTPException(status_code=400, detail="Already verified")
    verification.verified_at = now
    config = await _get_user_config(user.id, db)
    if config:
        config.config = {"email": verification.email, "verified": True}
    await db.commit()
    return {"status": "verified", "email": verification.email}


@user_router.put("/config/toggle")
async def toggle_notifications(req: NotifyEmailToggleRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure email first")
    if req.enabled and (not config.config or not config.config.get("verified")):
        raise HTTPException(status_code=400, detail="Email not verified")
    config.enabled = req.enabled
    await db.commit()
    return {"status": "ok", "enabled": config.enabled}


@user_router.put("/config/events")
async def update_events(req: NotifyEmailEventsRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure email first")
    config.events = req.events
    await db.commit()
    return {"status": "ok", "events": config.events}
