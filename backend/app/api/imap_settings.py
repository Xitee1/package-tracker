from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.imap_settings import ImapSettings
from app.schemas.imap_settings import ImapSettingsRequest, ImapSettingsResponse
from app.api.deps import get_admin_user

router = APIRouter(prefix="/api/v1/settings/imap", tags=["settings"], dependencies=[Depends(get_admin_user)])

DEFAULTS = ImapSettingsResponse(id=0, max_email_age_days=7, processing_delay_sec=2.0, check_uidvalidity=True)


@router.get("", response_model=ImapSettingsResponse)
async def get_imap_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImapSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return DEFAULTS
    return settings


@router.put("", response_model=ImapSettingsResponse)
async def update_imap_settings(req: ImapSettingsRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ImapSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ImapSettings(
            max_email_age_days=req.max_email_age_days,
            processing_delay_sec=req.processing_delay_sec,
            check_uidvalidity=req.check_uidvalidity,
        )
        db.add(settings)
    else:
        settings.max_email_age_days = req.max_email_age_days
        settings.processing_delay_sec = req.processing_delay_sec
        settings.check_uidvalidity = req.check_uidvalidity
    await db.commit()
    await db.refresh(settings)
    return settings
