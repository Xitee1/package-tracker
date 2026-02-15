from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.notification import UserNotificationConfig
from app.modules.notifiers.notify_webhook.schemas import (
    WebhookConfigRequest, WebhookConfigResponse, WebhookEventsRequest, WebhookToggleRequest, WebhookTestRequest,
)

user_router = APIRouter(tags=["notify-webhook"])


async def _get_user_config(user_id: int, db: AsyncSession) -> UserNotificationConfig | None:
    result = await db.execute(select(UserNotificationConfig).where(UserNotificationConfig.user_id == user_id, UserNotificationConfig.module_key == "notify-webhook"))
    return result.scalar_one_or_none()


@user_router.get("/config", response_model=WebhookConfigResponse)
async def get_config(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        return WebhookConfigResponse(enabled=False)
    return WebhookConfigResponse(enabled=config.enabled, url=config.config.get("url") if config.config else None, has_auth_header=bool(config.config.get("auth_header_encrypted")) if config.config else False, events=config.events or [])


@user_router.put("/config/webhook")
async def set_webhook(req: WebhookConfigRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    config_data = {"url": str(req.url)}
    if req.auth_header:
        config_data["auth_header_encrypted"] = encrypt_value(req.auth_header)
    if not config:
        config = UserNotificationConfig(user_id=user.id, module_key="notify-webhook", enabled=False, config=config_data, events=[])
        db.add(config)
    else:
        config.config = config_data
    await db.commit()
    return {"status": "ok"}


@user_router.put("/config/toggle")
async def toggle_notifications(req: WebhookToggleRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config or not config.config or not config.config.get("url"):
        raise HTTPException(status_code=400, detail="Configure webhook URL first")
    config.enabled = req.enabled
    await db.commit()
    return {"status": "ok", "enabled": config.enabled}


@user_router.put("/config/events")
async def update_events(req: WebhookEventsRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure webhook first")
    config.events = req.events
    await db.commit()
    return {"status": "ok", "events": config.events}


@user_router.post("/test")
async def test_webhook(req: WebhookTestRequest, user=Depends(get_current_user)):
    headers = {"Content-Type": "application/json"}
    if req.auth_header:
        headers["Authorization"] = req.auth_header
    payload = {"event": "test", "data": {"message": "This is a test notification from Package Tracker."}}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(str(req.url), json=payload, headers=headers)
        return {"status": "ok", "response_code": resp.status_code}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
