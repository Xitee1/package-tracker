# Notification System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a two-layer notification system — core SMTP infrastructure for app-level emails, plus pluggable notifier modules (email, webhook) for user-facing notification channels.

**Architecture:** Core SMTP config is a singleton admin setting (like LLMConfig). Notifier modules are a new module type (`"notifier"`) auto-discovered from `app/modules/notifiers/`. A unified `notify_user()` dispatch function iterates enabled notifier modules and sends based on user preferences. Integration point is `queue_worker.py` after order creation/update.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, aiosmtplib, Vue 3 Composition API, Pinia, Tailwind CSS 4, vue-i18n

**Design doc:** `docs/plans/2026-02-15-notifications-design.md`

---

### Task 1: Core SMTP Model & Service

**Files:**
- Create: `backend/app/models/smtp_config.py`
- Create: `backend/app/services/email_service.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/smtp.py`
- Test: `backend/tests/test_smtp.py`

**Step 1: Create SmtpConfig model**

Create `backend/app/models/smtp_config.py`:

```python
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=587)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[str] = mapped_column(String(1024), nullable=True)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    sender_address: Mapped[str] = mapped_column(String(320))
    sender_name: Mapped[str] = mapped_column(String(255), default="Package Tracker")
```

**Step 2: Create SMTP schemas**

Create `backend/app/schemas/smtp.py`:

```python
from typing import Optional
from pydantic import BaseModel, EmailStr


class SmtpConfigRequest(BaseModel):
    host: str
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    sender_address: EmailStr
    sender_name: str = "Package Tracker"


class SmtpConfigResponse(BaseModel):
    id: int
    host: str
    port: int
    username: Optional[str] = None
    use_tls: bool
    sender_address: str
    sender_name: str

    model_config = {"from_attributes": True}


class SmtpTestRequest(BaseModel):
    recipient: EmailStr
```

**Step 3: Create email service**

Create `backend/app/services/email_service.py`:

```python
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.smtp_config import SmtpConfig

logger = logging.getLogger(__name__)


async def get_smtp_config(db: AsyncSession) -> SmtpConfig | None:
    result = await db.execute(select(SmtpConfig))
    return result.scalar_one_or_none()


async def is_smtp_configured(db: AsyncSession) -> bool:
    return await get_smtp_config(db) is not None


async def send_email(
    to: str,
    subject: str,
    html_body: str,
    db: AsyncSession,
) -> None:
    """Send an email using the configured SMTP settings."""
    config = await get_smtp_config(db)
    if not config:
        raise RuntimeError("SMTP is not configured")

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{config.sender_name} <{config.sender_address}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    password = decrypt_value(config.password_encrypted) if config.password_encrypted else None

    await aiosmtplib.send(
        msg,
        hostname=config.host,
        port=config.port,
        username=config.username,
        password=password,
        use_tls=config.use_tls,
        start_tls=not config.use_tls,
    )
    logger.info(f"Email sent to {to}: {subject}")
```

**Step 4: Register model in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.smtp_config import SmtpConfig
```

And add `"SmtpConfig"` to `__all__`.

**Step 5: Add aiosmtplib dependency**

Run: `cd backend && pip install aiosmtplib` and add `aiosmtplib` to the project's dependencies in `pyproject.toml`.

**Step 6: Write tests for email service**

Create `backend/tests/test_smtp.py`:

```python
import pytest
from httpx import AsyncClient

from app.models.smtp_config import SmtpConfig
from app.core.encryption import encrypt_value


