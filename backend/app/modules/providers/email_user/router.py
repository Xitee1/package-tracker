from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.imap_settings import ImapSettings
from app.schemas.imap_settings import ImapSettingsRequest, ImapSettingsResponse
from app.api.deps import get_admin_user

router = APIRouter(tags=["email-user"], dependencies=[Depends(get_admin_user)])

DEFAULTS = ImapSettingsResponse(id=0, max_email_age_days=7, check_uidvalidity=True)


@router.get("/settings", response_model=ImapSettingsResponse)
async def get_imap_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImapSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return DEFAULTS
    return settings


@router.put("/settings", response_model=ImapSettingsResponse)
async def update_imap_settings(req: ImapSettingsRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImapSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ImapSettings(
            max_email_age_days=req.max_email_age_days,
            check_uidvalidity=req.check_uidvalidity,
        )
        db.add(settings)
    else:
        settings.max_email_age_days = req.max_email_age_days
        settings.check_uidvalidity = req.check_uidvalidity
    await db.commit()
    await db.refresh(settings)
    return settings
