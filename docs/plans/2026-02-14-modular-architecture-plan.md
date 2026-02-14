# Modular Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the backend and frontend into a drop-in module architecture where Analysers and Providers are self-contained packages discovered at startup.

**Architecture:** Each module lives in `app/modules/{type}/{name}/` with its own models, schemas, router, and service. A module registry discovers modules at startup, registers routes, syncs DB config, and manages lifecycle hooks. Shared IMAP utilities live in `modules/_shared/email/`. The frontend mirrors this with `src/modules/` containing per-module views, stores, and manifests.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Vue 3 Composition API, TypeScript, Pinia, Tailwind CSS 4

---

## Task 1: Create module base types and registry (backend)

**Files:**
- Create: `backend/app/core/module_base.py`
- Create: `backend/app/core/module_registry.py`
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/analysers/__init__.py`
- Create: `backend/app/modules/providers/__init__.py`
- Create: `backend/app/modules/_shared/__init__.py`
- Create: `backend/app/modules/_shared/email/__init__.py`

**Step 1: Create module base type definitions**

Create `backend/app/core/module_base.py`:

```python
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any
from fastapi import APIRouter


@dataclass
class ModuleInfo:
    """Manifest that every module must provide as MODULE_INFO."""
    key: str
    name: str
    type: str  # "analyser" or "provider"
    version: str
    description: str
    router: APIRouter
    models: list[Any] = field(default_factory=list)
    user_router: APIRouter | None = None
    startup: Callable[[], Awaitable[None]] | None = None
    shutdown: Callable[[], Awaitable[None]] | None = None
```

**Step 2: Create the module registry**

Create `backend/app/core/module_registry.py`:

```python
import importlib
import logging
import pkgutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_base import ModuleInfo
from app.database import async_session
from app.models.module_config import ModuleConfig

logger = logging.getLogger(__name__)

_registered_modules: dict[str, ModuleInfo] = {}


def get_module(key: str) -> ModuleInfo | None:
    return _registered_modules.get(key)


def get_all_modules() -> dict[str, ModuleInfo]:
    return dict(_registered_modules)


def get_modules_by_type(module_type: str) -> dict[str, ModuleInfo]:
    return {k: v for k, v in _registered_modules.items() if v.type == module_type}


def discover_modules() -> dict[str, ModuleInfo]:
    """Scan app/modules/analysers/ and app/modules/providers/ for MODULE_INFO."""
    _registered_modules.clear()
    modules_dir = Path(__file__).parent.parent / "modules"

    for module_type in ("analysers", "providers"):
        type_dir = modules_dir / module_type
        if not type_dir.is_dir():
            continue
        for finder, name, is_pkg in pkgutil.iter_modules([str(type_dir)]):
            if not is_pkg or name.startswith("_"):
                continue
            module_path = f"app.modules.{module_type}.{name}"
            try:
                mod = importlib.import_module(module_path)
                info = getattr(mod, "MODULE_INFO", None)
                if not isinstance(info, ModuleInfo):
                    logger.warning(f"Module {module_path} has no valid MODULE_INFO, skipping")
                    continue
                _registered_modules[info.key] = info
                logger.info(f"Discovered module: {info.key} ({info.type})")
            except Exception as e:
                logger.error(f"Failed to load module {module_path}: {e}")

    return _registered_modules


async def sync_module_configs() -> None:
    """Ensure every discovered module has a ModuleConfig row in the database."""
    async with async_session() as db:
        result = await db.execute(select(ModuleConfig))
        existing = {m.module_key for m in result.scalars().all()}
        for key in _registered_modules:
            if key not in existing:
                db.add(ModuleConfig(module_key=key, enabled=False))
                logger.info(f"Created ModuleConfig for new module: {key}")
        if _registered_modules.keys() - existing:
            await db.commit()


async def startup_enabled_modules() -> None:
    """Call startup() on all enabled modules that have a startup hook."""
    async with async_session() as db:
        result = await db.execute(select(ModuleConfig).where(ModuleConfig.enabled == True))
        enabled_keys = {m.module_key for m in result.scalars().all()}

    for key, info in _registered_modules.items():
        if key in enabled_keys and info.startup:
            try:
                await info.startup()
                logger.info(f"Module {key} started")
            except Exception as e:
                logger.error(f"Failed to start module {key}: {e}")


async def shutdown_all_modules() -> None:
    """Call shutdown() on all modules that have a shutdown hook."""
    for key, info in _registered_modules.items():
        if info.shutdown:
            try:
                await info.shutdown()
                logger.info(f"Module {key} stopped")
            except Exception as e:
                logger.error(f"Failed to stop module {key}: {e}")


async def enable_module(key: str) -> None:
    """Enable a module and call its startup hook."""
    info = _registered_modules.get(key)
    if info and info.startup:
        await info.startup()


async def disable_module(key: str) -> None:
    """Disable a module and call its shutdown hook."""
    info = _registered_modules.get(key)
    if info and info.shutdown:
        await info.shutdown()
