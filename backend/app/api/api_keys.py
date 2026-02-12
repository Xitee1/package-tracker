import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.api.deps import require_jwt_auth
from app.schemas.api_key import CreateApiKeyRequest, ApiKeyResponse, ApiKeyCreatedResponse

_MAX_KEYS_PER_USER = 25
_KEY_EXPIRY_DAYS = 3650  # ~10 years

router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["api-keys"],
    dependencies=[Depends(require_jwt_auth)],
)


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(require_jwt_auth),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: CreateApiKeyRequest,
    user: User = Depends(require_jwt_auth),
    db: AsyncSession = Depends(get_db),
):
    count = await db.scalar(
        select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user.id)
    )
    if count >= _MAX_KEYS_PER_USER:
        raise HTTPException(status_code=400, detail=f"Maximum of {_MAX_KEYS_PER_USER} API keys reached")

    raw_key = f"pt_{secrets.token_hex(16)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        user_id=user.id,
        name=req.name,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        expires_at=datetime.now(timezone.utc) + timedelta(days=_KEY_EXPIRY_DAYS),
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        key=raw_key,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    user: User = Depends(require_jwt_auth),
    db: AsyncSession = Depends(get_db),
):
    api_key = await db.get(ApiKey, key_id)
    if not api_key or api_key.user_id != user.id:
        raise HTTPException(status_code=404, detail="API key not found")
    await db.delete(api_key)
    await db.commit()
