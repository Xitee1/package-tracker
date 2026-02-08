# Package Tracker Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a self-hosted email-powered package tracker with AI analysis, multi-user support, and Vue 3 dashboard.

**Architecture:** FastAPI backend with async IMAP workers + LiteLLM for email analysis, Vue 3 + Tailwind frontend, PostgreSQL database, all deployed via Docker Compose.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), Alembic, LiteLLM, aioimaplib, Vue 3, Vite, Tailwind CSS, Pinia, PostgreSQL 16, Docker Compose.

**Reference:** See `docs/plans/2026-02-08-package-tracker-design.md` for full design.

---

## Phase 1: Project Scaffolding & Database

### Task 1: Backend project setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/__init__.py`

**Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "package-tracker"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.0",
    "cryptography>=44.0.0",
    "litellm>=1.55.0",
    "aioimaplib>=2.0.0",
    "html2text>=2024.0.0",
    "python-multipart>=0.0.18",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.28.0",
    "aiosqlite>=0.20.0",
]

[build-system]
requires = ["setuptools>=75.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

**Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://tracker:tracker@db:5432/tracker"
    secret_key: str = "change-me-in-production"
    encryption_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    model_config = {"env_prefix": "PT_"}


settings = Settings()
```

**Step 3: Create `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Package Tracker", version="0.1.0")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

**Step 4: Create empty `__init__.py` files**

Create empty files at `backend/app/__init__.py` and `backend/tests/__init__.py`.

**Step 5: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with FastAPI"
```

---

### Task 2: Docker Compose & database setup

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: tracker
      POSTGRES_PASSWORD: tracker
      POSTGRES_DB: tracker
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    environment:
      PT_DATABASE_URL: postgresql+asyncpg://tracker:tracker@db:5432/tracker
      PT_SECRET_KEY: ${PT_SECRET_KEY:-dev-secret-key}
      PT_ENCRYPTION_KEY: ${PT_ENCRYPTION_KEY:-dev-encryption-key}
    ports:
      - "8000:8000"
    depends_on:
      - db
    volumes:
      - ./backend:/app

volumes:
  pgdata:
```

**Step 2: Create `.env.example`**

```env
PT_SECRET_KEY=change-me-to-a-random-string
PT_ENCRYPTION_KEY=change-me-to-a-random-string
PT_DATABASE_URL=postgresql+asyncpg://tracker:tracker@db:5432/tracker
```

**Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
*.egg-info/
.venv/
node_modules/
dist/
.pytest_cache/
```

**Step 4: Test Docker Compose starts**

Run: `docker compose up --build -d`
Then: `curl http://localhost:8000/api/v1/health`
Expected: `{"status":"ok"}`

**Step 5: Commit**

```bash
git add docker-compose.yml .env.example .gitignore
git commit -m "feat: add Docker Compose with PostgreSQL and backend"
```

---

### Task 3: Database engine, models, and migrations

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/email_account.py`
- Create: `backend/app/models/order.py`
- Create: `backend/app/models/llm_config.py`
- Modify: `backend/app/main.py`

**Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 2: Create `backend/app/models/user.py`**

```python
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    email_accounts = relationship("EmailAccount", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
```

**Step 3: Create `backend/app/models/email_account.py`**

```python
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailAccount(Base):
    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    imap_host: Mapped[str] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_user: Mapped[str] = mapped_column(String(255))
    imap_password_encrypted: Mapped[str] = mapped_column(String(1024))
    use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    polling_interval_sec: Mapped[int] = mapped_column(Integer, default=120)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="email_accounts")
    watched_folders = relationship("WatchedFolder", back_populates="account", cascade="all, delete-orphan")


class WatchedFolder(Base):
    __tablename__ = "watched_folders"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("email_accounts.id", ondelete="CASCADE"))
    folder_path: Mapped[str] = mapped_column(String(512))
    last_seen_uid: Mapped[int] = mapped_column(Integer, default=0)

    account = relationship("EmailAccount", back_populates="watched_folders")
```

**Step 4: Create `backend/app/models/order.py`**

```python
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Numeric, ForeignKey, func, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    order_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tracking_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    carrier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vendor_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ordered")
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    items: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    estimated_delivery: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50))
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50))
    source_email_message_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_email_uid: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_folder: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="events")
```

**Step 5: Create `backend/app/models/llm_config.py`**

```python
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(255))
    api_key_encrypted: Mapped[str] = mapped_column(String(1024), default="")
    api_base_url: Mapped[str] = mapped_column(String(512), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Step 6: Create `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.order import Order, OrderEvent
from app.models.llm_config import LLMConfig

__all__ = ["User", "EmailAccount", "WatchedFolder", "Order", "OrderEvent", "LLMConfig"]
```

**Step 7: Set up Alembic**

Run inside the backend container:
```bash
docker compose exec backend pip install alembic
docker compose exec backend alembic init alembic
```

Then edit `backend/alembic/env.py` to use async engine and import all models. Edit `backend/alembic.ini` to use the `PT_DATABASE_URL` env var.

Create `backend/alembic/env.py`:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.config import settings
from app.database import Base
from app.models import *  # noqa: F401, F403 - import all models for autogenerate

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Step 8: Generate and run initial migration**

```bash
docker compose exec backend alembic revision --autogenerate -m "initial schema"
docker compose exec backend alembic upgrade head
```

**Step 9: Update `backend/app/main.py` to run migrations on startup**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine, Base
from app.models import *  # noqa: F401, F403


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (in prod, use alembic migrate instead)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Package Tracker", version="0.1.0", lifespan=lifespan)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

**Step 10: Commit**

```bash
git add backend/
git commit -m "feat: add database models and Alembic migrations"
```

---

## Phase 2: Authentication & User Management

### Task 4: Core auth utilities (encryption, JWT, password hashing)

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/encryption.py`
- Create: `backend/app/core/auth.py`
- Create: `backend/tests/test_core.py`

**Step 1: Write tests for encryption and auth**

```python
# backend/tests/test_core.py
import pytest
from app.core.encryption import encrypt_value, decrypt_value
from app.core.auth import hash_password, verify_password, create_access_token, decode_access_token


def test_encrypt_decrypt_roundtrip():
    plaintext = "my-secret-password"
    encrypted = encrypt_value(plaintext)
    assert encrypted != plaintext
    assert decrypt_value(encrypted) == plaintext


def test_password_hash_and_verify():
    password = "testpassword123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_create_and_decode():
    token = create_access_token(user_id=42)
    payload = decode_access_token(token)
    assert payload["sub"] == 42
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_core.py -v`
Expected: ImportError

**Step 3: Implement `backend/app/core/encryption.py`**

```python
from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib


def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_value(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
```

**Step 4: Implement `backend/app/core/auth.py`**

```python
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": expire}, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
```

**Step 5: Create empty `backend/app/core/__init__.py`**

**Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_core.py -v`
Expected: 3 passed

**Step 7: Commit**

```bash
git add backend/app/core/ backend/tests/test_core.py
git commit -m "feat: add encryption, password hashing, and JWT utilities"
```

---

### Task 5: Auth API endpoints (setup, login, me)

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/deps.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_auth.py`

**Step 1: Create Pydantic schemas `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel


class SetupRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = {"from_attributes": True}
```

**Step 2: Create dependency for getting current user `backend/app/api/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_access_token
from app.database import get_db
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
```

**Step 3: Create auth routes `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password, create_access_token
from app.database import get_db
from app.models.user import User
from app.schemas.auth import SetupRequest, LoginRequest, TokenResponse, UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/setup", response_model=TokenResponse)
async def setup(req: SetupRequest, db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(func.count()).select_from(User))
    if count > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setup already completed")
    user = User(username=req.username, password_hash=hash_password(req.password), is_admin=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return user
```

**Step 4: Register router in `backend/app/main.py`**

Add after app creation:
```python
from app.api.auth import router as auth_router
app.include_router(auth_router)
```

**Step 5: Write integration tests `backend/tests/test_auth.py`**

These tests use httpx + an in-memory SQLite database for speed. Create a `backend/tests/conftest.py` first:

```python
# backend/tests/conftest.py
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

```python
# backend/tests/test_auth.py
import pytest


@pytest.mark.asyncio
async def test_setup_creates_admin(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_setup_only_works_once(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin2", "password": "pass123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "pass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me(client):
    setup = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    token = setup.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["is_admin"] is True
```

**Step 6: Run tests**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: 5 passed

**Step 7: Commit**

```bash
git add backend/app/schemas/ backend/app/api/ backend/tests/
git commit -m "feat: add auth endpoints (setup, login, me)"
```

---

### Task 6: User management API (admin-only)

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/api/users.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_users.py`

**Step 1: Create schemas `backend/app/schemas/user.py`**

```python
from pydantic import BaseModel
from typing import Optional


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    is_admin: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    model_config = {"from_attributes": True}
```

**Step 2: Create routes `backend/app/api/users.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import CreateUserRequest, UpdateUserRequest, UserResponse
from app.api.deps import get_admin_user

router = APIRouter(prefix="/api/v1/users", tags=["users"], dependencies=[Depends(get_admin_user)])


@router.get("", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(req: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(username=req.username, password_hash=hash_password(req.password), is_admin=req.is_admin)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, req: UpdateUserRequest, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.is_admin is not None:
        user.is_admin = req.is_admin
    if req.password is not None:
        user.password_hash = hash_password(req.password)
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    await db.delete(user)
    await db.commit()
```

**Step 3: Register router in `backend/app/main.py`**

```python
from app.api.users import router as users_router
app.include_router(users_router)
```

**Step 4: Write tests `backend/tests/test_users.py`**

```python
import pytest


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_user(client, admin_token):
    resp = await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    assert resp.status_code == 201
    assert resp.json()["username"] == "user1"
    assert resp.json()["is_admin"] is False


@pytest.mark.asyncio
async def test_list_users(client, admin_token):
    await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    resp = await client.get("/api/v1/users", headers=auth(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 2  # admin + user1


@pytest.mark.asyncio
async def test_non_admin_cannot_create_user(client, admin_token):
    resp = await client.post("/api/v1/users", json={"username": "user1", "password": "pass"}, headers=auth(admin_token))
    login = await client.post("/api/v1/auth/login", json={"username": "user1", "password": "pass"})
    user_token = login.json()["access_token"]
    resp = await client.post("/api/v1/users", json={"username": "user2", "password": "pass"}, headers=auth(user_token))
    assert resp.status_code == 403
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_users.py -v`
Expected: 3 passed

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add admin-only user management API"
```

---

## Phase 3: Email Account & LLM Config APIs

### Task 7: Email account CRUD and IMAP folder listing

**Files:**
- Create: `backend/app/schemas/email_account.py`
- Create: `backend/app/api/accounts.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_accounts.py`

**Step 1: Create schemas `backend/app/schemas/email_account.py`**

```python
from pydantic import BaseModel
from typing import Optional


class CreateAccountRequest(BaseModel):
    name: str
    imap_host: str
    imap_port: int = 993
    imap_user: str
    imap_password: str
    use_ssl: bool = True
    polling_interval_sec: int = 120


class UpdateAccountRequest(BaseModel):
    name: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    use_ssl: Optional[bool] = None
    polling_interval_sec: Optional[int] = None
    is_active: Optional[bool] = None


class AccountResponse(BaseModel):
    id: int
    name: str
    imap_host: str
    imap_port: int
    imap_user: str
    use_ssl: bool
    polling_interval_sec: int
    is_active: bool

    model_config = {"from_attributes": True}


class WatchFolderRequest(BaseModel):
    folder_path: str


class WatchedFolderResponse(BaseModel):
    id: int
    folder_path: str
    last_seen_uid: int

    model_config = {"from_attributes": True}
```

**Step 2: Create routes `backend/app/api/accounts.py`**

```python
import imaplib
import ssl

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.user import User
from app.models.email_account import EmailAccount, WatchedFolder
from app.schemas.email_account import (
    CreateAccountRequest, UpdateAccountRequest, AccountResponse,
    WatchFolderRequest, WatchedFolderResponse,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
async def list_accounts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailAccount).where(EmailAccount.user_id == user.id))
    return result.scalars().all()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(req: CreateAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = EmailAccount(
        user_id=user.id,
        name=req.name,
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        imap_user=req.imap_user,
        imap_password_encrypted=encrypt_value(req.imap_password),
        use_ssl=req.use_ssl,
        polling_interval_sec=req.polling_interval_sec,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, req: UpdateAccountRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "imap_password" and value is not None:
            account.imap_password_encrypted = encrypt_value(value)
        elif hasattr(account, field):
            setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


@router.post("/{account_id}/test")
async def test_connection(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        password = decrypt_value(account.imap_password_encrypted)
        if account.use_ssl:
            mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            mail = imaplib.IMAP4(account.imap_host, account.imap_port)
        mail.login(account.imap_user, password)
        mail.logout()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{account_id}/folders", response_model=list[str])
async def list_folders(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    try:
        password = decrypt_value(account.imap_password_encrypted)
        if account.use_ssl:
            mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
        else:
            mail = imaplib.IMAP4(account.imap_host, account.imap_port)
        mail.login(account.imap_user, password)
        status_code, folder_list = mail.list()
        mail.logout()
        folders = []
        for item in folder_list:
            decoded = item.decode() if isinstance(item, bytes) else item
            # Parse IMAP folder list response: (\\HasNoChildren) "/" "INBOX"
            parts = decoded.rsplit('" "', 1)
            if len(parts) == 2:
                folders.append(parts[1].strip('"'))
            else:
                parts = decoded.rsplit(" ", 1)
                folders.append(parts[-1].strip('"'))
        return folders
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list folders: {e}")


# --- Watched Folders ---

@router.get("/{account_id}/folders/watched", response_model=list[WatchedFolderResponse])
async def list_watched(account_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await db.execute(select(WatchedFolder).where(WatchedFolder.account_id == account_id))
    return result.scalars().all()


@router.post("/{account_id}/folders/watched", response_model=WatchedFolderResponse, status_code=status.HTTP_201_CREATED)
async def add_watched(account_id: int, req: WatchFolderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = WatchedFolder(account_id=account_id, folder_path=req.folder_path)
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/{account_id}/folders/watched/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watched(account_id: int, folder_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(EmailAccount, account_id)
    if not account or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    folder = await db.get(WatchedFolder, folder_id)
    if not folder or folder.account_id != account_id:
        raise HTTPException(status_code=404, detail="Folder not found")
    await db.delete(folder)
    await db.commit()
```

**Step 3: Register router, write tests, run, commit**

Register in `main.py`, write CRUD tests similar to Task 6 pattern, verify passing.

```bash
git add backend/
git commit -m "feat: add email account CRUD and IMAP folder listing"
```

---

### Task 8: LLM config API (admin-only)

**Files:**
- Create: `backend/app/schemas/llm_config.py`
- Create: `backend/app/api/llm.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_llm_config.py`

**Step 1: Create schemas `backend/app/schemas/llm_config.py`**

```python
from pydantic import BaseModel
from typing import Optional


class LLMConfigRequest(BaseModel):
    provider: str  # e.g. "openai", "ollama", "anthropic"
    model_name: str  # e.g. "gpt-4o", "llama3", "claude-sonnet-4-5-20250929"
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None


class LLMConfigResponse(BaseModel):
    id: int
    provider: str
    model_name: str
    api_base_url: str
    is_active: bool
    has_api_key: bool  # don't expose the actual key

    model_config = {"from_attributes": True}
```

**Step 2: Create routes `backend/app/api/llm.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import litellm

from app.core.encryption import encrypt_value, decrypt_value
from app.database import get_db
from app.models.llm_config import LLMConfig
from app.models.user import User
from app.schemas.llm_config import LLMConfigRequest, LLMConfigResponse
from app.api.deps import get_admin_user

router = APIRouter(prefix="/api/v1/llm", tags=["llm"], dependencies=[Depends(get_admin_user)])


@router.get("/config", response_model=LLMConfigResponse | None)
async def get_config(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None
    return LLMConfigResponse(
        id=config.id, provider=config.provider, model_name=config.model_name,
        api_base_url=config.api_base_url, is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
    )


@router.put("/config", response_model=LLMConfigResponse)
async def update_config(req: LLMConfigRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        config = LLMConfig(provider=req.provider, model_name=req.model_name)
        db.add(config)
    else:
        config.provider = req.provider
        config.model_name = req.model_name
    if req.api_key is not None:
        config.api_key_encrypted = encrypt_value(req.api_key)
    if req.api_base_url is not None:
        config.api_base_url = req.api_base_url
    config.is_active = True
    await db.commit()
    await db.refresh(config)
    return LLMConfigResponse(
        id=config.id, provider=config.provider, model_name=config.model_name,
        api_base_url=config.api_base_url, is_active=config.is_active,
        has_api_key=bool(config.api_key_encrypted),
    )


@router.post("/test")
async def test_llm(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=400, detail="No LLM configured")
    try:
        api_key = decrypt_value(config.api_key_encrypted) if config.api_key_encrypted else None
        model = f"{config.provider}/{config.model_name}" if config.provider != "openai" else config.model_name
        response = await litellm.acompletion(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            api_key=api_key,
            api_base=config.api_base_url or None,
            max_tokens=5,
        )
        return {"success": True, "response": response.choices[0].message.content}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 3: Register router, write tests, run, commit**

```bash
git add backend/
git commit -m "feat: add admin-only LLM config API"
```

---

## Phase 4: Core Email Processing

### Task 9: LLM service (email analysis)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/llm_service.py`
- Create: `backend/tests/test_llm_service.py`

**Step 1: Create `backend/app/services/llm_service.py`**

```python
import json
import litellm
from pydantic import BaseModel, ValidationError
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.llm_config import LLMConfig


class EmailItem(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None


class EmailAnalysis(BaseModel):
    is_relevant: bool
    email_type: Optional[str] = None  # order_confirmation, shipment_confirmation, shipment_update, delivery_confirmation
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_domain: Optional[str] = None
    status: Optional[str] = None
    order_date: Optional[str] = None
    estimated_delivery: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    items: Optional[list[EmailItem]] = None


SYSTEM_PROMPT = """You are an email analysis assistant. Analyze the provided email and extract purchase/shipping information.

Return ONLY valid JSON matching this schema:
{
  "is_relevant": true/false,
  "email_type": "order_confirmation" | "shipment_confirmation" | "shipment_update" | "delivery_confirmation",
  "order_number": "string or null",
  "tracking_number": "string or null",
  "carrier": "string or null",
  "vendor_name": "string or null",
  "vendor_domain": "string or null",
  "status": "ordered" | "shipment_preparing" | "shipped" | "in_transit" | "out_for_delivery" | "delivered",
  "order_date": "YYYY-MM-DD or null",
  "estimated_delivery": "YYYY-MM-DD or null",
  "total_amount": number or null,
  "currency": "string or null",
  "items": [{"name": "string", "quantity": number, "price": number or null}] or null
}

If the email is NOT related to a purchase order or shipment, return: {"is_relevant": false}
Do not include any text outside the JSON object."""


async def analyze_email(subject: str, sender: str, body: str, db: AsyncSession) -> tuple[EmailAnalysis | None, dict]:
    """Analyze an email using the configured LLM. Returns (parsed_result, raw_response_dict)."""
    result = await db.execute(select(LLMConfig).where(LLMConfig.is_active == True))
    config = result.scalar_one_or_none()
    if not config:
        return None, {"error": "No LLM configured"}

    api_key = decrypt_value(config.api_key_encrypted) if config.api_key_encrypted else None
    model = f"{config.provider}/{config.model_name}" if config.provider != "openai" else config.model_name

    user_message = f"Subject: {subject}\nFrom: {sender}\n\n{body}"

    for attempt in range(2):
        try:
            response = await litellm.acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                api_key=api_key,
                api_base=config.api_base_url or None,
                response_format={"type": "json_object"},
            )
            raw_text = response.choices[0].message.content
            raw_dict = json.loads(raw_text)
            parsed = EmailAnalysis.model_validate(raw_dict)
            return parsed, raw_dict
        except (json.JSONDecodeError, ValidationError):
            if attempt == 0:
                continue  # retry once
            return None, {"error": "Failed to parse LLM response", "raw": raw_text if 'raw_text' in dir() else None}
        except Exception as e:
            return None, {"error": str(e)}
```

**Step 2: Write unit tests with mocked LLM responses**

Test the parsing/validation logic by mocking `litellm.acompletion`. Test cases: relevant order email, irrelevant email, malformed JSON response.

**Step 3: Run tests, commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add LLM email analysis service"
```

---

### Task 10: Order matcher service

**Files:**
- Create: `backend/app/services/order_matcher.py`
- Create: `backend/tests/test_order_matcher.py`

**Step 1: Create `backend/app/services/order_matcher.py`**

```python
from datetime import timedelta
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.services.llm_service import EmailAnalysis


async def find_matching_order(analysis: EmailAnalysis, user_id: int, db: AsyncSession) -> Order | None:
    """Find an existing order that matches the email analysis result."""

    # Priority 1: exact order_number match
    if analysis.order_number:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id, Order.order_number == analysis.order_number)
        )
        order = result.scalar_one_or_none()
        if order:
            return order

    # Priority 2: exact tracking_number match
    if analysis.tracking_number:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id, Order.tracking_number == analysis.tracking_number)
        )
        order = result.scalar_one_or_none()
        if order:
            return order

    # Priority 3: fuzzy match - same vendor_domain + time proximity
    if analysis.vendor_domain:
        result = await db.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.vendor_domain == analysis.vendor_domain,
            ).order_by(Order.created_at.desc()).limit(5)
        )
        candidates = result.scalars().all()

        if analysis.items and candidates:
            email_item_names = {item.name.lower() for item in analysis.items if item.name}
            for candidate in candidates:
                if candidate.items:
                    order_item_names = {item.get("name", "").lower() for item in candidate.items}
                    overlap = email_item_names & order_item_names
                    if overlap:
                        return candidate

    return None
```

**Step 2: Write tests with in-memory DB, creating test orders and checking matching logic**

Test cases:
- Match by exact order number
- Match by exact tracking number
- Fuzzy match by vendor domain + item overlap
- No match returns None

**Step 3: Run tests, commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add order matching service"
```

---

### Task 11: Email processor service (orchestrator)

**Files:**
- Create: `backend/app/services/email_processor.py`
- Create: `backend/tests/test_email_processor.py`

**Step 1: Create `backend/app/services/email_processor.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderEvent
from app.services.llm_service import analyze_email, EmailAnalysis
from app.services.order_matcher import find_matching_order


async def process_email(
    subject: str,
    sender: str,
    body: str,
    message_id: str,
    email_uid: int,
    folder_path: str,
    account_id: int,
    user_id: int,
    db: AsyncSession,
) -> Order | None:
    """Process a single email: analyze with LLM, match/create order, log event."""

    # Dedup: check if this message_id was already processed
    existing = await db.execute(
        select(OrderEvent).where(OrderEvent.source_email_message_id == message_id)
    )
    if existing.scalar_one_or_none():
        return None

    # Analyze with LLM
    analysis, raw_response = await analyze_email(subject, sender, body, db)
    if analysis is None or not analysis.is_relevant:
        return None

    # Find matching order or create new one
    order = await find_matching_order(analysis, user_id, db)
    old_status = order.status if order else None

    if order:
        # Update existing order
        event_type = "status_update"
        if analysis.tracking_number and not order.tracking_number:
            order.tracking_number = analysis.tracking_number
            event_type = "shipment_added"
        if analysis.carrier and not order.carrier:
            order.carrier = analysis.carrier
        if analysis.estimated_delivery:
            order.estimated_delivery = analysis.estimated_delivery
        if analysis.status:
            order.status = analysis.status
    else:
        # Create new order
        event_type = "order_confirmed"
        order = Order(
            user_id=user_id,
            order_number=analysis.order_number,
            tracking_number=analysis.tracking_number,
            carrier=analysis.carrier,
            vendor_name=analysis.vendor_name,
            vendor_domain=analysis.vendor_domain,
            status=analysis.status or "ordered",
            order_date=analysis.order_date,
            total_amount=analysis.total_amount,
            currency=analysis.currency,
            items=[item.model_dump() for item in analysis.items] if analysis.items else None,
            estimated_delivery=analysis.estimated_delivery,
        )
        db.add(order)
        await db.flush()

    # Log event
    event = OrderEvent(
        order_id=order.id,
        event_type=event_type,
        old_status=old_status,
        new_status=order.status,
        source_email_message_id=message_id,
        source_email_uid=email_uid,
        source_folder=folder_path,
        source_account_id=account_id,
        llm_raw_response=raw_response,
    )
    db.add(event)
    await db.commit()
    await db.refresh(order)
    return order
```

**Step 2: Write integration tests with mocked LLM, verifying the full create/update/dedup flow**

**Step 3: Run tests, commit**

```bash
git add backend/app/services/ backend/tests/
git commit -m "feat: add email processor orchestrator"
```

---

### Task 12: IMAP worker (background email monitoring)

**Files:**
- Create: `backend/app/services/imap_worker.py`
- Modify: `backend/app/main.py`

**Step 1: Create `backend/app/services/imap_worker.py`**

```python
import asyncio
import email
import logging
from email.header import decode_header

import html2text
from aioimaplib import IMAP4_SSL
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.email_account import EmailAccount, WatchedFolder
from app.services.email_processor import process_email

logger = logging.getLogger(__name__)
h2t = html2text.HTML2Text()
h2t.ignore_links = False

_running_tasks: dict[int, asyncio.Task] = {}


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
            elif content_type == "text/html":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return h2t.handle(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        text = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            return h2t.handle(text)
        return text
    return ""


async def _watch_folder(account_id: int, folder_id: int):
    """Watch a single IMAP folder for new messages using IDLE + polling fallback."""
    while True:
        try:
            async with async_session() as db:
                account = await db.get(EmailAccount, account_id)
                folder = await db.get(WatchedFolder, folder_id)
                if not account or not folder or not account.is_active:
                    logger.info(f"Stopping watcher for folder {folder_id}: account/folder removed or inactive")
                    return

                from app.core.encryption import decrypt_value
                password = decrypt_value(account.imap_password_encrypted)

                imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
                await imap.wait_hello_from_server()
                await imap.login(account.imap_user, password)
                await imap.select(folder.folder_path)

                # Fetch new messages since last seen UID
                search_criteria = f"UID {folder.last_seen_uid + 1}:*"
                _, data = await imap.uid_search(search_criteria)
                uids = data[0].split() if data[0] else []

                for uid_bytes in uids:
                    uid = int(uid_bytes)
                    if uid <= folder.last_seen_uid:
                        continue

                    _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue

                    raw_email = msg_data[0]
                    # aioimaplib returns bytes directly
                    if isinstance(raw_email, (list, tuple)):
                        raw_email = raw_email[-1] if len(raw_email) > 1 else raw_email[0]
                    if isinstance(raw_email, bytes):
                        msg = email.message_from_bytes(raw_email)
                    else:
                        continue

                    subject = _decode_header_value(msg.get("Subject", ""))
                    sender = _decode_header_value(msg.get("From", ""))
                    message_id = msg.get("Message-ID", "")
                    body = _extract_body(msg)

                    await process_email(
                        subject=subject,
                        sender=sender,
                        body=body,
                        message_id=message_id,
                        email_uid=uid,
                        folder_path=folder.folder_path,
                        account_id=account_id,
                        user_id=account.user_id,
                        db=db,
                    )

                    folder.last_seen_uid = uid
                    await db.commit()

                # Try IDLE, fall back to polling
                try:
                    idle_task = await imap.idle_start(timeout=account.polling_interval_sec)
                    await asyncio.wait_for(idle_task, timeout=account.polling_interval_sec)
                except (asyncio.TimeoutError, Exception):
                    pass
                finally:
                    try:
                        await imap.idle_done()
                    except Exception:
                        pass
                    try:
                        await imap.logout()
                    except Exception:
                        pass

        except asyncio.CancelledError:
            logger.info(f"Watcher cancelled for folder {folder_id}")
            return
        except Exception as e:
            logger.error(f"Error watching folder {folder_id}: {e}")
            await asyncio.sleep(30)  # wait before retry on error


async def start_all_watchers():
    """Start watchers for all active accounts and their watched folders."""
    async with async_session() as db:
        result = await db.execute(
            select(WatchedFolder)
            .join(EmailAccount)
            .where(EmailAccount.is_active == True)
        )
        folders = result.scalars().all()
        for folder in folders:
            key = folder.id
            if key not in _running_tasks:
                task = asyncio.create_task(_watch_folder(folder.account_id, folder.id))
                _running_tasks[key] = task
                logger.info(f"Started watcher for folder {folder.id} (account {folder.account_id})")


async def stop_all_watchers():
    """Stop all running watchers."""
    for key, task in _running_tasks.items():
        task.cancel()
    _running_tasks.clear()


async def restart_watchers():
    """Restart all watchers (call after account/folder changes)."""
    await stop_all_watchers()
    await start_all_watchers()
```

**Step 2: Update `backend/app/main.py` lifespan to start/stop watchers**

```python
from app.services.imap_worker import start_all_watchers, stop_all_watchers

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await start_all_watchers()
    yield
    await stop_all_watchers()
```

**Step 3: Commit**

```bash
git add backend/
git commit -m "feat: add IMAP worker with IDLE + polling"
```

---

## Phase 5: Orders API

### Task 13: Orders API endpoints

**Files:**
- Create: `backend/app/schemas/order.py`
- Create: `backend/app/api/orders.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_orders.py`

**Step 1: Create schemas `backend/app/schemas/order.py`**

```python
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class OrderItemSchema(BaseModel):
    name: str
    quantity: int = 1
    price: Optional[float] = None


class OrderResponse(BaseModel):
    id: int
    order_number: Optional[str]
    tracking_number: Optional[str]
    carrier: Optional[str]
    vendor_name: Optional[str]
    vendor_domain: Optional[str]
    status: str
    order_date: Optional[date]
    total_amount: Optional[Decimal]
    currency: Optional[str]
    items: Optional[list[dict]]
    estimated_delivery: Optional[date]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderEventResponse(BaseModel):
    id: int
    event_type: str
    old_status: Optional[str]
    new_status: str
    source_email_message_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    events: list[OrderEventResponse]


class UpdateOrderRequest(BaseModel):
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_name: Optional[str] = None
    status: Optional[str] = None


class LinkOrderRequest(BaseModel):
    target_order_id: int
```

**Step 2: Create routes `backend/app/api/orders.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.order import Order, OrderEvent
from app.schemas.order import OrderResponse, OrderDetailResponse, UpdateOrderRequest, LinkOrderRequest
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Order).where(Order.user_id == user.id).order_by(Order.updated_at.desc())
    if status:
        query = query.where(Order.status == status)
    if search:
        query = query.where(
            (Order.order_number.icontains(search))
            | (Order.vendor_name.icontains(search))
            | (Order.tracking_number.icontains(search))
        )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id).options(selectinload(Order.events))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(order_id: int, req: UpdateOrderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/link")
async def link_orders(order_id: int, req: LinkOrderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    source = await db.get(Order, order_id)
    target = await db.get(Order, req.target_order_id)
    if not source or source.user_id != user.id or not target or target.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    # Merge: copy tracking info from target into source, delete target
    if target.tracking_number and not source.tracking_number:
        source.tracking_number = target.tracking_number
    if target.carrier and not source.carrier:
        source.carrier = target.carrier
    if target.status and target.status != "ordered":
        source.status = target.status
    # Move events from target to source
    result = await db.execute(select(OrderEvent).where(OrderEvent.order_id == target.id))
    for event in result.scalars().all():
        event.order_id = source.id
    await db.delete(target)
    await db.commit()
    await db.refresh(source)
    return {"merged_into": source.id}


@router.delete("/{order_id}", status_code=204)
async def delete_order(order_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    await db.delete(order)
    await db.commit()
```

**Step 3: Register router, write tests, run, commit**

```bash
git add backend/
git commit -m "feat: add orders API with search, detail, manual edit, and linking"
```

---

### Task 14: System status API

**Files:**
- Create: `backend/app/api/system.py`
- Modify: `backend/app/main.py`

**Step 1: Create `backend/app/api/system.py`**

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_admin_user
from app.services.imap_worker import _running_tasks

router = APIRouter(prefix="/api/v1/system", tags=["system"], dependencies=[Depends(get_admin_user)])


@router.get("/status")
async def system_status():
    workers = []
    for folder_id, task in _running_tasks.items():
        workers.append({
            "folder_id": folder_id,
            "running": not task.done(),
            "error": str(task.exception()) if task.done() and task.exception() else None,
        })
    return {"workers": workers, "total_workers": len(workers)}
```

**Step 2: Register router, commit**

```bash
git add backend/
git commit -m "feat: add system status API"
```

---

## Phase 6: Frontend

### Task 15: Vue 3 project scaffolding

**Step 1: Create Vue project with Vite inside Docker**

Create `frontend/Dockerfile`:
```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

Scaffold Vue project using: `docker run --rm -v ./frontend:/app -w /app node:20-alpine sh -c "npm create vue@latest . -- --typescript --router --pinia && npm install && npm install tailwindcss @tailwindcss/vite axios"`

**Step 2: Configure Tailwind with Vite plugin, set up Vite proxy for `/api` → backend**

In `vite.config.ts`:
```typescript
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://backend:8000',
    },
  },
})
```

**Step 3: Add frontend to `docker-compose.yml`**

```yaml
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
```

**Step 4: Verify `docker compose up` starts all 3 services**

**Step 5: Commit**

```bash
git add frontend/ docker-compose.yml
git commit -m "feat: scaffold Vue 3 frontend with Tailwind"
```

---

### Task 16: API client and auth store

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/stores/auth.ts`

**Step 1: Create API client `frontend/src/api/client.ts`**

```typescript
import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default api
```

**Step 2: Create auth store `frontend/src/stores/auth.ts`**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<{ id: number; username: string; is_admin: boolean } | null>(null)
  const token = ref(localStorage.getItem('token'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.is_admin ?? false)

  async function login(username: string, password: string) {
    const res = await api.post('/auth/login', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    await fetchUser()
  }

  async function setup(username: string, password: string) {
    const res = await api.post('/auth/setup', { username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', res.data.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    const res = await api.get('/auth/me')
    user.value = res.data
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return { user, token, isLoggedIn, isAdmin, login, setup, fetchUser, logout }
})
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add API client and auth store"
```

---

### Task 17: Login and Setup views

**Files:**
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/SetupView.vue`
- Modify: `frontend/src/router/index.ts`

**Step 1: Create login and setup views with forms (username/password inputs, submit button)**

**Step 2: Configure router with auth guards - redirect to `/setup` if no users, `/login` if not authenticated**

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add login and setup views"
```

---

### Task 18: Dashboard view

**Files:**
- Create: `frontend/src/views/DashboardView.vue`
- Create: `frontend/src/stores/orders.ts`

**Step 1: Create orders store that fetches from `/api/v1/orders`**

**Step 2: Create dashboard with status count cards (ordered/shipped/in transit/delivered) and recent orders table**

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add dashboard with order status overview"
```

---

### Task 19: Orders list and detail views

**Files:**
- Create: `frontend/src/views/OrdersView.vue`
- Create: `frontend/src/views/OrderDetailView.vue`
- Create: `frontend/src/components/StatusBadge.vue`

**Step 1: Create orders list with status filter tabs, search bar, and sortable table**

**Step 2: Create order detail view showing all fields + event timeline**

**Step 3: Create reusable StatusBadge component with color coding per status**

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add orders list and detail views"
```

---

### Task 20: Email accounts management view

**Files:**
- Create: `frontend/src/views/AccountsView.vue`
- Create: `frontend/src/components/AccountForm.vue`
- Create: `frontend/src/components/FolderSelector.vue`
- Create: `frontend/src/stores/accounts.ts`

**Step 1: Create accounts store**

**Step 2: Create account form (add/edit) with IMAP fields + test connection button**

**Step 3: Create folder selector that loads available folders from API, shows checkboxes to watch/unwatch**

**Step 4: Create accounts view combining list + form + folder management**

**Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add email accounts management UI"
```

---

### Task 21: Admin views (users, LLM config, system)

**Files:**
- Create: `frontend/src/views/admin/UsersView.vue`
- Create: `frontend/src/views/admin/LLMConfigView.vue`
- Create: `frontend/src/views/admin/SystemView.vue`

**Step 1: Create users view - table of users, add user form, toggle admin role, delete**

**Step 2: Create LLM config view - form with provider/model/API key/base URL, test button**

**Step 3: Create system view - list of running IMAP workers with status**

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add admin views (users, LLM config, system)"
```

---

### Task 22: App layout, navigation, and settings

**Files:**
- Create: `frontend/src/components/AppLayout.vue`
- Create: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/router/index.ts`

**Step 1: Create AppLayout with sidebar navigation (Dashboard, Orders, Accounts, Settings, Admin section for admins)**

**Step 2: Create settings view with password change form**

**Step 3: Wire up all routes in router**

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app layout, navigation, and settings"
```

---

## Phase 7: Production Docker Setup

### Task 23: Production Docker Compose

**Files:**
- Modify: `backend/Dockerfile` (multi-stage build)
- Create: `frontend/Dockerfile.prod` (build + nginx)
- Create: `frontend/nginx.conf`
- Create: `docker-compose.prod.yml`

**Step 1: Create production backend Dockerfile (no --reload, no volume mounts)**

**Step 2: Create production frontend Dockerfile - build Vue app, serve with nginx**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**Step 3: Create nginx.conf that proxies `/api` to backend and serves SPA for all other routes**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Step 4: Create `docker-compose.prod.yml`**

**Step 5: Verify `docker compose -f docker-compose.prod.yml up --build` works end to end**

**Step 6: Commit**

```bash
git add .
git commit -m "feat: add production Docker Compose setup"
```

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| 1 | 1-3 | Project scaffolding, Docker, database models |
| 2 | 4-6 | Auth, JWT, user management |
| 3 | 7-8 | Email accounts CRUD, LLM config |
| 4 | 9-12 | LLM analysis, order matching, email processor, IMAP worker |
| 5 | 13-14 | Orders API, system status |
| 6 | 15-22 | Vue frontend (all views) |
| 7 | 23 | Production Docker setup |

Total: 23 tasks across 7 phases. Each task is independently committable and testable.