async def _create_admin_token(client: AsyncClient) -> str:
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_get_smtp_config_empty(client: AsyncClient):
    token = await _create_admin_token(client)
    resp = await client.get("/api/v1/admin/smtp", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_save_smtp_config(client: AsyncClient):
    token = await _create_admin_token(client)
    resp = await client.put(
        "/api/v1/admin/smtp",
        json={
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": True,
            "sender_address": "noreply@example.com",
            "sender_name": "Package Tracker",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["host"] == "smtp.example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_smtp_requires_admin(client: AsyncClient):
    # Create admin and a regular user
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "password123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "password123"})
    admin_token = resp.json()["access_token"]

    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "password123"})
    user_token = resp.json()["access_token"]

    resp = await client.get("/api/v1/admin/smtp", headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403
```

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_smtp.py -v`

**Step 8: Commit**

```bash
git add backend/app/models/smtp_config.py backend/app/services/email_service.py backend/app/schemas/smtp.py backend/tests/test_smtp.py
git commit -m "feat: add core SMTP model and email service"
```

---

### Task 2: SMTP Admin API Endpoints

**Files:**
- Create: `backend/app/api/smtp.py`
- Modify: `backend/app/main.py` (add router)

**Step 1: Create SMTP admin router**

Create `backend/app/api/smtp.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.encryption import encrypt_value
from app.database import get_db
from app.models.smtp_config import SmtpConfig
from app.schemas.smtp import SmtpConfigRequest, SmtpConfigResponse, SmtpTestRequest
from app.services.email_service import send_email

router = APIRouter(prefix="/api/v1/admin/smtp", tags=["smtp"], dependencies=[Depends(get_admin_user)])


async def _get_config(db: AsyncSession) -> SmtpConfig | None:
    result = await db.execute(select(SmtpConfig))
    return result.scalar_one_or_none()


@router.get("", response_model=SmtpConfigResponse | None)
async def get_smtp_config(db: AsyncSession = Depends(get_db)):
    return await _get_config(db)


@router.put("", response_model=SmtpConfigResponse)
async def save_smtp_config(req: SmtpConfigRequest, db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if not config:
        config = SmtpConfig(
            host=req.host,
            port=req.port,
            username=req.username,
            password_encrypted=encrypt_value(req.password) if req.password else None,
            use_tls=req.use_tls,
            sender_address=req.sender_address,
            sender_name=req.sender_name,
        )
        db.add(config)
    else:
        config.host = req.host
        config.port = req.port
        config.username = req.username
        if req.password:
            config.password_encrypted = encrypt_value(req.password)
        config.use_tls = req.use_tls
        config.sender_address = req.sender_address
        config.sender_name = req.sender_name
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/test")
async def test_smtp(req: SmtpTestRequest, db: AsyncSession = Depends(get_db)):
    try:
        await send_email(
            to=req.recipient,
            subject="Package Tracker — SMTP Test",
            html_body="<p>This is a test email from Package Tracker. If you received this, SMTP is configured correctly.</p>",
            db=db,
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

**Step 2: Register SMTP router in main.py**

Add after existing core router imports in `backend/app/main.py`:

```python
from app.api.smtp import router as smtp_router
app.include_router(smtp_router)
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_smtp.py -v`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add backend/app/api/smtp.py backend/app/main.py
git commit -m "feat: add SMTP admin API endpoints"
```

---

### Task 3: Expand Module System for Notifier Type

**Files:**
- Modify: `backend/app/core/module_base.py`
- Modify: `backend/app/core/module_registry.py`
- Modify: `frontend/src/core/moduleRegistry.ts`

**Step 1: Update ModuleInfo type field docstring**

In `backend/app/core/module_base.py`, update the `type` field comment:

```python
type: str  # "analyser", "provider", or "notifier"
```

**Step 2: Add notifier discovery to module_registry.py**

In `backend/app/core/module_registry.py`, update the `discover_modules()` function to scan `notifiers/` too:

```python
for module_type in ("analysers", "providers", "notifiers"):
```

**Step 3: Update frontend ModuleManifest type**

In `frontend/src/core/moduleRegistry.ts`, update the `type` field:

```typescript
type: 'analyser' | 'provider' | 'notifier'
```

**Step 4: Add notifier groups to admin sidebar**

In `frontend/src/core/moduleRegistry.ts`, add to `getAdminSidebarItems()` — after the providers block:

```typescript
const notifiers = getModulesByType('notifier')

// ... existing analyser/provider groups ...

if (notifiers.length > 0) {
  groups.push({
    group: 'notifier',
    items: notifiers.flatMap((m) =>
      m.adminRoutes.map((r) => ({
        to: `/admin/settings/${r.path}`,
        label: r.label || m.name,
        moduleKey: m.key,
      })),
    ),
  })
}
```

**Step 5: Add notifier user sidebar items function**

In `frontend/src/core/moduleRegistry.ts`, add a new function:

```typescript
export function getNotifierSidebarItems(): { to: string; label: string; moduleKey: string }[] {
  return getModulesByType('notifier').flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      to: `/notifications/${r.path}`,
      label: r.label,
      moduleKey: m.key,
    })),
  )
}
```

**Step 6: Add notifier user routes function**

In `frontend/src/core/moduleRegistry.ts`, add:

```typescript
export function getNotifierUserRoutes(): RouteRecordRaw[] {
  return getModulesByType('notifier').flatMap((m) =>
    (m.userRoutes || []).map((r) => ({
      path: r.path,
      component: r.component,
      meta: { moduleKey: m.key },
    })),
  )
}
```

**Step 7: Add "notifier" to moduleType i18n**

In `frontend/src/i18n/locales/en.json`, inside `system.moduleType`:

```json
"notifier": "Notifier"
```

In `frontend/src/i18n/locales/de.json`, inside `system.moduleType`:

```json
"notifier": "Benachrichtigung"
```

**Step 8: Commit**

```bash
git add backend/app/core/module_base.py backend/app/core/module_registry.py frontend/src/core/moduleRegistry.ts frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: expand module system to support notifier type"
```

---

### Task 4: Notification Data Models

**Files:**
- Create: `backend/app/models/notification.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create notification models**

Create `backend/app/models/notification.py`:

```python
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON

from app.database import Base


class UserNotificationConfig(Base):
    __tablename__ = "user_notification_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    module_key: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    events: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    # Unique constraint added via Alembic migration


class EmailVerification(Base):
    __tablename__ = "email_verification"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(320))
    token: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column()
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
```

**Step 2: Register models in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.notification import UserNotificationConfig, EmailVerification
```

And add `"UserNotificationConfig", "EmailVerification"` to `__all__`.

**Step 3: Commit**

```bash
git add backend/app/models/notification.py backend/app/models/__init__.py
git commit -m "feat: add UserNotificationConfig and EmailVerification models"
```

---

### Task 5: Notification Events & Dispatch Service

**Files:**
- Create: `backend/app/services/notification_service.py`
- Test: `backend/tests/test_notifications.py`

**Step 1: Create notification service**

Create `backend/app/services/notification_service.py`:

```python
import enum
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.module_registry import get_modules_by_type
from app.database import async_session
from app.models.module_config import ModuleConfig
from app.models.notification import UserNotificationConfig

logger = logging.getLogger(__name__)


class NotificationEvent(str, enum.Enum):
    NEW_ORDER = "new_order"
    TRACKING_UPDATE = "tracking_update"
    PACKAGE_DELIVERED = "package_delivered"


async def notify_user(
    user_id: int,
    event_type: NotificationEvent,
    event_data: dict,
) -> None:
    """Send notifications to a user via all their enabled notification channels."""
    notifier_modules = get_modules_by_type("notifier")
    if not notifier_modules:
        return

    async with async_session() as db:
        # Get enabled notifier module keys
        result = await db.execute(
            select(ModuleConfig).where(
                ModuleConfig.module_key.in_(notifier_modules.keys()),
                ModuleConfig.enabled == True,
            )
        )
        enabled_keys = {m.module_key for m in result.scalars().all()}

        if not enabled_keys:
            return

        # Get user's notification configs
        result = await db.execute(
            select(UserNotificationConfig).where(
                UserNotificationConfig.user_id == user_id,
                UserNotificationConfig.module_key.in_(enabled_keys),
                UserNotificationConfig.enabled == True,
            )
        )
        user_configs = result.scalars().all()

        for config in user_configs:
            # Check if user subscribed to this event
            if config.events and event_type.value not in config.events:
                continue

            module_info = notifier_modules.get(config.module_key)
            if not module_info or not module_info.notify:
                continue

            try:
                await module_info.notify(user_id, event_type.value, event_data, config.config, db)
                logger.info(f"Notification sent via {config.module_key} to user {user_id} for {event_type.value}")
            except Exception as e:
                logger.error(f"Failed to send notification via {config.module_key} to user {user_id}: {e}")
```

**Step 2: Add `notify` field to ModuleInfo**

In `backend/app/core/module_base.py`, add after the `status` field:

```python
notify: Callable[[int, str, dict, dict | None, AsyncSession], Awaitable[None]] | None = None
```

This requires adding `AsyncSession` import (already present) and updating the existing import line — just check it has `Callable, Awaitable, Any`.

**Step 3: Write basic test**

Create `backend/tests/test_notifications.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch

from app.services.notification_service import notify_user, NotificationEvent


@pytest.mark.asyncio
async def test_notify_user_no_modules():
    """Should do nothing when no notifier modules exist."""
    with patch("app.services.notification_service.get_modules_by_type", return_value={}):
        await notify_user(1, NotificationEvent.NEW_ORDER, {"order_id": 1})
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_notifications.py -v`

**Step 5: Commit**

```bash
git add backend/app/services/notification_service.py backend/app/core/module_base.py backend/tests/test_notifications.py
git commit -m "feat: add notification dispatch service and event types"
```

---

### Task 6: Email Notifier Module (Backend)

**Files:**
- Create: `backend/app/modules/notifiers/__init__.py` (empty)
- Create: `backend/app/modules/notifiers/notify_email/__init__.py`
- Create: `backend/app/modules/notifiers/notify_email/router.py`
- Create: `backend/app/modules/notifiers/notify_email/user_router.py`
- Create: `backend/app/modules/notifiers/notify_email/schemas.py`
- Create: `backend/app/modules/notifiers/notify_email/service.py`

**Step 1: Create empty `__init__.py` for notifiers package**

Create `backend/app/modules/notifiers/__init__.py` (empty file).

**Step 2: Create email notifier service**

Create `backend/app/modules/notifiers/notify_email/service.py`:

```python
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import send_email

logger = logging.getLogger(__name__)

EVENT_LABELS = {
    "new_order": "New Order",
    "tracking_update": "Tracking Update",
    "package_delivered": "Package Delivered",
}


async def send_notification(
    user_id: int,
    event_type: str,
    event_data: dict,
    user_config: dict | None,
    db: AsyncSession,
) -> None:
    """Send an email notification to the user."""
    if not user_config or not user_config.get("email"):
        return
    if not user_config.get("verified"):
        return

    email = user_config["email"]
    event_label = EVENT_LABELS.get(event_type, event_type)

    vendor = event_data.get("vendor_name", "Unknown")
    order_number = event_data.get("order_number", "N/A")
    status = event_data.get("status", "")
    items_list = event_data.get("items", [])

    items_html = ""
    if items_list:
        items_html = "<ul>" + "".join(f"<li>{item}</li>" for item in items_list) + "</ul>"

    html_body = f"""
    <div style="font-family: sans-serif; max-width: 600px;">
        <h2>Package Tracker — {event_label}</h2>
        <p><strong>Vendor:</strong> {vendor}</p>
        <p><strong>Order:</strong> {order_number}</p>
        <p><strong>Status:</strong> {status}</p>
        {items_html}
    </div>
    """

    await send_email(
        to=email,
        subject=f"Package Tracker: {event_label} — {vendor}",
        html_body=html_body,
        db=db,
    )
```

**Step 3: Create email notifier schemas**

Create `backend/app/modules/notifiers/notify_email/schemas.py`:

```python
from typing import Optional
from pydantic import BaseModel, EmailStr


class NotifyEmailConfigRequest(BaseModel):
    email: EmailStr


class NotifyEmailConfigResponse(BaseModel):
    enabled: bool
    email: Optional[str] = None
    verified: bool = False
    events: list[str] = []

    model_config = {"from_attributes": True}


class NotifyEmailEventsRequest(BaseModel):
    events: list[str]


class NotifyEmailToggleRequest(BaseModel):
    enabled: bool
```

**Step 4: Create admin router**

Create `backend/app/modules/notifiers/notify_email/router.py`:

```python
from fastapi import APIRouter, Depends

from app.api.deps import get_admin_user

router = APIRouter(tags=["notify-email"], dependencies=[Depends(get_admin_user)])


@router.get("/info")
async def get_info():
    return {"message": "Email notification module. Requires core SMTP to be configured."}
```

**Step 5: Create user router**

Create `backend/app/modules/notifiers/notify_email/user_router.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.notification import UserNotificationConfig, EmailVerification
from app.services.email_service import send_email, is_smtp_configured
from app.modules.notifiers.notify_email.schemas import (
    NotifyEmailConfigRequest,
    NotifyEmailConfigResponse,
    NotifyEmailEventsRequest,
    NotifyEmailToggleRequest,
)

user_router = APIRouter(tags=["notify-email"])


async def _get_user_config(user_id: int, db: AsyncSession) -> UserNotificationConfig | None:
    result = await db.execute(
        select(UserNotificationConfig).where(
            UserNotificationConfig.user_id == user_id,
            UserNotificationConfig.module_key == "notify-email",
        )
    )
    return result.scalar_one_or_none()


@user_router.get("/config", response_model=NotifyEmailConfigResponse)
async def get_config(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        return NotifyEmailConfigResponse(enabled=False)

    email = config.config.get("email") if config.config else None
    verified = config.config.get("verified", False) if config.config else False
    return NotifyEmailConfigResponse(
        enabled=config.enabled,
        email=email,
        verified=verified,
        events=config.events or [],
    )


@user_router.post("/config/email")
async def set_email(
    req: NotifyEmailConfigRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await is_smtp_configured(db):
        raise HTTPException(status_code=400, detail="SMTP is not configured")

    config = await _get_user_config(user.id, db)
    if not config:
        config = UserNotificationConfig(
            user_id=user.id,
            module_key="notify-email",
            enabled=False,
            config={"email": req.email, "verified": False},
            events=[],
        )
        db.add(config)
    else:
        config.config = {"email": req.email, "verified": False}

    # Create verification token
    token = str(uuid.uuid4())
    verification = EmailVerification(
        user_id=user.id,
        email=req.email,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification)
    await db.commit()

    # Send verification email
    # Note: frontend_url would ideally come from config, using a relative path for now
    verify_link = f"/verify-email/{token}"
    await send_email(
        to=req.email,
        subject="Package Tracker — Verify your email",
        html_body=f"""
        <div style="font-family: sans-serif; max-width: 600px;">
            <h2>Verify your email address</h2>
            <p>Click the link below to verify your email for Package Tracker notifications:</p>
            <p><a href="{verify_link}">{verify_link}</a></p>
            <p>This link expires in 24 hours.</p>
        </div>
        """,
        db=db,
    )

    return {"status": "verification_sent"}


@user_router.post("/verify/{token}")
async def verify_email(token: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == token,
            EmailVerification.user_id == user.id,
        )
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    now = datetime.now(timezone.utc)
    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=400, detail="Verification link expired")

    if verification.verified_at:
        raise HTTPException(status_code=400, detail="Already verified")

    verification.verified_at = now

    # Update user config
    config = await _get_user_config(user.id, db)
    if config:
        config.config = {"email": verification.email, "verified": True}
    await db.commit()

    return {"status": "verified", "email": verification.email}


@user_router.put("/config/toggle")
async def toggle_notifications(
    req: NotifyEmailToggleRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure email first")
    if req.enabled and (not config.config or not config.config.get("verified")):
        raise HTTPException(status_code=400, detail="Email not verified")
    config.enabled = req.enabled
    await db.commit()
    return {"status": "ok", "enabled": config.enabled}


@user_router.put("/config/events")
async def update_events(
    req: NotifyEmailEventsRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure email first")
    config.events = req.events
    await db.commit()
    return {"status": "ok", "events": config.events}
```

**Step 6: Create module manifest**

Create `backend/app/modules/notifiers/notify_email/__init__.py`:

```python
from app.core.module_base import ModuleInfo
from app.modules.notifiers.notify_email.router import router
from app.modules.notifiers.notify_email.user_router import user_router
from app.modules.notifiers.notify_email.service import send_notification
from app.services.email_service import is_smtp_configured
from app.database import async_session


async def check_configured() -> bool:
    async with async_session() as db:
        return await is_smtp_configured(db)


MODULE_INFO = ModuleInfo(
    key="notify-email",
    name="Email Notifications",
    type="notifier",
    version="1.0.0",
    description="Send email notifications for order events",
    router=router,
    user_router=user_router,
    models=[],
    is_configured=check_configured,
    notify=send_notification,
)
```

**Step 7: Commit**

```bash
git add backend/app/modules/notifiers/
git commit -m "feat: add email notifier module"
```

---

### Task 7: Webhook Notifier Module (Backend)

**Files:**
- Create: `backend/app/modules/notifiers/notify_webhook/__init__.py`
- Create: `backend/app/modules/notifiers/notify_webhook/router.py`
- Create: `backend/app/modules/notifiers/notify_webhook/user_router.py`
- Create: `backend/app/modules/notifiers/notify_webhook/schemas.py`
- Create: `backend/app/modules/notifiers/notify_webhook/service.py`

**Step 1: Create webhook service**

Create `backend/app/modules/notifiers/notify_webhook/service.py`:

```python
import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def send_notification(
    user_id: int,
    event_type: str,
    event_data: dict,
    user_config: dict | None,
    db: AsyncSession,
) -> None:
    """Send a webhook notification."""
    if not user_config or not user_config.get("url"):
        return

    url = user_config["url"]
    headers = {"Content-Type": "application/json"}
    if user_config.get("auth_header"):
        headers["Authorization"] = user_config["auth_header"]

    payload = {
        "event": event_type,
        "data": event_data,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        logger.info(f"Webhook sent to {url} for user {user_id}, status {resp.status_code}")
```

**Step 2: Create webhook schemas**

Create `backend/app/modules/notifiers/notify_webhook/schemas.py`:

```python
from typing import Optional
from pydantic import BaseModel, HttpUrl


class WebhookConfigRequest(BaseModel):
    url: HttpUrl
    auth_header: Optional[str] = None


class WebhookConfigResponse(BaseModel):
    enabled: bool
    url: Optional[str] = None
    has_auth_header: bool = False
    events: list[str] = []


class WebhookEventsRequest(BaseModel):
    events: list[str]


class WebhookToggleRequest(BaseModel):
    enabled: bool


class WebhookTestRequest(BaseModel):
    url: HttpUrl
    auth_header: Optional[str] = None
```

**Step 3: Create admin router**

Create `backend/app/modules/notifiers/notify_webhook/router.py`:

```python
from fastapi import APIRouter, Depends

from app.api.deps import get_admin_user

router = APIRouter(tags=["notify-webhook"], dependencies=[Depends(get_admin_user)])


@router.get("/info")
async def get_info():
    return {"message": "Webhook notification module. No admin configuration required."}
```

**Step 4: Create user router**

Create `backend/app/modules/notifiers/notify_webhook/user_router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.notification import UserNotificationConfig
from app.modules.notifiers.notify_webhook.schemas import (
    WebhookConfigRequest,
    WebhookConfigResponse,
    WebhookEventsRequest,
    WebhookToggleRequest,
    WebhookTestRequest,
)

user_router = APIRouter(tags=["notify-webhook"])


async def _get_user_config(user_id: int, db: AsyncSession) -> UserNotificationConfig | None:
    result = await db.execute(
        select(UserNotificationConfig).where(
            UserNotificationConfig.user_id == user_id,
            UserNotificationConfig.module_key == "notify-webhook",
        )
    )
    return result.scalar_one_or_none()


@user_router.get("/config", response_model=WebhookConfigResponse)
async def get_config(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    config = await _get_user_config(user.id, db)
    if not config:
        return WebhookConfigResponse(enabled=False)
    return WebhookConfigResponse(
        enabled=config.enabled,
        url=config.config.get("url") if config.config else None,
        has_auth_header=bool(config.config.get("auth_header_encrypted")) if config.config else False,
        events=config.events or [],
    )


@user_router.put("/config/webhook")
async def set_webhook(
    req: WebhookConfigRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_user_config(user.id, db)
    config_data = {"url": str(req.url)}
    if req.auth_header:
        config_data["auth_header_encrypted"] = encrypt_value(req.auth_header)

    if not config:
        config = UserNotificationConfig(
            user_id=user.id,
            module_key="notify-webhook",
            enabled=False,
            config=config_data,
            events=[],
        )
        db.add(config)
    else:
        config.config = config_data
    await db.commit()
    return {"status": "ok"}


@user_router.put("/config/toggle")
async def toggle_notifications(
    req: WebhookToggleRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_user_config(user.id, db)
    if not config or not config.config or not config.config.get("url"):
        raise HTTPException(status_code=400, detail="Configure webhook URL first")
    config.enabled = req.enabled
    await db.commit()
    return {"status": "ok", "enabled": config.enabled}


@user_router.put("/config/events")
async def update_events(
    req: WebhookEventsRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_user_config(user.id, db)
    if not config:
        raise HTTPException(status_code=400, detail="Configure webhook first")
    config.events = req.events
    await db.commit()
    return {"status": "ok", "events": config.events}


@user_router.post("/test")
async def test_webhook(
    req: WebhookTestRequest,
    user=Depends(get_current_user),
):
    headers = {"Content-Type": "application/json"}
    if req.auth_header:
        headers["Authorization"] = req.auth_header

    payload = {
        "event": "test",
        "data": {"message": "This is a test notification from Package Tracker."},
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(str(req.url), json=payload, headers=headers)
        return {"status": "ok", "response_code": resp.status_code}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
```

**Step 5: Update webhook service to decrypt auth header**

The `send_notification` in `service.py` needs to decrypt the auth header since it's stored encrypted. Update `backend/app/modules/notifiers/notify_webhook/service.py`:

Replace `if user_config.get("auth_header"):` block with:

```python
    if user_config.get("auth_header_encrypted"):
        from app.core.encryption import decrypt_value
        headers["Authorization"] = decrypt_value(user_config["auth_header_encrypted"])
```

**Step 6: Create module manifest**

Create `backend/app/modules/notifiers/notify_webhook/__init__.py`:

```python
from app.core.module_base import ModuleInfo
from app.modules.notifiers.notify_webhook.router import router
from app.modules.notifiers.notify_webhook.user_router import user_router
from app.modules.notifiers.notify_webhook.service import send_notification


MODULE_INFO = ModuleInfo(
    key="notify-webhook",
    name="Webhook Notifications",
    type="notifier",
    version="1.0.0",
    description="Send webhook notifications for order events",
    router=router,
    user_router=user_router,
    models=[],
    notify=send_notification,
)
```

**Step 7: Commit**

```bash
git add backend/app/modules/notifiers/notify_webhook/
git commit -m "feat: add webhook notifier module"
```

---

### Task 8: Integrate Notifications into Queue Worker

**Files:**
- Modify: `backend/app/services/queue/queue_worker.py`

**Step 1: Add notification dispatch after order creation/update**

In `backend/app/services/queue/queue_worker.py`, add import at top:

```python
from app.services.notification_service import notify_user, NotificationEvent
```

After the `order = await create_or_update_order(...)` call (around line 67), add:

```python
            # Determine notification event type
            if existing_order:
                if order.status == "delivered":
                    notification_event = NotificationEvent.PACKAGE_DELIVERED
                else:
                    notification_event = NotificationEvent.TRACKING_UPDATE
            else:
                notification_event = NotificationEvent.NEW_ORDER

            # Send notifications (fire-and-forget, errors are logged)
            try:
                await notify_user(
                    user_id=item.user_id,
                    event_type=notification_event,
                    event_data={
                        "order_id": order.id,
                        "order_number": order.order_number,
                        "tracking_number": order.tracking_number,
                        "vendor_name": order.vendor_name,
                        "status": order.status,
                        "carrier": order.carrier,
                        "items": [i.get("name", "") for i in (order.items or [])],
                    },
                )
            except Exception as e:
                logger.error(f"Notification dispatch failed for order {order.id}: {e}")
```

**Step 2: Commit**

```bash
git add backend/app/services/queue/queue_worker.py
git commit -m "feat: dispatch notifications after order creation/update"
```

---

### Task 9: Alembic Migration

**Files:**
- Generate: `backend/alembic/versions/xxx_add_notification_tables.py`

**Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "add smtp_config, user_notification_config, email_verification tables"`

**Step 2: Review and edit generated migration**

Open the generated migration file and verify it creates:
- `smtp_config` table
- `user_notification_config` table with a unique constraint on `(user_id, module_key)`
- `email_verification` table

Add the unique constraint manually if autogenerate didn't pick it up:

```python
op.create_unique_constraint("uq_user_notification_config", "user_notification_config", ["user_id", "module_key"])
```

**Step 3: Commit**

```bash
git add backend/alembic/
git commit -m "feat: add migration for notification tables"
```

---

### Task 10: Frontend — SMTP Admin View

**Files:**
- Create: `frontend/src/views/admin/AdminSmtpSettingsView.vue`
- Modify: `frontend/src/router/index.ts` (add route)
- Modify: `frontend/src/views/admin/SettingsView.vue` (add sidebar item)
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Add i18n keys**

Add to `en.json`:

```json
"smtp": {
  "title": "E-Mail (SMTP)",
  "host": "SMTP Host",
  "hostPlaceholder": "smtp.example.com",
  "port": "Port",
  "username": "Username",
  "usernamePlaceholder": "user@example.com",
  "password": "Password",
  "passwordKeepCurrent": "(leave blank to keep current)",
  "useTls": "Use TLS",
  "senderAddress": "Sender Address",
  "senderAddressPlaceholder": "noreply@example.com",
  "senderName": "Sender Name",
  "senderNamePlaceholder": "Package Tracker",
  "saveConfig": "Save Configuration",
  "testConnection": "Send Test Email",
  "testRecipient": "Test Recipient",
  "testRecipientPlaceholder": "your@email.com",
  "testSuccess": "Test email sent successfully.",
  "testFailed": "Failed to send test email.",
  "configSaved": "SMTP configuration saved.",
  "saveFailed": "Failed to save SMTP configuration.",
  "loadFailed": "Failed to load SMTP configuration.",
  "notConfigured": "SMTP is not configured yet. Configure it to enable email notifications."
}
```

Add to `de.json`:

```json
"smtp": {
  "title": "E-Mail (SMTP)",
  "host": "SMTP-Host",
  "hostPlaceholder": "smtp.beispiel.de",
  "port": "Port",
  "username": "Benutzername",
  "usernamePlaceholder": "benutzer@beispiel.de",
  "password": "Passwort",
  "passwordKeepCurrent": "(leer lassen, um aktuelles beizubehalten)",
  "useTls": "TLS verwenden",
  "senderAddress": "Absenderadresse",
  "senderAddressPlaceholder": "noreply@beispiel.de",
  "senderName": "Absendername",
  "senderNamePlaceholder": "Package Tracker",
  "saveConfig": "Konfiguration speichern",
  "testConnection": "Test-E-Mail senden",
  "testRecipient": "Testempfänger",
  "testRecipientPlaceholder": "ihre@email.de",
  "testSuccess": "Test-E-Mail erfolgreich gesendet.",
  "testFailed": "Test-E-Mail konnte nicht gesendet werden.",
  "configSaved": "SMTP-Konfiguration gespeichert.",
  "saveFailed": "SMTP-Konfiguration konnte nicht gespeichert werden.",
  "loadFailed": "SMTP-Konfiguration konnte nicht geladen werden.",
  "notConfigured": "SMTP ist noch nicht konfiguriert. Konfigurieren Sie es, um E-Mail-Benachrichtigungen zu aktivieren."
}
```

Also add `"smtp": "E-Mail (SMTP)"` to `settings` section in both locale files.

**Step 2: Create AdminSmtpSettingsView.vue**

Create `frontend/src/views/admin/AdminSmtpSettingsView.vue` following the same pattern as `AdminGlobalMailView.vue` — form with host/port/username/password/TLS/sender fields, save button, test email section. Use `api.get('/admin/smtp')` and `api.put('/admin/smtp')` for loading/saving. Include a test section with `api.post('/admin/smtp/test', { recipient })`.

**Step 3: Add route to router**

In `frontend/src/router/index.ts`, add inside the `/admin/settings` children array (before `...getAdminRoutes()`):

```typescript
{
  path: 'smtp',
  name: 'smtp-settings',
  component: () => import('@/views/admin/AdminSmtpSettingsView.vue'),
},
```

**Step 4: Add sidebar item to SettingsView.vue**

In `frontend/src/views/admin/SettingsView.vue`, add a new router-link after the Analysers link (before the module groups template):

```html
<!-- SMTP (core, always visible) -->
<router-link
  to="/admin/settings/smtp"
  class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
  :class="
    isActive('/admin/settings/smtp')
      ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
  "
>
  {{ $t('settings.smtp') }}
</router-link>
```

**Step 5: Commit**

```bash
git add frontend/src/views/admin/AdminSmtpSettingsView.vue frontend/src/router/index.ts frontend/src/views/admin/SettingsView.vue frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: add SMTP admin settings view"
```

---

### Task 11: Frontend — Notifications Sidebar & Routes

**Files:**
- Modify: `frontend/src/components/AppLayout.vue`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/src/views/NotificationsView.vue`

**Step 1: Add notifications i18n keys**

Add to `en.json`:

```json
"notifications": {
  "title": "Notifications",
  "noModulesEnabled": "No notification modules are currently enabled. Contact your administrator.",
  "events": "Notify me about",
  "eventNewOrder": "New order detected",
  "eventTrackingUpdate": "Tracking update",
  "eventPackageDelivered": "Package delivered",
  "enabled": "Enabled",
  "disabled": "Disabled",
  "saveFailed": "Failed to save notification settings.",
  "configSaved": "Notification settings saved."
}
```

Add to `de.json`:

```json
"notifications": {
  "title": "Benachrichtigungen",
  "noModulesEnabled": "Derzeit sind keine Benachrichtigungsmodule aktiviert. Wenden Sie sich an Ihren Administrator.",
  "events": "Benachrichtigen bei",
  "eventNewOrder": "Neue Bestellung erkannt",
  "eventTrackingUpdate": "Tracking-Update",
  "eventPackageDelivered": "Paket zugestellt",
  "enabled": "Aktiviert",
  "disabled": "Deaktiviert",
  "saveFailed": "Benachrichtigungseinstellungen konnten nicht gespeichert werden.",
  "configSaved": "Benachrichtigungseinstellungen gespeichert."
}
```

Also add `"nav.notifications": "Notifications"` (en) / `"nav.notifications": "Benachrichtigungen"` (de).

**Step 2: Add notifications section to AppLayout.vue sidebar**

In `frontend/src/components/AppLayout.vue`, add import:

```typescript
import { getUserSidebarItems, getNotifierSidebarItems } from '@/core/moduleRegistry'
```

Add computed property after `providerItems`:

```typescript
const notifierItems = computed(() => {
  return getNotifierSidebarItems().filter(
    (item) => modulesStore.isEnabled(item.moduleKey) && modulesStore.isConfigured(item.moduleKey),
  )
})

const notifiersExpanded = ref(true)
```

Add the notifications section in the template, after the providers section and before the admin section:

```html
<!-- Notifications Section -->
<template v-if="notifierItems.length > 0">
  <button
    @click="notifiersExpanded = !notifiersExpanded"
    class="flex items-center justify-between w-full px-3 py-2 mt-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider hover:text-gray-600 dark:hover:text-gray-300"
  >
    {{ $t('nav.notifications') }}
    <svg
      class="w-3.5 h-3.5 transition-transform duration-200"
      :class="{ 'rotate-180': !notifiersExpanded }"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M19 9l-7 7-7-7"
      />
    </svg>
  </button>
  <template v-if="notifiersExpanded">
    <router-link
      v-for="item in notifierItems"
      :key="item.to"
      :to="item.to"
      class="flex items-center gap-3 px-3 py-2.5 pl-6 text-sm font-medium rounded-lg transition-colors"
      :class="
        isActive(item.to)
          ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
      "
      @click="sidebarOpen = false"
    >
      {{ $t(item.label) }}
    </router-link>
  </template>
</template>
```

Update `isActive` to handle notification routes:

```typescript
if (path.startsWith('/notifications/') && route.path === path) return true
```

**Step 3: Create NotificationsView.vue**

Create `frontend/src/views/NotificationsView.vue` — a layout view with a secondary sidebar (like `SettingsView.vue`) that lists notifier modules. Uses `<router-view />` for the content area.

```vue
<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('notifications.title') }}
    </h1>

    <div class="flex flex-col sm:flex-row gap-6">
      <nav class="sm:w-52 flex-shrink-0">
        <div class="flex sm:flex-col gap-1">
          <router-link
            v-for="item in notifierItems"
            :key="item.to"
            :to="item.to"
            class="px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            :class="
              isActive(item.to)
                ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
            "
          >
            {{ $t(item.label) }}
          </router-link>
        </div>
      </nav>
      <div class="flex-1 min-w-0">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useModulesStore } from '@/stores/modules'
import { getNotifierSidebarItems } from '@/core/moduleRegistry'

const route = useRoute()
const modulesStore = useModulesStore()

const notifierItems = computed(() => {
  return getNotifierSidebarItems().filter(
    (item) => modulesStore.isEnabled(item.moduleKey) && modulesStore.isConfigured(item.moduleKey),
  )
})

function isActive(path: string): boolean {
  return route.path === path
}
</script>
```

**Step 4: Add notification routes to router**

In `frontend/src/router/index.ts`, add module manifest imports:

```typescript
import '@/modules/notifiers/notify-email'
import '@/modules/notifiers/notify-webhook'
```

Add notification routes (after the `/providers` block):

```typescript
// Notifier user routes (dynamically from modules)
{
  path: '/notifications',
  component: () => import('@/views/NotificationsView.vue'),
  meta: { requiresAuth: true },
  children: getNotifierUserRoutes(),
},
```

Add import:

```typescript
import { getAdminRoutes, getUserRoutes, getNotifierUserRoutes } from '@/core/moduleRegistry'
```

**Step 5: Add verify-email route**

Add a public route for email verification:

```typescript
{
  path: '/verify-email/:token',
  name: 'verify-email',
  component: () => import('@/views/VerifyEmailView.vue'),
  meta: { requiresAuth: true },
},
```

Create `frontend/src/views/VerifyEmailView.vue` — a simple view that reads the token from the route, calls `POST /notifiers/notify-email/verify/{token}`, and shows success/error.

**Step 6: Commit**

```bash
git add frontend/src/components/AppLayout.vue frontend/src/router/index.ts frontend/src/views/NotificationsView.vue frontend/src/views/VerifyEmailView.vue frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: add notifications sidebar section and routes"
```

---

### Task 12: Frontend — Email Notifier Module

**Files:**
- Create: `frontend/src/modules/notifiers/notify-email/index.ts`
- Create: `frontend/src/modules/notifiers/notify-email/AdminNotifyEmailView.vue`
- Create: `frontend/src/modules/notifiers/notify-email/UserNotifyEmailView.vue`

**Step 1: Add module i18n keys**

Add to `modules` section in `en.json`:

```json
"notify-email": {
  "title": "Email Notifications",
  "description": "Send email notifications for order events",
  "userTitle": "Email",
  "smtpRequired": "Email notifications require SMTP to be configured. Ask your administrator to set up SMTP in Settings.",
  "emailAddress": "Notification Email",
  "emailPlaceholder": "your@email.com",
  "sendVerification": "Send Verification",
  "verificationSent": "Verification email sent. Check your inbox.",
  "verified": "Verified",
  "notVerified": "Not verified",
  "pendingVerification": "Verification pending — check your email",
  "verifySuccess": "Email verified successfully!",
  "verifyFailed": "Verification failed.",
  "verifyExpired": "Verification link has expired."
}
```

Add to `modules` section in `de.json`:

```json
"notify-email": {
  "title": "E-Mail-Benachrichtigungen",
  "description": "E-Mail-Benachrichtigungen für Bestellereignisse senden",
  "userTitle": "E-Mail",
  "smtpRequired": "E-Mail-Benachrichtigungen erfordern eine SMTP-Konfiguration. Bitten Sie Ihren Administrator, SMTP in den Einstellungen einzurichten.",
  "emailAddress": "Benachrichtigungs-E-Mail",
  "emailPlaceholder": "ihre@email.de",
  "sendVerification": "Verifizierung senden",
  "verificationSent": "Verifizierungs-E-Mail gesendet. Prüfen Sie Ihren Posteingang.",
  "verified": "Verifiziert",
  "notVerified": "Nicht verifiziert",
  "pendingVerification": "Verifizierung ausstehend — prüfen Sie Ihre E-Mails",
  "verifySuccess": "E-Mail erfolgreich verifiziert!",
  "verifyFailed": "Verifizierung fehlgeschlagen.",
  "verifyExpired": "Verifizierungslink ist abgelaufen."
}
```

**Step 2: Create module manifest**

Create `frontend/src/modules/notifiers/notify-email/index.ts`:

```typescript
import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'notify-email',
  name: 'modules.notify-email.title',
  type: 'notifier',
  adminRoutes: [
    {
      path: 'notify-email',
      component: () => import('./AdminNotifyEmailView.vue'),
      label: 'modules.notify-email.title',
    },
  ],
  userRoutes: [
    {
      path: 'notify-email',
      component: () => import('./UserNotifyEmailView.vue'),
      label: 'modules.notify-email.userTitle',
    },
  ],
})
```

**Step 3: Create AdminNotifyEmailView.vue**

Simple view with `ModuleHeader` toggle. Shows info text about SMTP dependency.

**Step 4: Create UserNotifyEmailView.vue**

User-facing view with:
- Toggle switch at top (enabled/disabled, disabled until email is verified)
- Email input + "Send Verification" button
- Verification status indicator
- Event checkboxes (new_order, tracking_update, package_delivered) — disabled until email verified

Uses API calls: `GET /notifiers/notify-email/config`, `POST /notifiers/notify-email/config/email`, `PUT /notifiers/notify-email/config/toggle`, `PUT /notifiers/notify-email/config/events`.

**Step 5: Commit**

```bash
git add frontend/src/modules/notifiers/notify-email/ frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: add email notifier frontend module"
```

---

### Task 13: Frontend — Webhook Notifier Module

**Files:**
- Create: `frontend/src/modules/notifiers/notify-webhook/index.ts`
- Create: `frontend/src/modules/notifiers/notify-webhook/AdminNotifyWebhookView.vue`
- Create: `frontend/src/modules/notifiers/notify-webhook/UserNotifyWebhookView.vue`

**Step 1: Add module i18n keys**

Add to `modules` section in `en.json`:

```json
"notify-webhook": {
  "title": "Webhook Notifications",
  "description": "Send webhook notifications for order events",
  "userTitle": "Webhook",
  "webhookUrl": "Webhook URL",
  "webhookUrlPlaceholder": "https://example.com/webhook",
  "authHeader": "Authorization Header",
  "authHeaderPlaceholder": "Bearer your-token (optional)",
  "saveWebhook": "Save Webhook",
  "testWebhook": "Send Test",
  "testSuccess": "Test webhook sent successfully (HTTP {code}).",
  "testFailed": "Test webhook failed.",
  "configSaved": "Webhook configuration saved."
}
```

Add to `modules` section in `de.json`:

```json
"notify-webhook": {
  "title": "Webhook-Benachrichtigungen",
  "description": "Webhook-Benachrichtigungen für Bestellereignisse senden",
  "userTitle": "Webhook",
  "webhookUrl": "Webhook-URL",
  "webhookUrlPlaceholder": "https://beispiel.de/webhook",
  "authHeader": "Authorization-Header",
  "authHeaderPlaceholder": "Bearer ihr-token (optional)",
  "saveWebhook": "Webhook speichern",
  "testWebhook": "Test senden",
  "testSuccess": "Test-Webhook erfolgreich gesendet (HTTP {code}).",
  "testFailed": "Test-Webhook fehlgeschlagen.",
  "configSaved": "Webhook-Konfiguration gespeichert."
}
```

**Step 2: Create module manifest**

Create `frontend/src/modules/notifiers/notify-webhook/index.ts`:

```typescript
import { registerModule } from '@/core/moduleRegistry'

registerModule({
  key: 'notify-webhook',
  name: 'modules.notify-webhook.title',
  type: 'notifier',
  adminRoutes: [
    {
      path: 'notify-webhook',
      component: () => import('./AdminNotifyWebhookView.vue'),
      label: 'modules.notify-webhook.title',
    },
  ],
  userRoutes: [
    {
      path: 'notify-webhook',
      component: () => import('./UserNotifyWebhookView.vue'),
      label: 'modules.notify-webhook.userTitle',
    },
  ],
})
```

**Step 3: Create AdminNotifyWebhookView.vue**

Simple view with `ModuleHeader` toggle only.

**Step 4: Create UserNotifyWebhookView.vue**

User-facing view with:
- Toggle switch at top
- Webhook URL input
- Authorization header input (type=password for masking)
- Save button
- Event checkboxes
- Test button

Uses API calls: `GET /notifiers/notify-webhook/config`, `PUT /notifiers/notify-webhook/config/webhook`, `PUT /notifiers/notify-webhook/config/toggle`, `PUT /notifiers/notify-webhook/config/events`, `POST /notifiers/notify-webhook/test`.

**Step 5: Commit**

```bash
git add frontend/src/modules/notifiers/notify-webhook/ frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat: add webhook notifier frontend module"
```

---

### Task 14: Test Conftest Updates & Final Tests

**Files:**
- Modify: `backend/tests/conftest.py`

**Step 1: Update conftest for new modules**

The test conftest seeds `ModuleConfig` rows for all discovered modules automatically (line 27-28 in conftest.py), so `notify-email` and `notify-webhook` will be included by discovery. No changes needed there.

If the new modules have startup hooks that need mocking, add patches similar to existing ones.

**Step 2: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass.

**Step 3: Run frontend build check**

Run: `cd frontend && npm run type-check && npm run build`
Expected: No type errors, clean build.

**Step 4: Commit any fixes**

If any fixes were needed, commit them.

---

### Task 15: Docker Test & Cleanup

**Step 1: Run Docker compose**

Run: `docker compose up --build`

Verify:
- App starts without errors
- Alembic migration creates new tables
- Admin settings shows SMTP and Queue sections
- Admin settings shows Notifier module group with notify-email and notify-webhook
- Enabling modules works
- User sidebar shows Notifications section when modules are enabled

**Step 2: Final commit**

```bash
git add -A
git commit -m "feat: complete notification system implementation"
```