```

**Step 3: Create empty `__init__.py` files for module packages**

Create these empty files:
- `backend/app/modules/__init__.py`
- `backend/app/modules/analysers/__init__.py`
- `backend/app/modules/providers/__init__.py`
- `backend/app/modules/_shared/__init__.py`
- `backend/app/modules/_shared/email/__init__.py`

**Step 4: Commit**

```bash
git add backend/app/core/module_base.py backend/app/core/module_registry.py backend/app/modules/
git commit -m "feat: add module base types and registry for drop-in module architecture"
```

---

## Task 2: Create the LLM analyser module (backend)

**Files:**
- Create: `backend/app/modules/analysers/llm/__init__.py`
- Create: `backend/app/modules/analysers/llm/models.py`
- Create: `backend/app/modules/analysers/llm/schemas.py`
- Create: `backend/app/modules/analysers/llm/router.py`
- Create: `backend/app/modules/analysers/llm/service.py`
- Reference: `backend/app/models/llm_config.py`, `backend/app/schemas/llm.py`, `backend/app/api/llm.py`, `backend/app/services/llm_service.py`

**Step 1: Move LLM model**

Copy the `LLMConfig` model from `backend/app/models/llm_config.py` to `backend/app/modules/analysers/llm/models.py`. Keep the exact same class definition (same table name, same columns).

**Step 2: Move LLM schemas**

Copy the schemas from `backend/app/schemas/llm.py` to `backend/app/modules/analysers/llm/schemas.py`. Keep exact same classes.

**Step 3: Move LLM service**

Copy `backend/app/services/llm_service.py` to `backend/app/modules/analysers/llm/service.py`. Update the import of `LLMConfig` to come from `app.modules.analysers.llm.models` instead of `app.models.llm_config`.

**Step 4: Move LLM router**

Copy `backend/app/api/llm.py` to `backend/app/modules/analysers/llm/router.py`. Update imports:
- `LLMConfig` from `app.modules.analysers.llm.models`
- Schemas from `app.modules.analysers.llm.schemas`
- Change the router prefix from `/api/v1/llm` to `""` (prefix will be added by the registry)

**Step 5: Create the module manifest**

Create `backend/app/modules/analysers/llm/__init__.py`:

```python
from app.core.module_base import ModuleInfo
from app.modules.analysers.llm.router import router
from app.modules.analysers.llm.models import LLMConfig

MODULE_INFO = ModuleInfo(
    key="llm",
    name="LLM Analyser",
    type="analyser",
    version="1.0.0",
    description="Analyse emails using LLM (via LiteLLM) to extract order information",
    router=router,
    models=[LLMConfig],
)
```

**Step 6: Commit**

```bash
git add backend/app/modules/analysers/llm/
git commit -m "feat: create LLM analyser module"
```

---

## Task 3: Create shared email utilities (backend)

**Files:**
- Create: `backend/app/modules/_shared/email/models.py`
- Create: `backend/app/modules/_shared/email/imap_client.py`
- Create: `backend/app/modules/_shared/email/imap_watcher.py`
- Create: `backend/app/modules/_shared/email/email_fetcher.py`
- Reference: `backend/app/services/imap_worker.py`, `backend/app/models/processed_email.py`

**Step 1: Move ProcessedEmail model**

Copy the `ProcessedEmail` model from `backend/app/models/processed_email.py` to `backend/app/modules/_shared/email/models.py`.

**Step 2: Extract IMAP client utilities**

Create `backend/app/modules/_shared/email/imap_client.py` with these functions extracted from `imap_worker.py`:
- `_decode_header_value()`
- `_extract_email_from_header()`
- `_extract_body()`

These are pure utility functions with no state.

**Step 3: Extract IMAP watcher utilities**

Create `backend/app/modules/_shared/email/imap_watcher.py` with shared IMAP connection/watch infrastructure extracted from `imap_worker.py`:
- `WorkerMode` enum
- `WorkerState` dataclass
- Constants: `IDLE_TIMEOUT_SEC`, `MAX_BACKOFF_SEC`

These are the shared types that both email modules use for state tracking.

**Step 4: Extract email fetching utilities**

Create `backend/app/modules/_shared/email/email_fetcher.py` with the dedup-check + enqueue logic that both `_fetch_new_emails()` and `_fetch_global_emails()` share. This should be a reusable function like:

```python
async def check_dedup_and_enqueue(
    message_id: str,
    subject: str,
    sender: str,
    body: str,
    email_date: datetime | None,
    email_uid: int,
    user_id: int,
    source_info: str,
    account_id: int | None,
    folder_path: str,
    source: str,
    db: AsyncSession,
) -> bool:
    """Check for duplicate, enqueue if new. Returns True if enqueued."""
```

**Step 5: Commit**

```bash
git add backend/app/modules/_shared/email/
git commit -m "feat: extract shared email utilities for module reuse"
```

---

## Task 4: Create email-user provider module (backend)

**Files:**
- Create: `backend/app/modules/providers/email_user/__init__.py`
- Create: `backend/app/modules/providers/email_user/models.py`
- Create: `backend/app/modules/providers/email_user/schemas.py`
- Create: `backend/app/modules/providers/email_user/router.py`
- Create: `backend/app/modules/providers/email_user/user_router.py`
- Create: `backend/app/modules/providers/email_user/service.py`
- Reference: `backend/app/models/email_account.py`, `backend/app/schemas/account.py`, `backend/app/api/accounts.py`, `backend/app/api/imap_settings.py`, `backend/app/services/imap_worker.py`

**Step 1: Move EmailAccount and WatchedFolder models**

Copy from `backend/app/models/email_account.py` to `backend/app/modules/providers/email_user/models.py`. Keep exact same table names and columns.

**Step 2: Move account schemas**

Copy from `backend/app/schemas/account.py` to `backend/app/modules/providers/email_user/schemas.py`.

**Step 3: Create the user-facing router**

Extract the user-facing account CRUD routes from `backend/app/api/accounts.py` into `backend/app/modules/providers/email_user/user_router.py`. This includes:
- List accounts, create account, update account, delete account
- Test connection
- List folders, watched folders, add/remove watched folders, update watched folder, scan folder

Change the router prefix from `/api/v1/accounts` to `""` (the registry will mount it under `/api/v1/providers/email-user/`).

Update all model/schema imports to come from the module.

**Step 4: Create the admin router**

Extract the admin IMAP settings from `backend/app/api/imap_settings.py` into `backend/app/modules/providers/email_user/router.py`. This router serves the admin settings page for this module.

Change the router prefix to `""` (the registry will mount under `/api/v1/modules/providers/email-user/`).

**Step 5: Extract per-user watcher service**

Create `backend/app/modules/providers/email_user/service.py` with the user-account-specific watcher logic extracted from `imap_worker.py`:
- `_watch_folder()`, `_idle_loop()`, `_poll_loop()`
- `_fetch_new_emails()` (uses shared `check_dedup_and_enqueue` from `_shared`)
- `_connect_and_select()`
- `start_all_watchers()`, `stop_all_watchers()`, `restart_watchers()`, `restart_single_watcher()`
- `_running_tasks`, `_worker_state` dicts
- `get_worker_states()`, `is_folder_scanning()`

Update imports to use:
- `app.modules._shared.email.models.ProcessedEmail`
- `app.modules._shared.email.imap_client` for utilities
- `app.modules._shared.email.imap_watcher` for WorkerMode/WorkerState
- `app.modules._shared.email.email_fetcher` for dedup+enqueue
- `app.modules.providers.email_user.models` for EmailAccount, WatchedFolder

**Step 6: Create the module manifest**

Create `backend/app/modules/providers/email_user/__init__.py`:

```python
from app.core.module_base import ModuleInfo
from app.modules.providers.email_user.router import router
from app.modules.providers.email_user.user_router import user_router
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.modules.providers.email_user.service import start_all_watchers, stop_all_watchers

