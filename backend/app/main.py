import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from app.database import engine, wait_for_db
from app.models import *  # noqa: F401, F403
from app.services.imap_worker import start_all_watchers, stop_all_watchers
from app.services.scheduler import create_scheduler, register_schedules

logger = logging.getLogger(__name__)


def _run_migrations(connection) -> None:
    """Run Alembic migrations, auto-detecting pre-Alembic databases."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["connection"] = connection

    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()

    if "alembic_version" not in tables and len(tables) > 0:
        # Pre-Alembic database: tables exist but Alembic hasn't been initialized.
        # Stamp the baseline (initial schema) as already applied.
        logger.info("Detected pre-Alembic database, stamping baseline revision.")
        command.stamp(alembic_cfg, "9299dae441a6")

    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations complete.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_db()
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)

    scheduler = await create_scheduler()
    async with scheduler:
        await register_schedules(scheduler)
        await scheduler.start_in_background()
        app.state.scheduler = scheduler
        await start_all_watchers()
        logger.info("Package Tracker is ready.")
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
from app.api.scan_history import router as scan_history_router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(accounts_router)
app.include_router(llm_router)
app.include_router(orders_router)
app.include_router(api_keys_router)
app.include_router(system_router)
app.include_router(imap_settings_router)
app.include_router(scan_history_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
