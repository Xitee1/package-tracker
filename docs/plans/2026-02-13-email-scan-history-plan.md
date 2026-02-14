# Email Scan History Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a scan history feature that records every email processed, shows LLM results as JSON, allows fetching original emails from IMAP, supports rescan, and introduces a centralized APScheduler-based task scheduler with automatic history cleanup.

**Architecture:** New `EmailScan` model records every processed email (relevant or not). Dedup moves from `OrderEvent.source_email_message_id` to `EmailScan.message_id`. APScheduler 4 (async) handles scheduled tasks with PostgreSQL persistence. New `/api/v1/scan-history` endpoints + `HistoryView.vue` frontend.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, APScheduler 4, Vue 3 Composition API, Pinia, Tailwind CSS 4

**Design doc:** `docs/plans/2026-02-13-email-scan-history-design.md`

---

### Task 1: Add APScheduler dependency

**Files:**
- Modify: `backend/pyproject.toml`

**Step 1: Add apscheduler to dependencies**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
"apscheduler[sqlalchemy]>=4.0.0",
```

**Step 2: Install dependencies**

Run: `cd backend && pip install -e ".[dev]"`

**Step 3: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: add APScheduler dependency"
```

---

### Task 2: EmailScan + ScanHistorySettings models

**Files:**
- Create: `backend/app/models/email_scan.py`
- Create: `backend/app/models/scan_history_settings.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create EmailScan model**

Create `backend/app/models/email_scan.py`:

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmailScan(Base):
    __tablename__ = "email_scans"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE")
    )
    folder_path: Mapped[str] = mapped_column(String(512))
    email_uid: Mapped[int] = mapped_column(Integer)
    message_id: Mapped[str] = mapped_column(String(512), index=True)
    subject: Mapped[str] = mapped_column(String(1024), default="")
    sender: Mapped[str] = mapped_column(String(512), default="")
    email_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_relevant: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_raw_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    rescan_queued: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account = relationship("EmailAccount")
    order = relationship("Order")
```

**Step 2: Create ScanHistorySettings model**

Create `backend/app/models/scan_history_settings.py`:

```python
from sqlalchemy import Integer, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ScanHistorySettings(Base):
    __tablename__ = "scan_history_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=7)
    max_per_user: Mapped[int] = mapped_column(Integer, default=1000)
    cleanup_interval_hours: Mapped[float] = mapped_column(Float, default=1.0)
```

**Step 3: Update model exports**

In `backend/app/models/__init__.py`, add:

```python
from app.models.email_scan import EmailScan
from app.models.scan_history_settings import ScanHistorySettings
```

And add both to `__all__`.

**Step 4: Create Alembic migration**

Run: `cd backend && alembic revision --autogenerate -m "add email_scans and scan_history_settings tables"`

Review the generated migration file to verify it creates both tables correctly.

**Step 5: Apply migration**

Run: `cd backend && alembic upgrade head`

**Step 6: Verify tests still pass**

Run: `cd backend && pytest tests/ -v`

Tests use in-memory SQLite with `Base.metadata.create_all`, so new tables are auto-created.

**Step 7: Commit**

```bash
git add backend/app/models/email_scan.py backend/app/models/scan_history_settings.py backend/app/models/__init__.py backend/alembic/versions/
git commit -m "feat: add EmailScan and ScanHistorySettings models"
```

---

### Task 3: Scan history schemas

**Files:**
- Create: `backend/app/schemas/scan_history.py`

**Step 1: Create Pydantic schemas**

Create `backend/app/schemas/scan_history.py`:

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EmailScanResponse(BaseModel):
    id: int
    account_id: int
    account_name: str | None = None
    folder_path: str
    email_uid: int
    message_id: str
    subject: str
    sender: str
    email_date: datetime | None
    is_relevant: bool
    llm_raw_response: dict | None
    order_id: int | None
    rescan_queued: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailScanListResponse(BaseModel):
    items: list[EmailScanResponse]
    total: int
    page: int
    per_page: int


class EmailContentResponse(BaseModel):
    subject: str
    sender: str
    date: str | None
    body_text: str


class ScanHistorySettingsResponse(BaseModel):
    max_age_days: int
    max_per_user: int
    cleanup_interval_hours: float

    model_config = {"from_attributes": True}


class UpdateScanHistorySettingsRequest(BaseModel):
    max_age_days: int | None = None
    max_per_user: int | None = None
    cleanup_interval_hours: float | None = None
```

**Step 2: Commit**

```bash
git add backend/app/schemas/scan_history.py
git commit -m "feat: add scan history Pydantic schemas"
```

---

### Task 4: Update email_processor.py — dedup + EmailScan creation

**Files:**
- Modify: `backend/app/services/email_processor.py`
- Create: `backend/tests/test_email_processor.py`

**Step 1: Write tests for the updated processor**

Create `backend/tests/test_email_processor.py`:

```python
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models.email_scan import EmailScan
from app.models.order import Order, OrderEvent


@pytest.fixture
async def user_and_account(db_session):
    """Create a test user and email account."""
    from app.models.user import User
    from app.models.email_account import EmailAccount
    from app.core.encryption import encrypt_value

    user = User(username="testuser", password_hash="fakehash", is_admin=False)
    db_session.add(user)
    await db_session.flush()

    account = EmailAccount(
        user_id=user.id,
        name="Test Account",
        imap_host="imap.test.com",
        imap_port=993,
        imap_user="test@test.com",
        imap_password_encrypted=encrypt_value("password"),
    )
    db_session.add(account)
    await db_session.flush()
    return user, account