MODULE_INFO = ModuleInfo(
    key="email-user",
    name="Email - User IMAP",
    type="provider",
    version="1.0.0",
    description="Allow users to connect their own IMAP email accounts",
    router=router,
    user_router=user_router,
    models=[EmailAccount, WatchedFolder],
    startup=start_all_watchers,
    shutdown=stop_all_watchers,
)
```

**Step 7: Commit**

```bash
git add backend/app/modules/providers/email_user/
git commit -m "feat: create email-user provider module"
```

---

## Task 5: Create email-global provider module (backend)

**Files:**
- Create: `backend/app/modules/providers/email_global/__init__.py`
- Create: `backend/app/modules/providers/email_global/models.py`
- Create: `backend/app/modules/providers/email_global/schemas.py`
- Create: `backend/app/modules/providers/email_global/router.py`
- Create: `backend/app/modules/providers/email_global/user_router.py`
- Create: `backend/app/modules/providers/email_global/service.py`
- Reference: `backend/app/models/global_mail_config.py`, `backend/app/models/user_sender_address.py`, `backend/app/schemas/global_mail.py`, `backend/app/schemas/sender_address.py`, `backend/app/api/global_mail.py`, `backend/app/api/sender_addresses.py`, `backend/app/services/imap_worker.py`

**Step 1: Move GlobalMailConfig and UserSenderAddress models**

Copy from `backend/app/models/global_mail_config.py` and `backend/app/models/user_sender_address.py` into `backend/app/modules/providers/email_global/models.py`. Both models in one file.

**Step 2: Move schemas**

Combine `backend/app/schemas/global_mail.py` and `backend/app/schemas/sender_address.py` into `backend/app/modules/providers/email_global/schemas.py`.

**Step 3: Move admin router**

Copy `backend/app/api/global_mail.py` to `backend/app/modules/providers/email_global/router.py`. Change prefix to `""`. Update imports.

**Step 4: Move user router**

Copy `backend/app/api/sender_addresses.py` to `backend/app/modules/providers/email_global/user_router.py`. Change prefix to `""`. Update imports. Also include the `/info` endpoint (currently in `global_mail.py`) that returns the global inbox address for users.

**Step 5: Extract global watcher service**

Create `backend/app/modules/providers/email_global/service.py` with the global-mail-specific watcher logic from `imap_worker.py`:
- `_watch_global_folder()`, `_global_idle_loop()`, `_global_poll_loop()`
- `_fetch_global_emails()` (uses shared `check_dedup_and_enqueue`)
- `_start_global_watcher()`
- `start_global_watcher()` (startup hook), `stop_global_watcher()` (shutdown hook)
- `_global_task`, `_global_state` tracking

Update imports similar to email_user module.

**Step 6: Create the module manifest**

```python
from app.core.module_base import ModuleInfo
from app.modules.providers.email_global.router import router
from app.modules.providers.email_global.user_router import user_router
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress
from app.modules.providers.email_global.service import start_global_watcher, stop_global_watcher

MODULE_INFO = ModuleInfo(
    key="email-global",
    name="Email - Global/Redirect",
    type="provider",
    version="1.0.0",
    description="Shared global email inbox with sender-based routing",
    router=router,
    user_router=user_router,
    models=[GlobalMailConfig, UserSenderAddress],
    startup=start_global_watcher,
    shutdown=stop_global_watcher,
)
```

**Step 7: Commit**

```bash
git add backend/app/modules/providers/email_global/
git commit -m "feat: create email-global provider module"
```

---

## Task 6: Wire up module registry in main.py and update modules API

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/api/modules.py`
- Modify: `backend/alembic/env.py`

**Step 1: Update `main.py` to use module registry**

Replace the manual router imports and watcher startup with module discovery:

```python
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
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(orders_router)
app.include_router(api_keys_router)
app.include_router(system_router)
app.include_router(queue_router)
app.include_router(queue_settings_router)
app.include_router(modules_router)

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
```

**Step 2: Update `models/__init__.py`**

Import module models so Alembic sees them:

