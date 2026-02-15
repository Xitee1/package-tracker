from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.queue_settings import QueueSettings
from app.schemas.queue_settings import QueueSettingsResponse, UpdateQueueSettingsRequest

router = APIRouter(
    prefix="/api/v1/settings/queue",
    tags=["settings"],
    dependencies=[Depends(get_admin_user)],
)


async def _get_or_create_settings(db: AsyncSession) -> QueueSettings:
    result = await db.execute(select(QueueSettings))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = QueueSettings(id=1, max_age_days=7, max_per_user=5000)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/", response_model=QueueSettingsResponse)
async def get_queue_settings(db: AsyncSession = Depends(get_db)):
    return await _get_or_create_settings(db)


@router.patch("/", response_model=QueueSettingsResponse)
async def update_queue_settings(
    body: UpdateQueueSettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create_settings(db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings
