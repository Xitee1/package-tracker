import hashlib
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey

security = HTTPBearer()

_API_KEY_PREFIX = "pt_"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    if token.startswith(_API_KEY_PREFIX):
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()
        if api_key is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        now = datetime.now(timezone.utc)
        expires_at = api_key.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")
        api_key.last_used_at = now
        await db.commit()
        request.state.auth_method = "api_key"
        return await db.get(User, api_key.user_id)

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    request.state.auth_method = "jwt"
    return user


async def require_jwt_auth(request: Request, user: User = Depends(get_current_user)) -> User:
    if getattr(request.state, "auth_method", None) != "jwt":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API keys cannot access this endpoint")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