```python
from app.models.user import User
from app.models.order import Order
from app.models.order_state import OrderState
from app.models.api_key import ApiKey
from app.models.imap_settings import ImapSettings
from app.models.queue_item import QueueItem
from app.models.queue_settings import QueueSettings
from app.models.module_config import ModuleConfig

# Module models (imported so Alembic discovers them)
from app.modules._shared.email.models import ProcessedEmail
from app.modules.analysers.llm.models import LLMConfig
from app.modules.providers.email_user.models import EmailAccount, WatchedFolder
from app.modules.providers.email_global.models import GlobalMailConfig, UserSenderAddress

__all__ = [
    "User", "Order", "OrderState", "ApiKey", "ImapSettings",
    "QueueItem", "QueueSettings", "ModuleConfig",
    "ProcessedEmail", "LLMConfig", "EmailAccount", "WatchedFolder",
    "GlobalMailConfig", "UserSenderAddress",
]
```

**Step 3: Update `api/modules.py`**

Replace the hardcoded `KNOWN_MODULES` with dynamic discovery from the registry. Add enable/disable lifecycle hooks:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_user
from app.database import get_db
from app.models.module_config import ModuleConfig
from app.schemas.module_config import ModuleResponse, UpdateModuleRequest
from app.core.module_registry import (
    get_all_modules, enable_module, disable_module,
)

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.module_key))
    return result.scalars().all()


@router.put("/{module_key}", response_model=ModuleResponse)
async def update_module(
    module_key: str,
    req: UpdateModuleRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if module_key not in get_all_modules():
        raise HTTPException(status_code=404, detail="Unknown module")
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    was_enabled = module.enabled
    module.enabled = req.enabled
    await db.commit()
    await db.refresh(module)

    # Lifecycle hooks
    if req.enabled and not was_enabled:
        await enable_module(module_key)
    elif not req.enabled and was_enabled:
        await disable_module(module_key)

    return module
```

**Step 4: Update `ModuleResponse` schema to include module metadata**

Modify `backend/app/schemas/module_config.py` to add name, type, description from the registry:

```python
from pydantic import BaseModel


class ModuleResponse(BaseModel):
    module_key: str
    enabled: bool
    name: str | None = None
    type: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class UpdateModuleRequest(BaseModel):
    enabled: bool
```

Then update the `list_modules` endpoint to enrich responses with registry metadata:

```python
@router.get("")
async def list_modules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.module_key))
    configs = result.scalars().all()
    all_modules = get_all_modules()
    response = []
    for config in configs:
        info = all_modules.get(config.module_key)
        response.append(ModuleResponse(
            module_key=config.module_key,
            enabled=config.enabled,
            name=info.name if info else None,
            type=info.type if info else None,
            description=info.description if info else None,
        ))
    return response
```

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/models/__init__.py backend/app/api/modules.py backend/app/schemas/module_config.py
git commit -m "feat: wire module registry into app startup and modules API"
```

---

## Task 7: Update queue processor to use module import path

**Files:**
- Modify: `backend/app/services/queue/queue_processor.py`

**Step 1: Update the import**

Change the import in `queue_processor.py` from:
```python
from app.services.llm_service import EmailAnalysis, analyze_email
```
to:
```python
from app.modules.analysers.llm.service import EmailAnalysis, analyze_email
```

**Step 2: Commit**

```bash
git add backend/app/services/queue/queue_processor.py
git commit -m "refactor: update queue processor to import from LLM module"
```

---

## Task 8: Update system API worker state imports

**Files:**
- Modify: `backend/app/api/system.py` (if it imports from imap_worker for worker states)

**Step 1: Check and update imports**

If `system.py` imports `get_worker_states` or similar from `imap_worker`, update to import from both module services:
- `app.modules.providers.email_user.service` for user watcher states
- `app.modules.providers.email_global.service` for global watcher state

**Step 2: Commit**

```bash
git add backend/app/api/system.py
git commit -m "refactor: update system API to import worker states from modules"
```

---

## Task 9: Delete old backend files

**Files:**
- Delete: `backend/app/api/llm.py`
- Delete: `backend/app/api/global_mail.py`
- Delete: `backend/app/api/sender_addresses.py`
- Delete: `backend/app/api/accounts.py`
- Delete: `backend/app/api/imap_settings.py`
- Delete: `backend/app/api/module_deps.py`
- Delete: `backend/app/models/llm_config.py`
- Delete: `backend/app/models/global_mail_config.py`
- Delete: `backend/app/models/user_sender_address.py`
- Delete: `backend/app/models/email_account.py`
- Delete: `backend/app/models/watched_folder.py` (if separate file, check if it's in email_account.py)
- Delete: `backend/app/models/processed_email.py`
- Delete: `backend/app/schemas/llm.py`
- Delete: `backend/app/schemas/global_mail.py`
- Delete: `backend/app/schemas/sender_address.py`
- Delete: `backend/app/schemas/account.py`
- Delete: `backend/app/services/llm_service.py`
- Delete: `backend/app/services/imap_worker.py`

**Step 1: Delete the files**

```bash
rm backend/app/api/llm.py backend/app/api/global_mail.py backend/app/api/sender_addresses.py \
   backend/app/api/accounts.py backend/app/api/imap_settings.py backend/app/api/module_deps.py
rm backend/app/models/llm_config.py backend/app/models/global_mail_config.py \
   backend/app/models/user_sender_address.py backend/app/models/processed_email.py
rm backend/app/schemas/llm.py backend/app/schemas/global_mail.py \
   backend/app/schemas/sender_address.py backend/app/schemas/account.py
rm backend/app/services/llm_service.py backend/app/services/imap_worker.py
```

Note: `EmailAccount` and `WatchedFolder` are both in `email_account.py` based on `models/__init__.py`. Delete that file. Check if `watched_folder.py` exists separately.

**Step 2: Search for any remaining imports of deleted modules**

```bash
grep -r "from app.api.llm\|from app.api.global_mail\|from app.api.sender_addresses\|from app.api.accounts\|from app.api.imap_settings\|from app.api.module_deps\|from app.services.llm_service\|from app.services.imap_worker\|from app.models.llm_config\|from app.models.global_mail\|from app.models.email_account\|from app.models.processed_email\|from app.models.user_sender_address\|from app.schemas.llm\|from app.schemas.global_mail\|from app.schemas.sender_address\|from app.schemas.account" backend/app/
```

Fix any remaining import references.

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove old files replaced by module packages"
```

---

## Task 10: Verify backend starts and all imports resolve

**Step 1: Run the application**

```bash
cd backend && docker compose up --build backend
```

Check logs for:
- "Discovered module: llm (analyser)"
- "Discovered module: email-user (provider)"
- "Discovered module: email-global (provider)"
- No import errors

**Step 2: Test API endpoints respond**

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Modules list
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/modules

# LLM config (admin)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/modules/analysers/llm/config

# User accounts (user)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/providers/email-user/accounts
```

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve import issues from module restructure"
```

---

## Task 11: Create frontend module registry

**Files:**
- Create: `frontend/src/core/moduleRegistry.ts`

**Step 1: Create the registry**

```typescript
import type { RouteRecordRaw } from 'vue-router'

export interface ModuleManifest {
  key: string
  name: string
  type: 'analyser' | 'provider'
  adminRoutes: { path: string; component: () => Promise<any>; label?: string }[]
  userRoutes?: { path: string; component: () => Promise<any>; label: string }[]
}

const modules: ModuleManifest[] = []

export function registerModule(manifest: ModuleManifest) {
  modules.push(manifest)
}

export function getModules(): ModuleManifest[] {
  return modules
}

export function getModulesByType(type: 'analyser' | 'provider'): ModuleManifest[] {
  return modules.filter((m) => m.type === type)
}

export function getAdminRoutes(): RouteRecordRaw[] {
  return modules.flatMap((m) =>
    m.adminRoutes.map((r) => ({
      path: r.path,
      component: r.component,
      meta: { moduleKey: m.key },
    }))
  )
}

export function getUserRoutes(): RouteRecordRaw[] {
  return modules.flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      path: r.path,
      component: r.component,
      meta: { moduleKey: m.key },
    }))
  )
}

export function getAdminSidebarItems(): { group: string; items: { to: string; label: string; moduleKey: string }[] }[] {
  const analysers = getModulesByType('analyser')
  const providers = getModulesByType('provider')

  const groups = []

  if (analysers.length > 0) {
    groups.push({
      group: 'Analysers',
      items: analysers.flatMap((m) =>
        m.adminRoutes.map((r) => ({
          to: `/admin/settings/${r.path}`,
          label: r.label || m.name,
          moduleKey: m.key,
        }))
      ),
    })
  }

  if (providers.length > 0) {
    groups.push({
      group: 'Providers',
      items: providers.flatMap((m) =>
        m.adminRoutes.map((r) => ({
          to: `/admin/settings/${r.path}`,
          label: r.label || m.name,
          moduleKey: m.key,
        }))
      ),
    })
  }

  return groups
}

