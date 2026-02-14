# Global Mail & Module System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a global mail account for email forwarding, user sender address registration, and a module system to toggle email-imap and email-global features.

**Architecture:** Three new DB models (GlobalMailConfig singleton, UserSenderAddress user-scoped, ModuleConfig key-value toggles). New API routers for each. IMAP worker extended with a global account watcher that gates processing on sender address lookup. Frontend Accounts page becomes a tabbed layout; Admin Settings gets Email and Modules sub-tabs.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Vue 3 Composition API, Pinia, Tailwind CSS 4, vue-i18n

---

### Task 1: ModuleConfig model + migration

**Files:**
- Create: `backend/app/models/module_config.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/` (auto-generated migration)

**Step 1: Create the ModuleConfig model**

Create `backend/app/models/module_config.py`:

```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ModuleConfig(Base):
    __tablename__ = "module_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Step 2: Register in models __init__**

Add to `backend/app/models/__init__.py`:

```python
from app.models.module_config import ModuleConfig
```

And add `"ModuleConfig"` to `__all__`.

**Step 3: Generate and review migration**

Run: `cd /home/mato/projects/tools/package-tracker/backend && alembic revision --autogenerate -m "add module_config table"`

Review the generated migration. It should create the `module_config` table. Manually add seed data to the `upgrade()` function:

```python
op.bulk_insert(
    sa.table(
        "module_config",
        sa.column("module_key", sa.String),
        sa.column("enabled", sa.Boolean),
    ),
    [
        {"module_key": "email-imap", "enabled": True},
        {"module_key": "email-global", "enabled": False},
    ],
)
```

**Step 4: Verify migration applies**

Run: `cd /home/mato/projects/tools/package-tracker && docker compose exec backend alembic upgrade head`

**Step 5: Commit**

```
feat: add ModuleConfig model with migration
```

---

### Task 2: Modules API router + tests

**Files:**
- Create: `backend/app/schemas/module_config.py`
- Create: `backend/app/api/modules.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_modules.py`

**Step 1: Create schemas**

Create `backend/app/schemas/module_config.py`:

```python
from pydantic import BaseModel


class ModuleResponse(BaseModel):
    module_key: str
    enabled: bool

    model_config = {"from_attributes": True}


class UpdateModuleRequest(BaseModel):
    enabled: bool
