from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ModuleInfo:
    """Manifest that every module must provide as MODULE_INFO."""
    key: str
    name: str
    type: str  # "analyser", "provider", or "notifier"
    version: str
    description: str
    router: APIRouter
    models: list[Any] = field(default_factory=list)
    user_router: APIRouter | None = None
    startup: Callable[[], Awaitable[None]] | None = None
    shutdown: Callable[[], Awaitable[None]] | None = None
    is_configured: Callable[[], Awaitable[bool]] | None = None
    status: Callable[[AsyncSession], Awaitable[dict | None]] | None = None
    notify: Callable[[int, str, dict, dict | None, AsyncSession], Awaitable[None]] | None = None
