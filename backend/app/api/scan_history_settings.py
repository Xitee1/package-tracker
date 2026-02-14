from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.scan_history_settings import ScanHistorySettings
from app.schemas.scan_history import ScanHistorySettingsResponse, UpdateScanHistorySettingsRequest

router = APIRouter(
    prefix="/api/v1/settings/scan-history",
    tags=["settings"],
    dependencies=[Depends(get_admin_user)],
)


async def _get_or_create_settings(db: AsyncSession) -> ScanHistorySettings:
    """Return the singleton settings row, creating defaults if none exist."""
    result = await db.execute(select(ScanHistorySettings))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = ScanHistorySettings(
            id=1,
            max_age_days=7,
            max_per_user=1000,
            cleanup_interval_hours=1.0,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/", response_model=ScanHistorySettingsResponse)
async def get_scan_history_settings(db: AsyncSession = Depends(get_db)):
    settings = await _get_or_create_settings(db)
    return settings


@router.put("/", response_model=ScanHistorySettingsResponse)
async def update_scan_history_settings(
    body: UpdateScanHistorySettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create_settings(db)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings
