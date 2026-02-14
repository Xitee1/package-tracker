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