```

**Step 2: Write failing tests**

Create `backend/tests/test_modules.py`:

```python
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_modules_as_user(client, user_token):
    resp = await client.get("/api/v1/modules", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    keys = {m["module_key"] for m in data}
    assert "email-imap" in keys
    assert "email-global" in keys


@pytest.mark.asyncio
async def test_list_modules_as_admin(client, admin_token):
    resp = await client.get("/api/v1/modules", headers=auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_modules_unauthenticated(client):
    resp = await client.get("/api/v1/modules")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_module_as_admin(client, admin_token):
    resp = await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    # Verify persistence
    resp = await client.get("/api/v1/modules", headers=auth(admin_token))
    modules = {m["module_key"]: m["enabled"] for m in resp.json()}
    assert modules["email-global"] is True


@pytest.mark.asyncio
async def test_update_module_as_user_denied(client, user_token):
    resp = await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(user_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_unknown_module(client, admin_token):
    resp = await client.put(
        "/api/v1/modules/nonexistent",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    assert resp.status_code == 404
```

**Step 3: Run tests to verify they fail**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_modules.py -v`

Expected: FAIL (router not registered yet)

**Step 4: Create the modules router**

Create `backend/app/api/modules.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_admin_user
from app.database import get_db
from app.models.module_config import ModuleConfig
from app.schemas.module_config import ModuleResponse, UpdateModuleRequest

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])

KNOWN_MODULES = {"email-imap", "email-global"}


async def _ensure_modules_exist(db: AsyncSession) -> None:
    """Create module rows if they don't exist (first-run without migration seed)."""
    result = await db.execute(select(ModuleConfig))
    existing = {m.module_key for m in result.scalars().all()}
    for key in KNOWN_MODULES:
        if key not in existing:
            db.add(ModuleConfig(module_key=key, enabled=(key == "email-imap")))
    if KNOWN_MODULES - existing:
        await db.commit()


@router.get("", response_model=list[ModuleResponse])
async def list_modules(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_modules_exist(db)
    result = await db.execute(select(ModuleConfig).order_by(ModuleConfig.module_key))
    return result.scalars().all()


@router.put("/{module_key}", response_model=ModuleResponse)
async def update_module(
    module_key: str,
    req: UpdateModuleRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    if module_key not in KNOWN_MODULES:
        raise HTTPException(status_code=404, detail="Unknown module")
    await _ensure_modules_exist(db)
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    module.enabled = req.enabled
    await db.commit()
    await db.refresh(module)
    return module
```

**Step 5: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.modules import router as modules_router
app.include_router(modules_router)
```

**Step 6: Run tests to verify they pass**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_modules.py -v`

Expected: All PASS

**Step 7: Commit**

```
feat: add modules API with list and toggle endpoints
```

---

### Task 3: GlobalMailConfig model + migration

**Files:**
- Create: `backend/app/models/global_mail_config.py`
- Modify: `backend/app/models/__init__.py`
- Create: Alembic migration (auto-generated)

**Step 1: Create the GlobalMailConfig model**

Create `backend/app/models/global_mail_config.py`:

```python
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GlobalMailConfig(Base):
    __tablename__ = "global_mail_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_user: Mapped[str] = mapped_column(String(255))
    imap_password_encrypted: Mapped[str] = mapped_column(String(1024))
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_sec: Mapped[int] = mapped_column(Integer, default=300)
    use_polling: Mapped[bool] = mapped_column(Boolean, default=False)
    idle_supported: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    watched_folder_path: Mapped[str] = mapped_column(String(512), default="INBOX")
    last_seen_uid: Mapped[int] = mapped_column(Integer, default=0)
    uidvalidity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
```

**Step 2: Register in models __init__**

Add to `backend/app/models/__init__.py`:

```python
from app.models.global_mail_config import GlobalMailConfig
```

And add `"GlobalMailConfig"` to `__all__`.

**Step 3: Generate migration**

Run: `cd /home/mato/projects/tools/package-tracker/backend && alembic revision --autogenerate -m "add global_mail_config table"`

Review the migration.

**Step 4: Apply migration**

Run: `cd /home/mato/projects/tools/package-tracker && docker compose exec backend alembic upgrade head`

**Step 5: Commit**

```
feat: add GlobalMailConfig model with migration
```

---

### Task 4: UserSenderAddress model + migration

**Files:**
- Create: `backend/app/models/user_sender_address.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/models/user.py` (add relationship)
- Create: Alembic migration (auto-generated)

**Step 1: Create the UserSenderAddress model**

Create `backend/app/models/user_sender_address.py`:

```python
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserSenderAddress(Base):
    __tablename__ = "user_sender_address"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    email_address: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user = relationship("User", back_populates="sender_addresses")
```

**Step 2: Add relationship to User model**

In `backend/app/models/user.py`, add:

```python
sender_addresses = relationship("UserSenderAddress", back_populates="user", cascade="all, delete-orphan")
```

**Step 3: Register in models __init__**

Add to `backend/app/models/__init__.py`:

```python
from app.models.user_sender_address import UserSenderAddress
```

And add `"UserSenderAddress"` to `__all__`.

**Step 4: Generate and apply migration**

Run: `cd /home/mato/projects/tools/package-tracker/backend && alembic revision --autogenerate -m "add user_sender_address table"`

Then: `cd /home/mato/projects/tools/package-tracker && docker compose exec backend alembic upgrade head`

**Step 5: Commit**

```
feat: add UserSenderAddress model with migration
```

---

### Task 5: ProcessedEmail schema change + migration

**Files:**
- Modify: `backend/app/models/processed_email.py`
- Create: Alembic migration (auto-generated)

**Step 1: Modify ProcessedEmail model**

In `backend/app/models/processed_email.py`:
- Make `account_id` nullable (add `nullable=True`)
- Add `source` column: `Mapped[str] = mapped_column(String(20), default="user_account")`

**Step 2: Generate and apply migration**

Run: `cd /home/mato/projects/tools/package-tracker/backend && alembic revision --autogenerate -m "make processed_email account_id nullable and add source column"`

Then: `cd /home/mato/projects/tools/package-tracker && docker compose exec backend alembic upgrade head`

**Step 3: Commit**

```
feat: make ProcessedEmail.account_id nullable, add source column
```

---

### Task 6: Global mail config API + tests

**Files:**
- Create: `backend/app/schemas/global_mail_config.py`
- Create: `backend/app/api/global_mail.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_global_mail.py`

**Step 1: Create schemas**

Create `backend/app/schemas/global_mail_config.py`:

```python
from pydantic import BaseModel
from typing import Optional


class GlobalMailConfigRequest(BaseModel):
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: Optional[str] = None  # optional on update
    use_ssl: bool = True
    polling_interval_sec: int = 300
    use_polling: bool = False
    is_active: bool = False
    watched_folder_path: str = "INBOX"


class GlobalMailConfigResponse(BaseModel):
    id: int
    imap_host: str
    imap_port: int
    imap_user: str
    use_ssl: bool
    polling_interval_sec: int
    use_polling: bool
    idle_supported: Optional[bool] = None
    is_active: bool
    watched_folder_path: str

    model_config = {"from_attributes": True}


class GlobalMailInfoResponse(BaseModel):
    configured: bool
    email_address: Optional[str] = None
```

**Step 2: Write failing tests**

Create `backend/tests/test_global_mail.py`:

```python
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_returns_empty_when_not_configured(client, admin_token):
    resp = await client.get("/api/v1/settings/global-mail", headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_put_creates_config(client, admin_token):
    payload = {
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "imap_user": "global@example.com",
        "imap_password": "secret",
        "use_ssl": True,
        "is_active": True,
        "watched_folder_path": "INBOX",
    }
    resp = await client.put("/api/v1/settings/global-mail", json=payload, headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["imap_host"] == "imap.example.com"
    assert data["imap_user"] == "global@example.com"
    assert data["is_active"] is True
    assert "imap_password" not in data  # password should not be returned


@pytest.mark.asyncio
async def test_put_updates_existing(client, admin_token):
    payload = {
        "imap_host": "imap.example.com",
        "imap_user": "global@example.com",
        "imap_password": "secret",
    }
    await client.put("/api/v1/settings/global-mail", json=payload, headers=auth(admin_token))
    # Update without password
    payload2 = {
        "imap_host": "imap2.example.com",
        "imap_user": "global@example.com",
    }
    resp = await client.put("/api/v1/settings/global-mail", json=payload2, headers=auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["imap_host"] == "imap2.example.com"


@pytest.mark.asyncio
async def test_non_admin_denied(client, user_token):
    resp = await client.get("/api/v1/settings/global-mail", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_info_endpoint_as_user(client, admin_token, user_token):
    # Before config: not configured
    resp = await client.get("/api/v1/settings/global-mail/info", headers=auth(user_token))
    assert resp.status_code == 200
    assert resp.json()["configured"] is False

    # Create config
    await client.put(
        "/api/v1/settings/global-mail",
        json={
            "imap_host": "imap.example.com",
            "imap_user": "global@example.com",
            "imap_password": "secret",
            "is_active": True,
        },
        headers=auth(admin_token),
    )

    # After config: configured with email
    resp = await client.get("/api/v1/settings/global-mail/info", headers=auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["email_address"] == "global@example.com"
```

**Step 3: Run tests to verify they fail**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_global_mail.py -v`

**Step 4: Create the global mail router**

Create `backend/app/api/global_mail.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.core.encryption import encrypt_value
from app.database import get_db
from app.models.global_mail_config import GlobalMailConfig
from app.schemas.global_mail_config import (
    GlobalMailConfigRequest,
    GlobalMailConfigResponse,
    GlobalMailInfoResponse,
)

router = APIRouter(prefix="/api/v1/settings/global-mail", tags=["settings"])


async def _get_config(db: AsyncSession) -> GlobalMailConfig | None:
    result = await db.execute(select(GlobalMailConfig))
    return result.scalar_one_or_none()


@router.get("", response_model=GlobalMailConfigResponse | None)
async def get_global_mail_config(
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_config(db)


@router.put("", response_model=GlobalMailConfigResponse)
async def update_global_mail_config(
    req: GlobalMailConfigRequest,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if not config:
        config = GlobalMailConfig(
            imap_host=req.imap_host,
            imap_port=req.imap_port,
            imap_user=req.imap_user,
            imap_password_encrypted=encrypt_value(req.imap_password) if req.imap_password else "",
            use_ssl=req.use_ssl,
            polling_interval_sec=req.polling_interval_sec,
            use_polling=req.use_polling,
            is_active=req.is_active,
            watched_folder_path=req.watched_folder_path,
        )
        db.add(config)
    else:
        config.imap_host = req.imap_host
        config.imap_port = req.imap_port
        config.imap_user = req.imap_user
        if req.imap_password:
            config.imap_password_encrypted = encrypt_value(req.imap_password)
        config.use_ssl = req.use_ssl
        config.polling_interval_sec = req.polling_interval_sec
        config.use_polling = req.use_polling
        config.is_active = req.is_active
        config.watched_folder_path = req.watched_folder_path
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/info", response_model=GlobalMailInfoResponse)
async def get_global_mail_info(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if not config or not config.is_active:
        return GlobalMailInfoResponse(configured=False)
    return GlobalMailInfoResponse(configured=True, email_address=config.imap_user)
```

**Step 5: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.global_mail import router as global_mail_router
app.include_router(global_mail_router)
```

**Step 6: Run tests to verify they pass**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_global_mail.py -v`

**Step 7: Commit**

```
feat: add global mail config API with admin and info endpoints
```

---

### Task 7: Sender addresses API + tests

**Files:**
- Create: `backend/app/schemas/sender_address.py`
- Create: `backend/app/api/sender_addresses.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_sender_addresses.py`

**Step 1: Create schemas**

Create `backend/app/schemas/sender_address.py`:

```python
from datetime import datetime

from pydantic import BaseModel, EmailStr


class CreateSenderAddressRequest(BaseModel):
    email_address: EmailStr


class SenderAddressResponse(BaseModel):
    id: int
    email_address: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

**Step 2: Write failing tests**

Create `backend/tests/test_sender_addresses.py`:

```python
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


@pytest.fixture
async def user2_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user2", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user2", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_empty(client, user_token):
    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_and_list(client, user_token):
    resp = await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email_address"] == "me@example.com"

    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_duplicate_same_user(client, user_token):
    await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    resp = await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "me@example.com"},
        headers=auth(user_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_different_user(client, user_token, user2_token):
    await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "shared@example.com"},
        headers=auth(user_token),
    )
    resp = await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "shared@example.com"},
        headers=auth(user2_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_delete(client, user_token):
    resp = await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "del@example.com"},
        headers=auth(user_token),
    )
    addr_id = resp.json()["id"]
    resp = await client.delete(f"/api/v1/sender-addresses/{addr_id}", headers=auth(user_token))
    assert resp.status_code == 204

    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_delete_other_users_address(client, user_token, user2_token):
    resp = await client.post(
        "/api/v1/sender-addresses",
        json={"email_address": "other@example.com"},
        headers=auth(user_token),
    )
    addr_id = resp.json()["id"]
    resp = await client.delete(f"/api/v1/sender-addresses/{addr_id}", headers=auth(user2_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_denied(client):
    resp = await client.get("/api/v1/sender-addresses")
    assert resp.status_code in (401, 403)
```

**Step 3: Run tests to verify they fail**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_sender_addresses.py -v`

**Step 4: Create the sender addresses router**

Create `backend/app/api/sender_addresses.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user_sender_address import UserSenderAddress
from app.schemas.sender_address import CreateSenderAddressRequest, SenderAddressResponse

router = APIRouter(prefix="/api/v1/sender-addresses", tags=["sender-addresses"])


@router.get("", response_model=list[SenderAddressResponse])
async def list_sender_addresses(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSenderAddress).where(UserSenderAddress.user_id == user.id)
    )
    return result.scalars().all()


@router.post("", response_model=SenderAddressResponse, status_code=201)
async def create_sender_address(
    req: CreateSenderAddressRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness across all users
    existing = await db.execute(
        select(UserSenderAddress).where(
            UserSenderAddress.email_address == req.email_address.lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email address already registered")

    addr = UserSenderAddress(user_id=user.id, email_address=req.email_address.lower())
    db.add(addr)
    await db.commit()
    await db.refresh(addr)
    return addr


@router.delete("/{address_id}", status_code=204)
async def delete_sender_address(
    address_id: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await db.get(UserSenderAddress, address_id)
    if not addr or addr.user_id != user.id:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.delete(addr)
    await db.commit()
```

**Step 5: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.api.sender_addresses import router as sender_addresses_router
app.include_router(sender_addresses_router)
```

Note: `pydantic[email]` may need to be added to dependencies for `EmailStr`. Check `pyproject.toml` — if not present, add `email-validator` to dependencies.

**Step 6: Run tests to verify they pass**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_sender_addresses.py -v`

**Step 7: Commit**

```
feat: add sender addresses API with CRUD and duplicate checking
```

---

### Task 8: Module enforcement on existing endpoints

**Files:**
- Create: `backend/app/api/module_deps.py`
- Modify: `backend/app/api/accounts.py`
- Modify: `backend/app/api/sender_addresses.py`
- Create: `backend/tests/test_module_enforcement.py`

**Step 1: Create module dependency helpers**

Create `backend/app/api/module_deps.py`:

```python
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.module_config import ModuleConfig


async def _check_module(module_key: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(ModuleConfig).where(ModuleConfig.module_key == module_key)
    )
    module = result.scalar_one_or_none()
    if module and not module.enabled:
        raise HTTPException(status_code=403, detail=f"Module '{module_key}' is disabled")


async def require_email_imap(db: AsyncSession = Depends(get_db)) -> None:
    await _check_module("email-imap", db)


async def require_email_global(db: AsyncSession = Depends(get_db)) -> None:
    await _check_module("email-global", db)
```

**Step 2: Write failing tests**

Create `backend/tests/test_module_enforcement.py`:

```python
import pytest
from app.models.module_config import ModuleConfig


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def user_token(client, admin_token):
    await client.post(
        "/api/v1/users",
        json={"username": "user1", "password": "pass"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_accounts_blocked_when_imap_disabled(client, admin_token, user_token):
    # Disable email-imap module
    await client.put(
        "/api/v1/modules/email-imap",
        json={"enabled": False},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/accounts", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_accounts_allowed_when_imap_enabled(client, admin_token, user_token):
    # Ensure module is enabled (default)
    await client.put(
        "/api/v1/modules/email-imap",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/accounts", headers=auth(user_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sender_addresses_blocked_when_global_disabled(client, admin_token, user_token):
    # email-global is disabled by default
    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sender_addresses_allowed_when_global_enabled(client, admin_token, user_token):
    await client.put(
        "/api/v1/modules/email-global",
        json={"enabled": True},
        headers=auth(admin_token),
    )
    resp = await client.get("/api/v1/sender-addresses", headers=auth(user_token))
    assert resp.status_code == 200
```

**Step 3: Run tests to verify they fail**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_module_enforcement.py -v`

**Step 4: Add module dependencies to routers**

In `backend/app/api/accounts.py`, add the dependency to the router:

```python
from app.api.module_deps import require_email_imap

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"],
    dependencies=[Depends(require_email_imap)],
)
```

In `backend/app/api/sender_addresses.py`, add:

```python
from app.api.module_deps import require_email_global

router = APIRouter(
    prefix="/api/v1/sender-addresses",
    tags=["sender-addresses"],
    dependencies=[Depends(require_email_global)],
)
```

**Step 5: Run tests to verify they pass**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_module_enforcement.py -v`

Also run the full test suite to ensure nothing else broke:

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/ -v`

**Step 6: Commit**

```
feat: add module enforcement to accounts and sender-addresses routers
```

---

### Task 9: IMAP worker — global mail watcher

**Files:**
- Modify: `backend/app/services/imap_worker.py`

**Step 1: Add global watcher functions**

Add to `backend/app/services/imap_worker.py` the following:

1. Import `GlobalMailConfig`, `UserSenderAddress`, `ModuleConfig`
2. Add a module-level `_global_task: asyncio.Task | None = None` and `_global_state: WorkerState | None = None`
3. Add helper to extract email address from a FROM header string (handles `"Name <addr>"` format):

```python
def _extract_email_from_header(from_header: str) -> str:
    """Extract bare email from 'Display Name <email@example.com>' format."""
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).lower()
    return from_header.strip().lower()
```

4. Add `_fetch_global_emails()` — similar to `_fetch_new_emails` but with sender gate:

```python
async def _fetch_global_emails(imap, config: GlobalMailConfig, db, state: WorkerState | None) -> None:
    """Fetch new emails from global inbox, gate on sender address."""
    max_age = 7  # Use global IMAP settings default
    result = await db.execute(select(ImapSettings))
    global_settings = result.scalar_one_or_none()
    if global_settings:
        max_age = global_settings.max_email_age_days

    since_date = (datetime.now(timezone.utc) - timedelta(days=max_age)).strftime("%d-%b-%Y")
    search_criteria = f"UID {config.last_seen_uid + 1}:* SINCE {since_date}"
    _, data = await imap.uid_search(search_criteria)
    uids = data[0].split() if data[0] else []

    if state:
        if uids:
            state.mode = WorkerMode.PROCESSING
            state.queue_total = len(uids)
        state.last_activity_at = datetime.now(timezone.utc)

    for i, uid_bytes in enumerate(uids):
        uid = int(uid_bytes)
        if uid <= config.last_seen_uid:
            continue

        _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
        if not msg_data or not msg_data[0]:
            continue

        raw_email = None
        for part in msg_data:
            if isinstance(part, bytearray):
                raw_email = bytes(part)
                break
        if raw_email is None:
            continue
        msg = email.message_from_bytes(raw_email)

        sender = _decode_header_value(msg.get("From", ""))
        sender_email = _extract_email_from_header(sender)

        # Sender gate: look up in UserSenderAddress
        result = await db.execute(
            select(UserSenderAddress).where(UserSenderAddress.email_address == sender_email)
        )
        sender_addr = result.scalar_one_or_none()
        if not sender_addr:
            logger.info(f"Global mail: discarding email from unregistered sender: {sender_email}")
            config.last_seen_uid = uid
            await db.commit()
            continue

        subject = _decode_header_value(msg.get("Subject", ""))
        message_id = msg.get("Message-ID", "")
        body = _extract_body(msg)

        email_date = None
        try:
            date_str = msg.get("Date", "")
            if date_str:
                from email.utils import parsedate_to_datetime
                email_date = parsedate_to_datetime(date_str)
        except Exception:
            pass

        if state:
            state.queue_position = i + 1
            state.current_email_subject = subject
            state.current_email_sender = sender
            state.last_activity_at = datetime.now(timezone.utc)

        # Dedup check
        existing = await db.execute(
            select(ProcessedEmail).where(ProcessedEmail.message_id == message_id)
        )
        if existing.scalar_one_or_none():
            config.last_seen_uid = uid
            await db.commit()
            continue

        queue_item = QueueItem(
            user_id=sender_addr.user_id,
            status="queued",
            source_type="email",
            source_info=f"global / {config.watched_folder_path}",
            raw_data={
                "subject": subject,
                "sender": sender,
                "body": body,
                "message_id": message_id,
                "email_uid": uid,
                "email_date": email_date.isoformat() if email_date else None,
            },
        )
        db.add(queue_item)
        await db.flush()

        processed = ProcessedEmail(
            account_id=None,
            folder_path=config.watched_folder_path,
            email_uid=uid,
            message_id=message_id,
            queue_item_id=queue_item.id,
            source="global_mail",
        )
        db.add(processed)

        config.last_seen_uid = uid
        await db.commit()

    if state:
        state.last_scan_at = datetime.now(timezone.utc)
        state.clear_queue()
```

5. Add `_watch_global_folder()` — connect using GlobalMailConfig credentials, then IDLE or poll, calling `_fetch_global_emails`. Structure mirrors `_watch_folder` but uses `GlobalMailConfig` instead of `EmailAccount`/`WatchedFolder`.

6. Modify `start_all_watchers()` to also check `GlobalMailConfig` + `email-global` module:

```python
# At the end of start_all_watchers():
async with async_session() as db:
    result = await db.execute(select(ModuleConfig).where(ModuleConfig.module_key == "email-global"))
    module = result.scalar_one_or_none()
    if module and module.enabled:
        result = await db.execute(select(GlobalMailConfig))
        config = result.scalar_one_or_none()
        if config and config.is_active:
            _start_global_watcher(config)
```

7. Modify `stop_all_watchers()` to also cancel `_global_task`.

8. Modify `restart_watchers()` to restart the global watcher too.

**Step 2: Run existing imap_worker tests to ensure no regressions**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/test_imap_worker.py -v`

**Step 3: Commit**

```
feat: add global mail watcher with sender address gating
```

---

### Task 10: Frontend — Modules store

**Files:**
- Create: `frontend/src/stores/modules.ts`

**Step 1: Create the modules store**

Create `frontend/src/stores/modules.ts`:

```typescript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

interface Module {
  module_key: string
  enabled: boolean
}

export const useModulesStore = defineStore('modules', () => {
  const modules = ref<Module[]>([])
  const loaded = ref(false)

  const isEnabled = computed(() => (key: string) => {
    const m = modules.value.find((mod) => mod.module_key === key)
    return m?.enabled ?? false
  })

  async function fetchModules() {
    const res = await api.get('/modules')
    modules.value = res.data
    loaded.value = true
  }

  return { modules, loaded, isEnabled, fetchModules }
})
```

**Step 2: Commit**

```
feat(frontend): add modules Pinia store
```

---

### Task 11: Frontend — Sender addresses store

**Files:**
- Create: `frontend/src/stores/senderAddresses.ts`

**Step 1: Create the store**

Create `frontend/src/stores/senderAddresses.ts`:

```typescript
import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export interface SenderAddress {
  id: number
  email_address: string
  created_at: string
}

export const useSenderAddressesStore = defineStore('senderAddresses', () => {
  const addresses = ref<SenderAddress[]>([])
  const loading = ref(false)

  async function fetchAddresses() {
    loading.value = true
    try {
      const res = await api.get('/sender-addresses')
      addresses.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function addAddress(email: string): Promise<SenderAddress> {
    const res = await api.post('/sender-addresses', { email_address: email })
    addresses.value.push(res.data)
    return res.data
  }

  async function removeAddress(id: number) {
    await api.delete(`/sender-addresses/${id}`)
    addresses.value = addresses.value.filter((a) => a.id !== id)
  }

  return { addresses, loading, fetchAddresses, addAddress, removeAddress }
})
```

**Step 2: Commit**

```
feat(frontend): add sender addresses Pinia store
```

---

### Task 12: Frontend — Refactor Accounts page to tabbed layout

**Files:**
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/AccountsView.vue` (becomes shell)
- Create: `frontend/src/views/AccountsImapView.vue` (current content moves here)
- Create: `frontend/src/views/AccountsForwardingView.vue`

**Step 1: Extract current AccountsView content to AccountsImapView**

Create `frontend/src/views/AccountsImapView.vue` with the entire current content of `AccountsView.vue` (template + script).

**Step 2: Rewrite AccountsView as tabbed shell**

Replace `AccountsView.vue` with a tabbed layout. Pattern mirrors `SettingsView.vue` but uses horizontal tabs and conditionally renders based on module state:

```vue
<template>
  <div class="p-6 max-w-5xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
      {{ $t('accounts.title') }}
    </h1>

    <div v-if="!modulesStore.loaded" class="text-center py-12 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>

    <template v-else-if="enabledTabs.length === 0">
      <div class="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
        <p class="text-gray-500 dark:text-gray-400">{{ $t('accounts.noModulesEnabled') }}</p>
      </div>
    </template>

    <template v-else>
      <!-- Tab Navigation -->
      <div class="border-b border-gray-200 dark:border-gray-700 mb-6">
        <nav class="flex gap-4">
          <router-link
            v-for="tab in enabledTabs"
            :key="tab.to"
            :to="tab.to"
            class="pb-3 px-1 text-sm font-medium border-b-2 transition-colors"
            :class="
              isActive(tab.to)
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'
            "
          >
            {{ tab.label }}
          </router-link>
        </nav>
      </div>

      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()
const route = useRoute()
const modulesStore = useModulesStore()

const allTabs = computed(() => [
  { to: '/accounts/imap', label: t('accounts.tabImap'), module: 'email-imap' },
  { to: '/accounts/forwarding', label: t('accounts.tabForwarding'), module: 'email-global' },
])

const enabledTabs = computed(() =>
  allTabs.value.filter((tab) => modulesStore.isEnabled(tab.module))
)

function isActive(path: string): boolean {
  return route.path === path
}

onMounted(async () => {
  if (!modulesStore.loaded) {
    await modulesStore.fetchModules()
  }
})
</script>
```

**Step 3: Create AccountsForwardingView**

Create `frontend/src/views/AccountsForwardingView.vue`:

```vue
<template>
  <div>
    <!-- Info box showing the global inbox address -->
    <div
      v-if="globalInfo.configured"
      class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6"
    >
      <p class="text-sm text-blue-800 dark:text-blue-300">
        {{ $t('forwarding.infoText') }}
        <span class="font-mono font-semibold">{{ globalInfo.email_address }}</span>
      </p>
    </div>
    <div
      v-else
      class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6"
    >
      <p class="text-sm text-amber-800 dark:text-amber-300">
        {{ $t('forwarding.notConfigured') }}
      </p>
    </div>

    <!-- Add form -->
    <div class="mb-6">
      <form @submit.prevent="handleAdd" class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {{ $t('forwarding.emailAddress') }}
          </label>
          <input
            v-model="newEmail"
            type="email"
            required
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            :placeholder="$t('forwarding.emailPlaceholder')"
          />
        </div>
        <button
          type="submit"
          :disabled="adding"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {{ adding ? $t('common.saving') : $t('forwarding.addAddress') }}
        </button>
      </form>
      <p v-if="error" class="mt-2 text-sm text-red-600 dark:text-red-400">{{ error }}</p>
    </div>

    <!-- Address list -->
    <div v-if="store.loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>
    <div v-else-if="store.addresses.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('forwarding.noAddresses') }}
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="addr in store.addresses"
        :key="addr.id"
        class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-3"
      >
        <span class="text-sm text-gray-900 dark:text-white">{{ addr.email_address }}</span>
        <button
          @click="handleDelete(addr.id)"
          :disabled="deletingId === addr.id"
          class="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 disabled:opacity-50"
        >
          {{ deletingId === addr.id ? $t('common.deleting') : $t('common.delete') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { useSenderAddressesStore } from '@/stores/senderAddresses'

const { t } = useI18n()
const store = useSenderAddressesStore()

const newEmail = ref('')
const adding = ref(false)
const error = ref('')
const deletingId = ref<number | null>(null)
const globalInfo = reactive({ configured: false, email_address: '' })

async function fetchGlobalInfo() {
  try {
    const res = await api.get('/settings/global-mail/info')
    globalInfo.configured = res.data.configured
    globalInfo.email_address = res.data.email_address || ''
  } catch {
    // Not available
  }
}

async function handleAdd() {
  error.value = ''
  adding.value = true
  try {
    await store.addAddress(newEmail.value)
    newEmail.value = ''
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('forwarding.addFailed')
  } finally {
    adding.value = false
  }
}

async function handleDelete(id: number) {
  deletingId.value = id
  try {
    await store.removeAddress(id)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('forwarding.deleteFailed')
  } finally {
    deletingId.value = null
  }
}

onMounted(() => {
  store.fetchAddresses()
  fetchGlobalInfo()
})
</script>
```

**Step 4: Update router**

In `frontend/src/router/index.ts`, replace the `/accounts` route:

```typescript
{
  path: '/accounts',
  component: () => import('@/views/AccountsView.vue'),
  meta: { requiresAuth: true },
  children: [
    {
      path: '',
      name: 'accounts',
      redirect: '/accounts/imap',
    },
    {
      path: 'imap',
      name: 'accounts-imap',
      component: () => import('@/views/AccountsImapView.vue'),
    },
    {
      path: 'forwarding',
      name: 'accounts-forwarding',
      component: () => import('@/views/AccountsForwardingView.vue'),
    },
  ],
},
```

**Step 5: Commit**

```
feat(frontend): refactor accounts page to tabbed layout with IMAP and forwarding tabs
```

---

### Task 13: Frontend — Admin settings: Modules view

**Files:**
- Create: `frontend/src/views/admin/ModulesView.vue`
- Modify: `frontend/src/views/admin/SettingsView.vue`
- Modify: `frontend/src/router/index.ts`

**Step 1: Create ModulesView**

Create `frontend/src/views/admin/ModulesView.vue`:

```vue
<template>
  <div>
    <div v-if="loading" class="text-center py-8 text-gray-500 dark:text-gray-400">
      {{ $t('common.loading') }}
    </div>
    <div v-else class="space-y-4">
      <div
        v-for="mod in modulesStore.modules"
        :key="mod.module_key"
        class="flex items-center justify-between bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-4"
      >
        <div>
          <h3 class="text-sm font-medium text-gray-900 dark:text-white">
            {{ $t(`modules.${mod.module_key}.title`) }}
          </h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {{ $t(`modules.${mod.module_key}.description`) }}
          </p>
        </div>
        <button
          @click="handleToggle(mod.module_key, !mod.enabled)"
          :disabled="toggling === mod.module_key"
          class="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          :class="mod.enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'"
        >
          <span
            class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
            :class="mod.enabled ? 'translate-x-5' : 'translate-x-0'"
          />
        </button>
      </div>
    </div>
    <p v-if="error" class="mt-4 text-sm text-red-600 dark:text-red-400">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/client'
import { useModulesStore } from '@/stores/modules'

const { t } = useI18n()
const modulesStore = useModulesStore()
const loading = ref(false)
const toggling = ref<string | null>(null)
const error = ref('')

async function handleToggle(key: string, enabled: boolean) {
  toggling.value = key
  error.value = ''
  try {
    await api.put(`/modules/${key}`, { enabled })
    await modulesStore.fetchModules()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail || t('modules.toggleFailed')
  } finally {
    toggling.value = null
  }
}

onMounted(async () => {
  loading.value = true
  await modulesStore.fetchModules()
  loading.value = false
})
</script>
```

**Step 2: Add route and tab**

In `frontend/src/router/index.ts`, add to the `/admin/settings` children:

```typescript
{
  path: 'modules',
  name: 'settings-modules',
  component: () => import('@/views/admin/ModulesView.vue'),
},
```

In `frontend/src/views/admin/SettingsView.vue`, add to `tabs`:

```typescript
{ to: '/admin/settings/modules', label: t('settings.modules') },
```

**Step 3: Commit**

```
feat(frontend): add admin modules settings view with toggles
```

---

### Task 14: Frontend — Admin settings: Global mail config view

**Files:**
- Create: `frontend/src/views/admin/GlobalMailConfigView.vue`
- Modify: `frontend/src/views/admin/SettingsView.vue`
- Modify: `frontend/src/router/index.ts`

**Step 1: Create GlobalMailConfigView**

Create `frontend/src/views/admin/GlobalMailConfigView.vue` — follows the same pattern as `ImapSettingsView.vue` but with IMAP config fields (host, port, user, password, SSL, polling, folder path, active toggle). This is a form with GET/PUT against `/settings/global-mail`.

Include fields:
- `imap_host`, `imap_port`, `imap_user`, `imap_password` (password field, leave empty to keep current)
- `use_ssl` checkbox
- `polling_interval_sec` number input
- `use_polling` checkbox
- `watched_folder_path` text input (default "INBOX")
- `is_active` toggle

**Step 2: Add route and tab**

In `frontend/src/router/index.ts`, add to `/admin/settings` children:

```typescript
{
  path: 'email',
  name: 'settings-email',
  component: () => import('@/views/admin/GlobalMailConfigView.vue'),
},
```

In `frontend/src/views/admin/SettingsView.vue`, add to `tabs`:

```typescript
{ to: '/admin/settings/email', label: t('settings.email') },
```

**Step 3: Commit**

```
feat(frontend): add admin global mail config settings view
```

---

### Task 15: i18n translations

**Files:**
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Add all new translation keys**

Add to both locale files:

```json
{
  "accounts": {
    "tabImap": "IMAP Accounts",
    "tabForwarding": "Forwarding",
    "noModulesEnabled": "No email features are currently enabled. Contact your administrator."
  },
  "forwarding": {
    "infoText": "Forward your order confirmation emails to:",
    "notConfigured": "Global mail forwarding is not configured yet. Contact your administrator.",
    "emailAddress": "Your Email Address",
    "emailPlaceholder": "your.email@example.com",
    "addAddress": "Add Address",
    "noAddresses": "No sender addresses registered yet.",
    "addFailed": "Failed to add address.",
    "deleteFailed": "Failed to remove address."
  },
  "modules": {
    "email-imap": {
      "title": "IMAP Accounts",
      "description": "Allow users to connect their own IMAP email accounts."
    },
    "email-global": {
      "title": "Global Mail Forwarding",
      "description": "Allow users to forward emails to a shared inbox."
    },
    "toggleFailed": "Failed to update module."
  },
  "settings": {
    "email": "Email",
    "modules": "Modules"
  },
  "globalMail": {
    "imapHost": "IMAP Host",
    "imapPort": "IMAP Port",
    "username": "Username",
    "password": "Password",
    "passwordKeepCurrent": "(leave empty to keep current)",
    "useSsl": "Use SSL",
    "pollingInterval": "Polling Interval (seconds)",
    "usePolling": "Use Polling",
    "watchedFolder": "Watched Folder",
    "isActive": "Active",
    "saveSettings": "Save Settings",
    "configSaved": "Global mail configuration saved.",
    "saveFailed": "Failed to save configuration."
  }
}
```

German translations follow the same structure with translated values.

**Step 2: Commit**

```
feat(frontend): add i18n translations for modules, forwarding, and global mail
```

---

### Task 16: Final integration test

**Step 1: Run full backend test suite**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -m pytest tests/ -v`

Expected: All tests pass.

**Step 2: Run frontend build check**

Run: `cd /home/mato/projects/tools/package-tracker/frontend && npm run build`

Expected: Build succeeds with no type errors.

**Step 3: Manual smoke test with Docker**

Run: `cd /home/mato/projects/tools/package-tracker && docker compose up --build`

Verify:
1. Admin can toggle modules in `/admin/settings/modules`
2. Admin can configure global mail in `/admin/settings/email`
3. User sees appropriate tabs in `/accounts` based on enabled modules
4. User can add/remove sender addresses in `/accounts/forwarding`
5. Disabling a module hides the corresponding tab

**Step 4: Commit any fixes**

```
fix: address integration issues from smoke testing
```