MOCK_LLM_RELEVANT = {
    "is_relevant": True,
    "email_type": "order_confirmation",
    "order_number": "ORD-123",
    "tracking_number": None,
    "carrier": None,
    "vendor_name": "Amazon",
    "vendor_domain": "amazon.com",
    "status": "ordered",
    "order_date": "2026-01-15",
    "estimated_delivery": None,
    "total_amount": 42.99,
    "currency": "USD",
    "items": [{"name": "Widget", "quantity": 1, "price": 42.99}],
}

MOCK_LLM_NOT_RELEVANT = {
    "is_relevant": False,
}


@pytest.mark.asyncio
@patch("app.services.email_processor.analyze_email")
async def test_creates_email_scan_for_relevant_email(mock_analyze, db_session, user_and_account):
    from app.services.llm_service import EmailAnalysis
    from app.services.email_processor import process_email

    user, account = user_and_account
    analysis = EmailAnalysis(**MOCK_LLM_RELEVANT)
    mock_analyze.return_value = (analysis, MOCK_LLM_RELEVANT)

    order = await process_email(
        subject="Your order confirmed",
        sender="orders@amazon.com",
        body="Order ORD-123 confirmed",
        message_id="<msg1@test.com>",
        email_uid=100,
        folder_path="INBOX",
        account_id=account.id,
        user_id=user.id,
        db=db_session,
    )
    assert order is not None

    result = await db_session.execute(select(EmailScan))
    scan = result.scalar_one()
    assert scan.message_id == "<msg1@test.com>"
    assert scan.subject == "Your order confirmed"
    assert scan.is_relevant is True
    assert scan.order_id == order.id
    assert scan.llm_raw_response == MOCK_LLM_RELEVANT


@pytest.mark.asyncio
@patch("app.services.email_processor.analyze_email")
async def test_creates_email_scan_for_irrelevant_email(mock_analyze, db_session, user_and_account):
    from app.services.email_processor import process_email

    user, account = user_and_account
    mock_analyze.return_value = (None, MOCK_LLM_NOT_RELEVANT)

    order = await process_email(
        subject="Weekly newsletter",
        sender="news@site.com",
        body="This weeks news...",
        message_id="<msg2@test.com>",
        email_uid=101,
        folder_path="INBOX",
        account_id=account.id,
        user_id=user.id,
        db=db_session,
    )
    assert order is None

    result = await db_session.execute(select(EmailScan))
    scan = result.scalar_one()
    assert scan.message_id == "<msg2@test.com>"
    assert scan.subject == "Weekly newsletter"
    assert scan.is_relevant is False
    assert scan.order_id is None
    assert scan.llm_raw_response == MOCK_LLM_NOT_RELEVANT


@pytest.mark.asyncio
@patch("app.services.email_processor.analyze_email")
async def test_dedup_via_email_scan(mock_analyze, db_session, user_and_account):
    """Duplicate message_id should be skipped via EmailScan dedup."""
    from app.services.email_processor import process_email

    user, account = user_and_account

    # Pre-create an EmailScan record for this message_id
    existing = EmailScan(
        account_id=account.id,
        folder_path="INBOX",
        email_uid=100,
        message_id="<dup@test.com>",
        subject="Already scanned",
        sender="test@test.com",
        is_relevant=False,
    )
    db_session.add(existing)
    await db_session.flush()

    order = await process_email(
        subject="Already scanned",
        sender="test@test.com",
        body="Body text",
        message_id="<dup@test.com>",
        email_uid=100,
        folder_path="INBOX",
        account_id=account.id,
        user_id=user.id,
        db=db_session,
    )
    assert order is None
    mock_analyze.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_email_processor.py -v`

Expected: FAIL — `process_email` doesn't create EmailScan entries yet.

**Step 3: Update email_processor.py**

Rewrite `backend/app/services/email_processor.py` to:
- Change dedup check from `OrderEvent` to `EmailScan`
- Create an `EmailScan` row for every email (relevant or not)
- Set `order_id` on the scan if an order was created/matched
- Accept `email_date` parameter (optional)

Key changes:

```python
from app.models.email_scan import EmailScan

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
    email_date: datetime | None = None,
) -> Order | None:
    # Dedup: check EmailScan instead of OrderEvent
    existing = await db.execute(
        select(EmailScan).where(EmailScan.message_id == message_id)
    )
    if existing.scalar_one_or_none():
        return None

    # Analyze with LLM
    analysis, raw_response = await analyze_email(subject, sender, body, db)

    is_relevant = analysis is not None and analysis.is_relevant

    # Create EmailScan record for ALL emails
    scan = EmailScan(
        account_id=account_id,
        folder_path=folder_path,
        email_uid=email_uid,
        message_id=message_id,
        subject=subject,
        sender=sender,
        email_date=email_date,
        is_relevant=is_relevant,
        llm_raw_response=raw_response,
    )
    db.add(scan)

    if not is_relevant:
        await db.commit()
        return None

    # ... existing order matching/creation logic unchanged ...

    # After order is created/matched, link scan to order
    scan.order_id = order.id

    # Log event (keep existing OrderEvent creation)
    event = OrderEvent(...)
    db.add(event)
    await db.commit()
    await db.refresh(order)
    return order
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_email_processor.py -v`

Expected: PASS

**Step 5: Run all existing tests to check for regressions**

Run: `cd backend && pytest tests/ -v`

Expected: All pass. Existing tests don't directly test dedup behavior through OrderEvent.

**Step 6: Commit**

```bash
git add backend/app/services/email_processor.py backend/tests/test_email_processor.py
git commit -m "feat: create EmailScan records for all processed emails, move dedup to EmailScan"
```

---

### Task 5: Scan history API endpoints

**Files:**
- Create: `backend/app/api/scan_history.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_scan_history.py`

**Step 1: Write tests for scan history API**

Create `backend/tests/test_scan_history.py`:

```python
import pytest
from datetime import datetime, timezone

