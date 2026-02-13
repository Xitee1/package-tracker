from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
from app.database import engine, wait_for_db
from app.models import *  # noqa: F401, F403
from app.services.imap_worker import start_all_watchers, stop_all_watchers


def _run_migrations(connection) -> None:
    """Run Alembic migrations using the given sync connection."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_db()
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)
    await start_all_watchers()
    yield
    await stop_all_watchers()


app = FastAPI(
    title="Package Tracker",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.accounts import router as accounts_router
from app.api.llm import router as llm_router
from app.api.orders import router as orders_router
from app.api.api_keys import router as api_keys_router
from app.api.system import router as system_router
from app.api.imap_settings import router as imap_settings_router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(llm_router)
app.include_router(orders_router)
app.include_router(api_keys_router)
app.include_router(system_router)
app.include_router(imap_settings_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
