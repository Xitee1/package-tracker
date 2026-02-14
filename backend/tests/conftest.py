import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("PT_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("PT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("PT_ENCRYPTION_KEY", "test-encryption-key")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with (
        patch("app.modules.providers.email_user.user_router.restart_watchers", new_callable=AsyncMock),
        patch("app.modules.providers.email_user.user_router.restart_single_watcher", new_callable=AsyncMock),
        patch("app.modules.providers.email_user.user_router.is_folder_scanning", return_value=False),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    app.dependency_overrides.clear()