export function getUserSidebarItems(): { to: string; label: string; moduleKey: string }[] {
  return modules.flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      to: `/providers/${r.path}`,
      label: r.label,
      moduleKey: m.key,
    }))
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/core/moduleRegistry.ts
git commit -m "feat: create frontend module registry"
```

---

## Task 12: Create frontend module manifests and move views/stores

**Files:**
- Create: `frontend/src/modules/analysers/llm/index.ts`
- Move: `frontend/src/views/admin/LLMConfigView.vue` -> `frontend/src/modules/analysers/llm/AdminLLMConfigView.vue`
- Create: `frontend/src/modules/providers/email-global/index.ts`
- Move: `frontend/src/views/admin/GlobalMailConfigView.vue` -> `frontend/src/modules/providers/email-global/AdminGlobalMailView.vue`
- Move: `frontend/src/views/AccountsForwardingView.vue` -> `frontend/src/modules/providers/email-global/UserForwardingView.vue`
- Move: `frontend/src/stores/senderAddresses.ts` -> `frontend/src/modules/providers/email-global/store.ts`
- Create: `frontend/src/modules/providers/email-user/index.ts`
- Move: `frontend/src/views/admin/ImapSettingsView.vue` -> `frontend/src/modules/providers/email-user/AdminImapSettingsView.vue`
- Move: `frontend/src/views/AccountsImapView.vue` -> `frontend/src/modules/providers/email-user/UserImapAccountsView.vue`
- Move: `frontend/src/stores/accounts.ts` -> `frontend/src/modules/providers/email-user/store.ts`

**Step 1: Create directory structure**

```bash
mkdir -p frontend/src/modules/analysers/llm
mkdir -p frontend/src/modules/providers/email-global
mkdir -p frontend/src/modules/providers/email-user
```

**Step 2: Move LLM view and create manifest**

```bash
mv frontend/src/views/admin/LLMConfigView.vue frontend/src/modules/analysers/llm/AdminLLMConfigView.vue
```

Create `frontend/src/modules/analysers/llm/index.ts`:

```typescript
import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'llm',
  name: 'LLM Config',
  type: 'analyser',
  adminRoutes: [
    {
      path: 'llm',
      component: () => import('./AdminLLMConfigView.vue'),
      label: 'LLM Config',
    },
  ],
})
```

**Step 3: Move email-global views/store and create manifest**

```bash
mv frontend/src/views/admin/GlobalMailConfigView.vue frontend/src/modules/providers/email-global/AdminGlobalMailView.vue
mv frontend/src/views/AccountsForwardingView.vue frontend/src/modules/providers/email-global/UserForwardingView.vue
mv frontend/src/stores/senderAddresses.ts frontend/src/modules/providers/email-global/store.ts
```

Update `UserForwardingView.vue` import of `senderAddresses` store to use relative import:
```typescript
import { useSenderAddressesStore } from './store'
```

Update the API paths in `store.ts` to use the new module endpoint:
- `/sender-addresses` -> `/providers/email-global/sender-addresses`

Update the API paths in `AdminGlobalMailView.vue`:
- `/settings/global-mail` -> `/modules/providers/email-global/config`
- `/settings/global-mail/folders` -> `/modules/providers/email-global/folders`

Update the API path in `UserForwardingView.vue`:
- `/settings/global-mail/info` -> `/providers/email-global/info`

Create `frontend/src/modules/providers/email-global/index.ts`:

```typescript
import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-global',
  name: 'Email - Global/Redirect',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-global',
      component: () => import('./AdminGlobalMailView.vue'),
      label: 'Email - Global/Redirect',
    },
  ],
  userRoutes: [
    {
      path: 'email-global',
      component: () => import('./UserForwardingView.vue'),
      label: 'Email Redirect',
    },
  ],
})
```

**Step 4: Move email-user views/store and create manifest**

```bash
mv frontend/src/views/admin/ImapSettingsView.vue frontend/src/modules/providers/email-user/AdminImapSettingsView.vue
mv frontend/src/views/AccountsImapView.vue frontend/src/modules/providers/email-user/UserImapAccountsView.vue
mv frontend/src/stores/accounts.ts frontend/src/modules/providers/email-user/store.ts
```

Update `UserImapAccountsView.vue` import:
```typescript
import { useAccountsStore, type EmailAccount, type IMAPFolder, type WatchedFolder } from './store'
```

Update the API paths in `store.ts`:
- `/accounts` -> `/providers/email-user/accounts`
- `/accounts/${id}` -> `/providers/email-user/accounts/${id}`
- etc.

Create `frontend/src/modules/providers/email-user/index.ts`:

```typescript
import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'email-user',
  name: 'Email - User IMAP',
  type: 'provider',
  adminRoutes: [
    {
      path: 'email-user',
      component: () => import('./AdminImapSettingsView.vue'),
      label: 'Email - User IMAP',
    },
  ],
  userRoutes: [
    {
      path: 'email-user',
      component: () => import('./UserImapAccountsView.vue'),
      label: 'Email IMAP',
    },
  ],
})
```

**Step 5: Commit**

```bash
git add frontend/src/modules/
git commit -m "feat: create frontend module manifests and move views/stores"
```

---

## Task 13: Create ModuleHeader component

**Files:**
- Create: `frontend/src/components/ModuleHeader.vue`

**Step 1: Create the component**

```vue
<template>
  <div class="mb-6">
    <div class="flex items-center justify-between bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg px-5 py-4">
      <div>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{{ name }}</h2>
        <p v-if="description" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{{ description }}</p>
      </div>
      <button
        @click="handleToggle"
        :disabled="toggling"
        class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 disabled:opacity-50"
        :class="enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'"
      >
        <span
          class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
          :class="enabled ? 'translate-x-5' : 'translate-x-0'"
        />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '@/api/client'
import { useModulesStore } from '@/stores/modules'

const props = defineProps<{
  moduleKey: string
  name: string
  description?: string
  enabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:enabled', value: boolean): void
}>()

const modulesStore = useModulesStore()
const toggling = ref(false)

async function handleToggle() {
  toggling.value = true
  try {
    const newValue = !props.enabled
    await api.put(`/modules/${props.moduleKey}`, { enabled: newValue })
    emit('update:enabled', newValue)
    await modulesStore.fetchModules()
  } finally {
    toggling.value = false
  }
}
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/components/ModuleHeader.vue
git commit -m "feat: create ModuleHeader component with on/off toggle"
```

---

## Task 14: Add ModuleHeader to each module view

**Files:**
- Modify: `frontend/src/modules/analysers/llm/AdminLLMConfigView.vue`
- Modify: `frontend/src/modules/providers/email-global/AdminGlobalMailView.vue`
- Modify: `frontend/src/modules/providers/email-user/AdminImapSettingsView.vue`

**Step 1: Add ModuleHeader to each admin view**

For each admin view, add at the top of the template:

```vue
<ModuleHeader
  :module-key="moduleKey"
  :name="moduleName"
  :description="moduleDescription"
  :enabled="moduleEnabled"
  @update:enabled="moduleEnabled = $event"
/>
```

And in the script, add module state from the modules store:

```typescript
import ModuleHeader from '@/components/ModuleHeader.vue'
import { useModulesStore } from '@/stores/modules'

const modulesStore = useModulesStore()
const moduleKey = 'llm' // or 'email-global' or 'email-user'
const moduleName = 'LLM Config'
const moduleDescription = 'Analyse emails using LLM to extract order information'
const moduleEnabled = computed({
  get: () => modulesStore.isEnabled(moduleKey),
  set: () => {}, // handled by ModuleHeader emit
})
```

Wrap the existing form content in a `<div :class="{ 'opacity-50 pointer-events-none': !moduleEnabled }">` to grey out when disabled.

**Step 2: Commit**

```bash
git add frontend/src/modules/
git commit -m "feat: add ModuleHeader with enable/disable toggle to all module admin views"
```

---

## Task 15: Update router to use module registry

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: Import module registrations and build routes dynamically**

```typescript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getAdminRoutes, getUserRoutes } from '@/core/moduleRegistry'

