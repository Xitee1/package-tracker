import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from alembic.config import Config
from alembic import command
import sqlalchemy as sa
from app.database import engine, wait_for_db
from app.models import *  # noqa: F401, F403
from app.core.module_registry import (
    discover_modules, sync_module_configs, startup_enabled_modules,
    shutdown_all_modules, get_all_modules,
)
from app.services.scheduler import create_scheduler, register_schedules

logging.basicConfig(level=logging.INFO, format="%(levelname)-5s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


def _run_migrations(connection) -> None:
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["connection"] = connection
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    if "alembic_version" not in tables and len(tables) > 0:
        logger.info("Detected pre-Alembic database, stamping baseline revision.")
        command.stamp(alembic_cfg, "9cc36a87ec5f")
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
        await sync_module_configs()
        await startup_enabled_modules()
        logger.info("Package Tracker is ready.")
        yield
        await shutdown_all_modules()


# Discover modules BEFORE creating app so routes are ready
discover_modules()

app = FastAPI(
    title="Package Tracker",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Core routes
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.orders import router as orders_router
from app.api.api_keys import router as api_keys_router
from app.api.system import router as system_router
from app.api.queue import router as queue_router
from app.api.queue_settings import router as queue_settings_router
from app.api.modules import router as modules_router
from app.api.version import router as version_router
from app.api.smtp import router as smtp_router
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(orders_router)
app.include_router(api_keys_router)
app.include_router(system_router)
app.include_router(queue_router)
app.include_router(queue_settings_router)
app.include_router(modules_router)
app.include_router(version_router)
app.include_router(smtp_router)

# Module routes (auto-discovered)
for key, info in get_all_modules().items():
    prefix = f"/api/v1/modules/{info.type}s/{info.key}"
    app.include_router(info.router, prefix=prefix, tags=[f"module:{info.key}"])
    if info.user_router:
        user_prefix = f"/api/v1/{info.type}s/{info.key}"
        app.include_router(info.user_router, prefix=user_prefix, tags=[f"module:{info.key}:user"])


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