from app.models.email_scan import EmailScan
from app.models.email_account import EmailAccount
from app.models.user import User


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_token(client):
    resp = await client.post("/api/v1/auth/setup", json={"username": "admin", "password": "pass123"})
    return resp.json()["access_token"]


@pytest.fixture
async def admin_user(client, admin_token):
    resp = await client.get("/api/v1/auth/me", headers=auth(admin_token))
    return resp.json()


@pytest.fixture
async def account_with_scans(db_session, admin_user):
    """Create an email account with scan history entries."""
    from app.core.encryption import encrypt_value

    account = EmailAccount(
        user_id=admin_user["id"],
        name="Test Gmail",
        imap_host="imap.gmail.com",
        imap_port=993,
        imap_user="test@gmail.com",
        imap_password_encrypted=encrypt_value("pass"),
    )
    db_session.add(account)
    await db_session.flush()

    scans = []
    for i in range(5):
        scan = EmailScan(
            account_id=account.id,
            folder_path="INBOX",
            email_uid=100 + i,
            message_id=f"<msg{i}@test.com>",
            subject=f"Test email {i}",
            sender=f"sender{i}@test.com",
            email_date=datetime(2026, 2, 13, 10, i, tzinfo=timezone.utc),
            is_relevant=i % 2 == 0,
            llm_raw_response={"is_relevant": i % 2 == 0, "test": True},
        )
        scans.append(scan)
        db_session.add(scan)
    await db_session.commit()
    return account, scans


# --- List ---