// Import module manifests to trigger registration
import '@/modules/analysers/llm'
import '@/modules/providers/email-global'
import '@/modules/providers/email-user'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/dashboard' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { guest: true },
      beforeEnter: async () => {
        const auth = useAuthStore()
        if (auth.setupCompleted === null) {
          await auth.checkStatus()
        }
      },
    },
    { path: '/setup', redirect: '/login' },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/orders',
      name: 'orders',
      component: () => import('@/views/OrdersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/orders/:id',
      name: 'order-detail',
      component: () => import('@/views/OrderDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('@/views/HistoryView.vue'),
      meta: { requiresAuth: true },
    },
    // Provider user routes (dynamically from modules)
    {
      path: '/providers',
      meta: { requiresAuth: true },
      children: getUserRoutes(),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
    // Legacy redirects
    { path: '/accounts', redirect: '/providers/email-user' },
    { path: '/accounts/imap', redirect: '/providers/email-user' },
    { path: '/accounts/forwarding', redirect: '/providers/email-global' },
    { path: '/admin/llm', redirect: '/admin/settings/llm' },
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/settings',
      component: () => import('@/views/admin/SettingsView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
      children: [
        { path: '', redirect: '/admin/settings/queue' },
        {
          path: 'queue',
          name: 'queue-settings',
          component: () => import('@/views/admin/QueueSettingsView.vue'),
        },
        // Module admin routes (dynamically from modules)
        ...getAdminRoutes(),
      ],
    },
    {
      path: '/admin/system',
      name: 'admin-system',
      component: () => import('@/views/admin/SystemView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.isLoggedIn && !auth.user) {
    await auth.fetchUser()
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login' }
  }
  if (to.meta.guest && auth.isLoggedIn) {
    return { name: 'dashboard' }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'dashboard' }
  }
})

export default router
```

**Step 2: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: update router to use dynamic module routes"
```

---

## Task 16: Update admin SettingsView with collapsible groups

**Files:**
- Modify: `frontend/src/views/admin/SettingsView.vue`

**Step 1: Rewrite SettingsView to use collapsible groups**

```vue
<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('settings.title') }}
    </h1>

    <div class="flex flex-col sm:flex-row gap-6">
      <!-- Vertical Tab Nav with Collapsible Groups -->
      <nav class="sm:w-52 flex-shrink-0">
        <div class="flex sm:flex-col gap-1">
          <!-- Queue (core, always visible) -->
          <router-link
            to="/admin/settings/queue"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="isActive('/admin/settings/queue')
              ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          >
            {{ $t('settings.queue') }}
          </router-link>

          <!-- Module Groups -->
          <template v-for="group in sidebarGroups" :key="group.group">
            <button
              @click="toggleGroup(group.group)"
              class="flex items-center justify-between w-full px-3 py-2 mt-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300"
            >
              {{ group.group }}
              <svg
                class="w-3.5 h-3.5 transition-transform duration-200"
                :class="{ 'rotate-180': !collapsedGroups[group.group] }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <template v-if="!collapsedGroups[group.group]">
              <router-link
                v-for="item in group.items"
                :key="item.to"
                :to="item.to"
                class="px-3 py-2 pl-5 text-sm font-medium rounded-lg transition-colors whitespace-nowrap block"
                :class="isActive(item.to)
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
              >
                {{ item.label }}
              </router-link>
            </template>
          </template>
        </div>
      </nav>

      <!-- Tab Content -->
      <div class="flex-1 min-w-0">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getAdminSidebarItems } from '@/core/moduleRegistry'

const { t } = useI18n()
const route = useRoute()

const sidebarGroups = getAdminSidebarItems()

const collapsedGroups = reactive<Record<string, boolean>>({})

function toggleGroup(group: string) {
  collapsedGroups[group] = !collapsedGroups[group]
}

function isActive(path: string): boolean {
  return route.path === path
}
</script>
```

**Step 2: Commit**

```bash
git add frontend/src/views/admin/SettingsView.vue
git commit -m "feat: update admin settings sidebar with collapsible module groups"
```

---

## Task 17: Update AppLayout with collapsible Providers section

**Files:**
- Modify: `frontend/src/components/AppLayout.vue`

**Step 1: Update user sidebar navigation**

Replace the conditional email accounts nav item with a collapsible "Providers" section populated from the module registry:

In the script, add:
```typescript
import { getUserSidebarItems } from '@/core/moduleRegistry'

const providerItems = computed(() => {
  return getUserSidebarItems().filter(item =>
    modulesStore.isEnabled(item.moduleKey)
  )
})

const providersExpanded = ref(true)
```

In the template, replace the old accounts nav item with:

```vue
<!-- Providers Section -->
<template v-if="providerItems.length > 0">
  <button
    @click="providersExpanded = !providersExpanded"
    class="flex items-center justify-between w-full px-3 py-2 mt-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300"
  >
    {{ $t('nav.providers') }}
    <svg
      class="w-3.5 h-3.5 transition-transform duration-200"
      :class="{ 'rotate-180': !providersExpanded }"
      fill="none" stroke="currentColor" viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
    </svg>
  </button>
  <template v-if="providersExpanded">
    <router-link
      v-for="item in providerItems"
      :key="item.to"
      :to="item.to"
      class="flex items-center gap-3 px-3 py-2.5 pl-6 text-sm font-medium rounded-lg transition-colors"
      :class="isActive(item.to)
        ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
      @click="sidebarOpen = false"
    >
      {{ item.label }}
    </router-link>
  </template>
</template>
```

Update `isActive()` to handle provider paths:
```typescript
function isActive(path: string): boolean {
  if (path === '/orders' && route.path.startsWith('/orders/')) return true
  if (path === '/admin/settings' && route.path.startsWith('/admin/settings')) return true
  if (path.startsWith('/providers/') && route.path === path) return true
  return route.path === path
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/AppLayout.vue
git commit -m "feat: update user sidebar with collapsible Providers section from module registry"
```

---

## Task 18: Delete old frontend files

**Files:**
- Delete: `frontend/src/views/admin/ModulesView.vue`
- Delete: `frontend/src/views/AccountsView.vue`

**Step 1: Delete the files**

```bash
rm frontend/src/views/admin/ModulesView.vue
rm frontend/src/views/AccountsView.vue
```

**Step 2: Search for remaining references**

```bash
grep -r "ModulesView\|AccountsView\|accounts/imap\|accounts/forwarding\|senderAddresses\|@/stores/accounts" frontend/src/
```

Fix any remaining import references. Key places to check:
- `router/index.ts` — should already be updated, but verify no old routes remain
- Any component importing from `@/stores/accounts` should import from `@/modules/providers/email-user/store`
- Any component importing from `@/stores/senderAddresses` should import from `@/modules/providers/email-global/store`

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove old frontend files replaced by module structure"
```

---

## Task 19: Update i18n translations

**Files:**
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Add new translation keys**

Add to both locale files:

```json
{
  "nav": {
    "providers": "Providers"
  },
  "modules": {
    "llm": {
      "title": "LLM Analyser",
      "description": "Analyse emails using LLM to extract order information"
    },
    "email-global": {
      "title": "Email - Global/Redirect",
      "description": "Shared global email inbox with sender-based routing"
    },
    "email-user": {
      "title": "Email - User IMAP",
      "description": "Allow users to connect their own IMAP email accounts"
    }
  }
}
```

German translations for `de.json`:
```json
{
  "nav": {
    "providers": "Anbieter"
  },
  "modules": {
    "llm": {
      "title": "LLM Analyse",
      "description": "E-Mails mit LLM analysieren, um Bestellinformationen zu extrahieren"
    },
    "email-global": {
      "title": "E-Mail - Global/Weiterleitung",
      "description": "Gemeinsames globales E-Mail-Postfach mit absenderbasierter Zuordnung"
    },
    "email-user": {
      "title": "E-Mail - Benutzer IMAP",
      "description": "Benutzern erlauben, eigene IMAP-E-Mail-Konten zu verbinden"
    }
  }
}
```

Remove the old `settings.modules` key since the Modules tab no longer exists.

**Step 2: Commit**

```bash
git add frontend/src/i18n/
git commit -m "feat: update translations for modular architecture"
```

---

## Task 20: Update modules store to include metadata

**Files:**
- Modify: `frontend/src/stores/modules.ts`

**Step 1: Update the Module interface**

The backend now returns `name`, `type`, and `description` with each module. Update the store:

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

interface Module {
  module_key: string
  enabled: boolean
  name: string | null
  type: string | null
  description: string | null
}

export const useModulesStore = defineStore('modules', () => {
  const modules = ref<Module[]>([])
  const loaded = ref(false)

  const isEnabled = computed(() => (key: string) => {
    const m = modules.value.find((mod) => mod.module_key === key)
    return m?.enabled ?? false
  })

  function getModule(key: string): Module | undefined {
    return modules.value.find((mod) => mod.module_key === key)
  }

  async function fetchModules() {
    const res = await api.get('/modules')
    modules.value = res.data
    loaded.value = true
  }

  return { modules, loaded, isEnabled, getModule, fetchModules }
})
```

**Step 2: Commit**

```bash
git add frontend/src/stores/modules.ts
git commit -m "feat: update modules store to include name/type/description metadata"
```

---

## Task 21: End-to-end verification

**Step 1: Build frontend**

```bash
cd frontend && npm run build
```

Fix any TypeScript or build errors.

**Step 2: Start full stack**

```bash
docker compose up --build
```

**Step 3: Manual verification checklist**

- [ ] Login works
- [ ] Admin Settings sidebar shows: Queue, collapsible Analysers (LLM Config), collapsible Providers (Email - Global/Redirect, Email - User IMAP)
- [ ] Each module admin page has ModuleHeader with on/off toggle
- [ ] Toggling a module off greys out the form
- [ ] Toggling a module on/off starts/stops the watcher (check backend logs)
- [ ] User sidebar shows collapsible Providers with enabled modules
- [ ] User can configure IMAP accounts at `/providers/email-user`
- [ ] User can configure forwarding at `/providers/email-global`
- [ ] Queue processing still works (submit an email, see it processed)
- [ ] `/api/v1/modules` returns all modules with metadata
- [ ] Legacy redirects work (`/accounts` -> `/providers/email-user`)

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve end-to-end issues from modular architecture migration"
```

---

## Task 22: Run tests and fix failures

**Step 1: Run backend tests**

```bash
cd backend && pytest tests/ -v
```

**Step 2: Fix import paths in tests**

Tests may import from old paths. Update imports to use new module paths:
- `app.models.llm_config` -> `app.modules.analysers.llm.models`
- `app.models.email_account` -> `app.modules.providers.email_user.models`
- `app.models.global_mail_config` -> `app.modules.providers.email_global.models`
- `app.services.llm_service` -> `app.modules.analysers.llm.service`
- `app.services.imap_worker` -> `app.modules.providers.email_user.service` / `app.modules.providers.email_global.service`
- API endpoint paths in tests need updating to match new prefixes

**Step 3: Run frontend checks**

```bash
cd frontend && npm run type-check && npm run lint
```

**Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: update tests and lint for modular architecture"
```