@pytest.mark.asyncio
async def test_list_scan_history(client, admin_token, account_with_scans):
    resp = await client.get("/api/v1/scan-history", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5


@pytest.mark.asyncio
async def test_list_scan_history_filter_relevant(client, admin_token, account_with_scans):
    resp = await client.get("/api/v1/scan-history?is_relevant=true", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert all(item["is_relevant"] for item in data["items"])


@pytest.mark.asyncio
async def test_list_scan_history_pagination(client, admin_token, account_with_scans):
    resp = await client.get("/api/v1/scan-history?page=1&per_page=2", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["per_page"] == 2


# --- Detail ---

@pytest.mark.asyncio
async def test_get_scan_detail(client, admin_token, account_with_scans):
    account, scans = account_with_scans
    resp = await client.get(f"/api/v1/scan-history/{scans[0].id}", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["message_id"] == "<msg0@test.com>"
    assert data["llm_raw_response"] == {"is_relevant": True, "test": True}


@pytest.mark.asyncio
async def test_get_scan_not_found(client, admin_token):
    resp = await client.get("/api/v1/scan-history/9999", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Delete ---

@pytest.mark.asyncio
async def test_delete_scan(client, admin_token, account_with_scans):
    account, scans = account_with_scans
    resp = await client.delete(f"/api/v1/scan-history/{scans[0].id}", headers=auth(admin_token))
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/scan-history/{scans[0].id}", headers=auth(admin_token))
    assert resp.status_code == 404


# --- Rescan ---

@pytest.mark.asyncio
async def test_queue_rescan(client, admin_token, account_with_scans):
    account, scans = account_with_scans
    resp = await client.post(f"/api/v1/scan-history/{scans[0].id}/rescan", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["rescan_queued"] is True


# --- User isolation ---

@pytest.mark.asyncio
async def test_user_cannot_see_other_users_scans(client, admin_token, db_session, account_with_scans):
    # Create another user
    await client.post(
        "/api/v1/users",
        json={"username": "user2", "password": "pass"},
        headers=auth(admin_token),
    )
    login = await client.post("/api/v1/auth/login", json={"username": "user2", "password": "pass"})
    user2_token = login.json()["access_token"]

    resp = await client.get("/api/v1/scan-history", headers=auth(user2_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_scan_history.py -v`

Expected: FAIL — router doesn't exist yet.

**Step 3: Create the scan history API router**

Create `backend/app/api/scan_history.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.email_account import EmailAccount
from app.models.email_scan import EmailScan
from app.models.user import User
from app.schemas.scan_history import (
    EmailScanListResponse,
    EmailScanResponse,
)

router = APIRouter(prefix="/api/v1/scan-history", tags=["scan-history"])


def _user_scans_query(user: User):
    """Base query: EmailScans belonging to user's accounts."""
    return (
        select(EmailScan)
        .join(EmailAccount)
        .where(EmailAccount.user_id == user.id)
    )


@router.get("/", response_model=EmailScanListResponse)
async def list_scan_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_relevant: bool | None = None,
    account_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _user_scans_query(user)
    count_query = (
        select(func.count())
        .select_from(EmailScan)
        .join(EmailAccount)
        .where(EmailAccount.user_id == user.id)
    )

    if is_relevant is not None:
        query = query.where(EmailScan.is_relevant == is_relevant)
        count_query = count_query.where(EmailScan.is_relevant == is_relevant)
    if account_id is not None:
        query = query.where(EmailScan.account_id == account_id)
        count_query = count_query.where(EmailScan.account_id == account_id)

    total = (await db.execute(count_query)).scalar()

    query = (
        query
        .options(selectinload(EmailScan.account))
        .order_by(EmailScan.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    scans = result.scalars().all()

    items = []
    for scan in scans:
        item = EmailScanResponse.model_validate(scan)
        item.account_name = scan.account.name if scan.account else None
        items.append(item)

    return EmailScanListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/{scan_id}", response_model=EmailScanResponse)
async def get_scan_detail(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _user_scans_query(user).where(EmailScan.id == scan_id)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return EmailScanResponse.model_validate(scan)


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _user_scans_query(user).where(EmailScan.id == scan_id)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    await db.delete(scan)
    await db.commit()


@router.post("/{scan_id}/rescan", response_model=EmailScanResponse)
async def queue_rescan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = _user_scans_query(user).where(EmailScan.id == scan_id)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan.rescan_queued = True
    await db.commit()
    await db.refresh(scan)
    return EmailScanResponse.model_validate(scan)
```

**Step 4: Register router in main.py**

In `backend/app/main.py`, add:

```python
from app.api.scan_history import router as scan_history_router
app.include_router(scan_history_router)
```

**Step 5: Run tests**

Run: `cd backend && pytest tests/test_scan_history.py -v`

Expected: PASS

**Step 6: Run all tests**

Run: `cd backend && pytest tests/ -v`

Expected: All pass.

**Step 7: Commit**

```bash
git add backend/app/api/scan_history.py backend/app/main.py backend/tests/test_scan_history.py
git commit -m "feat: add scan history API endpoints (list, detail, delete, rescan)"
```

---

### Task 6: IMAP email fetch service + endpoint

**Files:**
- Create: `backend/app/services/imap_service.py`
- Modify: `backend/app/api/scan_history.py` (add email fetch endpoint)
- Add tests to: `backend/tests/test_scan_history.py`

**Step 1: Write test for email fetch endpoint**

Add to `backend/tests/test_scan_history.py`:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
@patch("app.api.scan_history.fetch_email_by_uid")
async def test_fetch_email_content(mock_fetch, client, admin_token, account_with_scans):
    account, scans = account_with_scans
    mock_fetch.return_value = {
        "subject": "Test email 0",
        "sender": "sender0@test.com",
        "date": "2026-02-13T10:00:00+00:00",
        "body_text": "Hello, this is the email body.",
    }
    resp = await client.get(f"/api/v1/scan-history/{scans[0].id}/email", headers=auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["body_text"] == "Hello, this is the email body."


@pytest.mark.asyncio
@patch("app.api.scan_history.fetch_email_by_uid")
async def test_fetch_email_not_on_server(mock_fetch, client, admin_token, account_with_scans):
    account, scans = account_with_scans
    mock_fetch.return_value = None
    resp = await client.get(f"/api/v1/scan-history/{scans[0].id}/email", headers=auth(admin_token))
    assert resp.status_code == 404
```

**Step 2: Create IMAP service**

Create `backend/app/services/imap_service.py`:

```python
import email
import logging
from email.header import decode_header
from datetime import datetime

from aioimaplib import IMAP4_SSL
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_value
from app.models.email_account import EmailAccount
from app.services.imap_worker import _decode_header_value, _extract_body

logger = logging.getLogger(__name__)


async def fetch_email_by_uid(
    account: EmailAccount,
    folder_path: str,
    uid: int,
) -> dict | None:
    """Fetch a single email from IMAP by UID. Returns dict or None if not found."""
    try:
        password = decrypt_value(account.imap_password_encrypted)
        imap = IMAP4_SSL(host=account.imap_host, port=account.imap_port)
        await imap.wait_hello_from_server()
        await imap.login(account.imap_user, password)
        await imap.select(folder_path)

        _, msg_data = await imap.uid("fetch", str(uid), "(RFC822)")
        try:
            await imap.logout()
        except Exception:
            pass

        if not msg_data or not msg_data[0]:
            return None

        raw_email = msg_data[0]
        if isinstance(raw_email, (list, tuple)):
            raw_email = raw_email[-1] if len(raw_email) > 1 else raw_email[0]
        if not isinstance(raw_email, bytes):
            return None

        msg = email.message_from_bytes(raw_email)
        subject = _decode_header_value(msg.get("Subject", ""))
        sender = _decode_header_value(msg.get("From", ""))
        date_str = msg.get("Date", "")
        body = _extract_body(msg)

        return {
            "subject": subject,
            "sender": sender,
            "date": date_str,
            "body_text": body,
        }
    except Exception as e:
        logger.error(f"Failed to fetch email UID {uid} from {folder_path}: {e}")
        return None
```

**Step 3: Add email fetch endpoint to scan_history.py**

Add to `backend/app/api/scan_history.py`:

```python
from app.services.imap_service import fetch_email_by_uid
from app.schemas.scan_history import EmailContentResponse

@router.get("/{scan_id}/email", response_model=EmailContentResponse)
async def get_email_content(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        _user_scans_query(user)
        .where(EmailScan.id == scan_id)
        .options(selectinload(EmailScan.account))
    )
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    content = await fetch_email_by_uid(scan.account, scan.folder_path, scan.email_uid)
    if content is None:
        raise HTTPException(status_code=404, detail="Email no longer available on server")
    return EmailContentResponse(**content)
```

**Step 4: Run tests**

Run: `cd backend && pytest tests/test_scan_history.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/imap_service.py backend/app/api/scan_history.py backend/tests/test_scan_history.py
git commit -m "feat: add IMAP email fetch service and endpoint"
```

---

### Task 7: IMAP worker rescan queue integration

**Files:**
- Modify: `backend/app/services/imap_worker.py`

**Step 1: Add rescan queue processing to `_watch_folder`**

In `backend/app/services/imap_worker.py`, after the normal UID scan loop (after line ~248) and before the IDLE phase, add rescan queue processing:

```python
# Process rescan queue
from app.models.email_scan import EmailScan

rescan_query = (
    select(EmailScan)
    .where(
        EmailScan.account_id == account_id,
        EmailScan.folder_path == folder.folder_path,
        EmailScan.rescan_queued == True,
    )
)
rescan_result = await db.execute(rescan_query)
rescan_items = rescan_result.scalars().all()

for rescan_scan in rescan_items:
    try:
        _, msg_data = await imap.uid("fetch", str(rescan_scan.email_uid), "(RFC822)")
        if not msg_data or not msg_data[0]:
            rescan_scan.rescan_queued = False
            rescan_scan.llm_raw_response = {"error": "Email no longer available on server"}
            await db.commit()
            continue

        raw_email = msg_data[0]
        if isinstance(raw_email, (list, tuple)):
            raw_email = raw_email[-1] if len(raw_email) > 1 else raw_email[0]
        if not isinstance(raw_email, bytes):
            rescan_scan.rescan_queued = False
            await db.commit()
            continue

        msg = email.message_from_bytes(raw_email)
        r_subject = _decode_header_value(msg.get("Subject", ""))
        r_sender = _decode_header_value(msg.get("From", ""))
        r_body = _extract_body(msg)

        # Re-analyze with LLM
        from app.services.llm_service import analyze_email
        analysis, raw_response = await analyze_email(r_subject, r_sender, r_body, db)

        rescan_scan.llm_raw_response = raw_response
        rescan_scan.is_relevant = analysis is not None and analysis.is_relevant
        rescan_scan.rescan_queued = False
        await db.commit()

        # If relevant, run order matching (use existing process_email logic or inline)
        if analysis and analysis.is_relevant:
            from app.services.order_matcher import find_matching_order
            order = await find_matching_order(analysis, account.user_id, db)
            if order:
                rescan_scan.order_id = order.id
                await db.commit()

    except Exception as e:
        logger.error(f"Error rescanning UID {rescan_scan.email_uid}: {e}")
        rescan_scan.rescan_queued = False
        rescan_scan.llm_raw_response = {"error": str(e)}
        await db.commit()
```

**Step 2: Run all tests**

Run: `cd backend && pytest tests/ -v`

Expected: All pass (worker code is mocked in tests).

**Step 3: Commit**

```bash
git add backend/app/services/imap_worker.py
git commit -m "feat: add rescan queue processing to IMAP worker"
```

---

### Task 8: APScheduler setup + history cleanup job

**Files:**
- Create: `backend/app/services/scheduler.py`
- Create: `backend/app/services/history_cleanup.py`
- Modify: `backend/app/main.py` (integrate scheduler into lifespan)
- Create: `backend/tests/test_history_cleanup.py`

**Step 1: Write test for history cleanup**

Create `backend/tests/test_history_cleanup.py`:

```python
import pytest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.email_scan import EmailScan
from app.models.email_account import EmailAccount
from app.models.scan_history_settings import ScanHistorySettings


@pytest.fixture
async def setup_cleanup_data(db_session):
    """Create user, account, settings, and scan entries for cleanup tests."""
    from app.models.user import User
    from app.core.encryption import encrypt_value

    user = User(username="cleaner", password_hash="fakehash", is_admin=False)
    db_session.add(user)
    await db_session.flush()

    account = EmailAccount(
        user_id=user.id,
        name="Cleanup Account",
        imap_host="imap.test.com",
        imap_port=993,
        imap_user="test@test.com",
        imap_password_encrypted=encrypt_value("password"),
    )
    db_session.add(account)
    await db_session.flush()

    settings = ScanHistorySettings(id=1, max_age_days=7, max_per_user=1000, cleanup_interval_hours=1.0)
    db_session.add(settings)

    now = datetime.now(timezone.utc)
    # 3 old scans (10 days old) and 2 recent scans
    for i in range(3):
        db_session.add(EmailScan(
            account_id=account.id, folder_path="INBOX", email_uid=i,
            message_id=f"<old{i}@test>", subject=f"Old {i}", sender="s@t",
            created_at=now - timedelta(days=10),
        ))
    for i in range(2):
        db_session.add(EmailScan(
            account_id=account.id, folder_path="INBOX", email_uid=100 + i,
            message_id=f"<new{i}@test>", subject=f"New {i}", sender="s@t",
            created_at=now,
        ))
    await db_session.commit()
    return user, account


@pytest.mark.asyncio
async def test_cleanup_removes_old_scans(db_session, setup_cleanup_data):
    from app.services.history_cleanup import cleanup_scan_history

    await cleanup_scan_history(db_session)

    result = await db_session.execute(select(EmailScan))
    remaining = result.scalars().all()
    assert len(remaining) == 2
    assert all("New" in s.subject for s in remaining)


@pytest.mark.asyncio
async def test_cleanup_respects_max_per_user(db_session):
    """When max_per_user is exceeded, oldest entries are removed."""
    from app.models.user import User
    from app.core.encryption import encrypt_value
    from app.services.history_cleanup import cleanup_scan_history

    user = User(username="maxuser", password_hash="fakehash", is_admin=False)
    db_session.add(user)
    await db_session.flush()

    account = EmailAccount(
        user_id=user.id, name="Acc", imap_host="h", imap_port=993,
        imap_user="u", imap_password_encrypted=encrypt_value("p"),
    )
    db_session.add(account)
    await db_session.flush()

    settings = ScanHistorySettings(id=1, max_age_days=365, max_per_user=3, cleanup_interval_hours=1.0)
    db_session.add(settings)

    now = datetime.now(timezone.utc)
    for i in range(5):
        db_session.add(EmailScan(
            account_id=account.id, folder_path="INBOX", email_uid=i,
            message_id=f"<m{i}@test>", subject=f"Email {i}", sender="s@t",
            created_at=now - timedelta(hours=5 - i),  # oldest first
        ))
    await db_session.commit()

    await cleanup_scan_history(db_session)

    result = await db_session.execute(
        select(EmailScan).order_by(EmailScan.created_at.desc())
    )
    remaining = result.scalars().all()
    assert len(remaining) == 3
    # Should keep the 3 newest
    assert remaining[0].subject == "Email 4"
    assert remaining[1].subject == "Email 3"
    assert remaining[2].subject == "Email 2"
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_history_cleanup.py -v`

Expected: FAIL — module doesn't exist.

**Step 3: Create history cleanup service**

Create `backend/app/services/history_cleanup.py`:

```python
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_account import EmailAccount
from app.models.email_scan import EmailScan
from app.models.scan_history_settings import ScanHistorySettings
from app.models.user import User

logger = logging.getLogger(__name__)


async def _get_settings(db: AsyncSession) -> ScanHistorySettings | None:
    result = await db.execute(select(ScanHistorySettings))
    return result.scalar_one_or_none()


async def cleanup_scan_history(db: AsyncSession) -> None:
    """Remove old scan history entries based on settings."""
    settings = await _get_settings(db)
    if not settings:
        return

    now = datetime.now(timezone.utc)
    removed = 0

    # 1. Remove entries older than max_age_days
    cutoff = now - timedelta(days=settings.max_age_days)
    stmt = delete(EmailScan).where(EmailScan.created_at < cutoff)
    result = await db.execute(stmt)
    removed += result.rowcount

    # 2. Enforce max_per_user limit
    users_result = await db.execute(select(User.id))
    user_ids = [row[0] for row in users_result.all()]

    for user_id in user_ids:
        # Count scans for this user
        count_q = (
            select(func.count())
            .select_from(EmailScan)
            .join(EmailAccount)
            .where(EmailAccount.user_id == user_id)
        )
        count = (await db.execute(count_q)).scalar()

        if count > settings.max_per_user:
            excess = count - settings.max_per_user
            # Find IDs of oldest entries to delete
            oldest_q = (
                select(EmailScan.id)
                .join(EmailAccount)
                .where(EmailAccount.user_id == user_id)
                .order_by(EmailScan.created_at.asc())
                .limit(excess)
            )
            oldest_ids = [row[0] for row in (await db.execute(oldest_q)).all()]
            if oldest_ids:
                await db.execute(delete(EmailScan).where(EmailScan.id.in_(oldest_ids)))
                removed += len(oldest_ids)

    await db.commit()
    logger.info(f"Scan history cleanup: removed {removed} entries")
```

**Step 4: Run tests**

Run: `cd backend && pytest tests/test_history_cleanup.py -v`

Expected: PASS

**Step 5: Create scheduler setup module**

Create `backend/app/services/scheduler.py`:

```python
import logging
from datetime import datetime, timezone

from apscheduler import AsyncScheduler, ConflictPolicy
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.models.scan_history_settings import ScanHistorySettings
from app.services.history_cleanup import cleanup_scan_history

logger = logging.getLogger(__name__)

# Track last run time in-memory (APScheduler schedules persist in DB)
_job_metadata: dict[str, dict] = {}


def get_job_metadata() -> dict[str, dict]:
    return _job_metadata


async def _run_history_cleanup():
    """Wrapper called by APScheduler — creates its own DB session."""
    _job_metadata.setdefault("history_cleanup", {})["last_run_at"] = datetime.now(timezone.utc)
    async with async_session() as db:
        await cleanup_scan_history(db)


async def create_scheduler() -> AsyncScheduler:
    """Create and configure the APScheduler instance."""
    data_store = SQLAlchemyDataStore(engine)
    scheduler = AsyncScheduler(data_store)

    # Determine cleanup interval from settings (default 1 hour)
    interval_hours = 1.0
    try:
        async with async_session() as db:
            result = await db.execute(select(ScanHistorySettings))
            settings = result.scalar_one_or_none()
            if settings:
                interval_hours = settings.cleanup_interval_hours
    except Exception:
        pass

    await scheduler.add_schedule(
        _run_history_cleanup,
        IntervalTrigger(hours=interval_hours),
        id="history_cleanup",
        conflict_policy=ConflictPolicy.replace,
    )

    _job_metadata["history_cleanup"] = {
        "description": "Clean up old email scan history",
        "interval_hours": interval_hours,
        "last_run_at": None,
    }

    return scheduler
```

**Step 6: Integrate scheduler into main.py lifespan**

Update `backend/app/main.py` lifespan:

```python
from app.services.scheduler import create_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await wait_for_db()
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)

    scheduler = await create_scheduler()
    async with scheduler:
        await scheduler.start_in_background()
        app.state.scheduler = scheduler
        await start_all_watchers()
        logger.info("Package Tracker is ready.")
        yield
        await stop_all_watchers()
```

**Step 7: Run all tests**

Run: `cd backend && pytest tests/ -v`

Expected: All pass. APScheduler won't start in tests (lifespan doesn't run with ASGI transport).

**Step 8: Commit**

```bash
git add backend/app/services/history_cleanup.py backend/app/services/scheduler.py backend/app/main.py backend/tests/test_history_cleanup.py
git commit -m "feat: add APScheduler framework and history cleanup job"
```

---

### Task 9: Scan history settings API + system status extension

**Files:**
- Create: `backend/app/api/scan_history_settings.py`
- Modify: `backend/app/api/system.py` (add scheduled jobs to status)
- Modify: `backend/app/main.py` (register settings router)

**Step 1: Create scan history settings endpoints**

Create `backend/app/api/scan_history_settings.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.scan_history_settings import ScanHistorySettings
from app.schemas.scan_history import ScanHistorySettingsResponse, UpdateScanHistorySettingsRequest

router = APIRouter(
    prefix="/api/v1/settings/scan-history",
    tags=["settings"],
    dependencies=[Depends(get_admin_user)],
)


@router.get("/", response_model=ScanHistorySettingsResponse)
async def get_scan_history_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScanHistorySettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ScanHistorySettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.put("/", response_model=ScanHistorySettingsResponse)
async def update_scan_history_settings(
    data: UpdateScanHistorySettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ScanHistorySettings))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = ScanHistorySettings(id=1)
        db.add(settings)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)
    return settings
```

**Step 2: Extend system status with scheduled jobs**

In `backend/app/api/system.py`, add to the `system_status` endpoint response:

```python
from app.services.scheduler import get_job_metadata

# Inside system_status(), at the end before return:
scheduled_jobs = []
for job_id, meta in get_job_metadata().items():
    job_info = {
        "id": job_id,
        "description": meta.get("description", ""),
        "interval_hours": meta.get("interval_hours"),
        "last_run_at": meta["last_run_at"].isoformat() if meta.get("last_run_at") else None,
    }
    # Get next run time from scheduler if available
    try:
        from fastapi import Request
        # next_run_at can be computed from last_run + interval
        if meta.get("last_run_at") and meta.get("interval_hours"):
            from datetime import timedelta
            job_info["next_run_at"] = (
                meta["last_run_at"] + timedelta(hours=meta["interval_hours"])
            ).isoformat()
    except Exception:
        pass
    scheduled_jobs.append(job_info)
```

Add `"scheduled_jobs": scheduled_jobs` to the response dict.

**Step 3: Register settings router in main.py**

```python
from app.api.scan_history_settings import router as scan_history_settings_router
app.include_router(scan_history_settings_router)
```

**Step 4: Run all tests**

Run: `cd backend && pytest tests/ -v`

Expected: All pass.

**Step 5: Commit**

```bash
git add backend/app/api/scan_history_settings.py backend/app/api/system.py backend/app/main.py
git commit -m "feat: add scan history settings API and scheduled jobs in system status"
```

---

### Task 10: Frontend — scan history store + router + sidebar

**Files:**
- Create: `frontend/src/stores/scanHistory.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/AppLayout.vue`

**Step 1: Create scan history Pinia store**

Create `frontend/src/stores/scanHistory.ts`:

```typescript
import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export interface EmailScan {
  id: number
  account_id: number
  account_name: string | null
  folder_path: string
  email_uid: number
  message_id: string
  subject: string
  sender: string
  email_date: string | null
  is_relevant: boolean
  llm_raw_response: Record<string, unknown> | null
  order_id: number | null
  rescan_queued: boolean
  created_at: string
}

export interface EmailScanList {
  items: EmailScan[]
  total: number
  page: number
  per_page: number
}

export interface EmailContent {
  subject: string
  sender: string
  date: string | null
  body_text: string
}

export const useScanHistoryStore = defineStore('scanHistory', () => {
  const scans = ref<EmailScanList>({ items: [], total: 0, page: 1, per_page: 50 })
  const loading = ref(false)

  async function fetchScans(params?: {
    page?: number
    per_page?: number
    is_relevant?: boolean | null
    account_id?: number | null
  }) {
    loading.value = true
    try {
      const query = new URLSearchParams()
      if (params?.page) query.set('page', String(params.page))
      if (params?.per_page) query.set('per_page', String(params.per_page))
      if (params?.is_relevant !== undefined && params.is_relevant !== null)
        query.set('is_relevant', String(params.is_relevant))
      if (params?.account_id) query.set('account_id', String(params.account_id))
      const { data } = await api.get(`/scan-history?${query}`)
      scans.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchScan(id: number): Promise<EmailScan> {
    const { data } = await api.get(`/scan-history/${id}`)
    return data
  }

  async function fetchEmailContent(id: number): Promise<EmailContent> {
    const { data } = await api.get(`/scan-history/${id}/email`)
    return data
  }

  async function deleteScan(id: number) {
    await api.delete(`/scan-history/${id}`)
  }

  async function queueRescan(id: number): Promise<EmailScan> {
    const { data } = await api.post(`/scan-history/${id}/rescan`)
    return data
  }

  return { scans, loading, fetchScans, fetchScan, fetchEmailContent, deleteScan, queueRescan }
})
```

**Step 2: Add route to router/index.ts**

Add to the routes array (after `/orders/:id` and before `/accounts`):

```typescript
{
  path: '/history',
  name: 'history',
  component: () => import('@/views/HistoryView.vue'),
  meta: { requiresAuth: true },
},
```

**Step 3: Add sidebar entry to AppLayout.vue**

In the navigation items computed array, add between orders and accounts:

```typescript
{ name: t('nav.history'), path: '/history', icon: 'ClockIcon' },
```

Use an appropriate icon (clock/history icon) matching the existing icon pattern. If the project uses Heroicons or similar, adapt accordingly.

**Step 4: Commit**

```bash
git add frontend/src/stores/scanHistory.ts frontend/src/router/index.ts frontend/src/components/AppLayout.vue
git commit -m "feat(frontend): add scan history store, route, and sidebar entry"
```

---

### Task 11: Frontend — HistoryView + detail modal

**Files:**
- Create: `frontend/src/views/HistoryView.vue`

**Step 1: Create HistoryView.vue**

Create `frontend/src/views/HistoryView.vue` following the pattern of `OrdersView.vue`:

Key elements:
- **Filters bar**: Account dropdown (fetch from accounts store), relevance toggle (All / Relevant / Not Relevant)
- **Table**: Date, Subject, Sender, Account, Relevant (green/gray badge), Order (link), Actions (View, Rescan, Delete)
- **Pagination**: Page controls using `scans.total`, `scans.page`, `scans.per_page`
- **Detail modal**: Opens on "View" click
  - Shows: subject, sender, email_date, account, folder_path
  - LLM raw response as formatted JSON in `<pre>` block with syntax highlighting via `JSON.stringify(llm_raw_response, null, 2)`
  - Order link if `order_id` set
  - "Fetch Email" button → calls `fetchEmailContent(id)`, shows body_text in a `<pre>` block
  - Loading/error states for email fetch
  - Rescan button
- **Rescan button**: Calls `queueRescan(id)`, updates local state, shows "Queued" badge
- **Delete button**: Confirmation dialog, calls `deleteScan(id)`, refetches list

Follow existing patterns:
- `<script setup lang="ts">` with `useI18n()`, `useScanHistoryStore()`, `useAccountsStore()`
- Tailwind styling matching existing views
- Dark mode support with `dark:` classes
- Responsive layout
- `onMounted` fetches initial data

**Step 2: Verify it builds**

Run: `cd frontend && npm run build`

Expected: Build succeeds with no type errors.

**Step 3: Commit**

```bash
git add frontend/src/views/HistoryView.vue
git commit -m "feat(frontend): add HistoryView with table, filters, detail modal, and email fetch"
```

---

### Task 12: Frontend — SystemView scheduled jobs + i18n

**Files:**
- Modify: `frontend/src/views/admin/SystemView.vue`
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Add scheduled jobs section to SystemView**

In `SystemView.vue`, add a new section after the stats chart and before the folder list:

```html
<!-- Scheduled Jobs -->
<div v-if="status?.scheduled_jobs?.length" class="...">
  <h3>{{ $t('system.scheduledJobs') }}</h3>
  <div v-for="job in status.scheduled_jobs" :key="job.id" class="...">
    <div>{{ job.description }}</div>
    <div>{{ $t('system.jobInterval', { hours: job.interval_hours }) }}</div>
    <div>{{ $t('system.jobLastRun') }}: {{ job.last_run_at ? formatTimeAgo(job.last_run_at) : $t('common.never') }}</div>
    <div>{{ $t('system.jobNextRun') }}: {{ job.next_run_at ? formatTimeUntil(job.next_run_at) : '-' }}</div>
  </div>
</div>
```

Update the `SystemStatus` interface to include `scheduled_jobs` array.

**Step 2: Add i18n strings to en.json**

Add to `en.json`:

```json
{
  "nav": {
    "history": "History"
  },
  "history": {
    "title": "Scan History",
    "filters": "Filters",
    "allEmails": "All",
    "relevant": "Relevant",
    "notRelevant": "Not Relevant",
    "date": "Date",
    "subject": "Subject",
    "sender": "Sender",
    "account": "Account",
    "relevance": "Relevant",
    "order": "Order",
    "actions": "Actions",
    "view": "View",
    "rescan": "Rescan",
    "delete": "Delete",
    "confirmDelete": "Delete this scan history entry?",
    "rescanQueued": "Queued for rescan",
    "noResults": "No scan history entries found.",
    "detail": "Scan Detail",
    "folder": "Folder",
    "llmResponse": "LLM Response",
    "fetchEmail": "Fetch Email",
    "fetchingEmail": "Fetching email from server...",
    "emailNotAvailable": "Email is no longer available on the server.",
    "emailContent": "Email Content",
    "page": "Page {page} of {total}"
  },
  "system": {
    "scheduledJobs": "Scheduled Jobs",
    "jobInterval": "Runs every {hours}h",
    "jobLastRun": "Last run",
    "jobNextRun": "Next run"
  }
}
```

**Step 3: Add i18n strings to de.json**

Add equivalent German translations to `de.json`.

**Step 4: Verify build**

Run: `cd frontend && npm run build`

Expected: Build succeeds.

**Step 5: Run lint and type-check**

Run: `cd frontend && npm run lint && npm run type-check`

**Step 6: Commit**

```bash
git add frontend/src/views/admin/SystemView.vue frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat(frontend): add scheduled jobs to SystemView and i18n for scan history"
```

---

### Task 13: Alembic APScheduler table exclusion + pass email_date from worker

**Files:**
- Modify: `backend/alembic/env.py` (exclude APScheduler tables from autogenerate)
- Modify: `backend/app/services/imap_worker.py` (pass email_date to process_email)

**Step 1: Exclude APScheduler tables from Alembic**

In `backend/alembic/env.py`, add to the `run_migrations_online` (or equivalent) function:

```python
def include_name(name, type_, parent_names):
    if type_ == "table" and name.startswith("apscheduler_"):
        return False
    return True

# Pass to context.configure:
context.configure(
    ...,
    include_name=include_name,
)
```

**Step 2: Pass email_date from IMAP worker**

In `backend/app/services/imap_worker.py`, after extracting email headers (~line 220), parse the Date header and pass it to `process_email`:

```python
from email.utils import parsedate_to_datetime

# After extracting subject, sender, message_id, body:
email_date = None
try:
    date_str = msg.get("Date", "")
    if date_str:
        email_date = parsedate_to_datetime(date_str)
except Exception:
    pass

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
    email_date=email_date,
)
```

**Step 3: Run all tests**

Run: `cd backend && pytest tests/ -v`

Expected: All pass.

**Step 4: Commit**

```bash
git add backend/alembic/env.py backend/app/services/imap_worker.py
git commit -m "chore: exclude APScheduler tables from Alembic + pass email_date to processor"
```

---

### Final verification

**Step 1: Run full backend test suite**

Run: `cd backend && pytest tests/ -v`

**Step 2: Run frontend build + checks**

Run: `cd frontend && npm run build && npm run lint && npm run type-check`

**Step 3: Docker compose smoke test**

Run: `docker compose up --build` and verify:
- `/api/v1/scan-history` returns empty list
- `/api/v1/system/status` includes `scheduled_jobs`
- `/api/v1/settings/scan-history` returns defaults
- History sidebar link appears and navigates to HistoryView
