# Queue Architecture Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate the backend into source/queue/order layers with a decoupled processing queue, OrderState history, and pluggable matching.

**Architecture:** IMAP worker becomes a pure source adapter that pushes raw email data into a `QueueItem` table. A `QueueWorker` (scheduled every 5s) picks items, calls the LLM via `QueueProcessor`, matches/creates orders via a pluggable `OrderMatcher`, and records `OrderState` transitions. Retention cleanup runs every 10 minutes.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL, APScheduler, Vue 3, Pinia, Tailwind CSS 4, i18n

**Design doc:** `docs/plans/2026-02-14-queue-architecture-design.md`

**Important context:** This app is in early development — no deployed users. We can freely drop/recreate tables. Tests use in-memory SQLite. The CLAUDE.md says no need to worry about DB migrations, but since Alembic is set up, we generate a new migration for the model changes.

---

## Task 1: New models — QueueItem, OrderState, ProcessedEmail

**Files:**
- Create: `backend/app/models/queue_item.py`
- Create: `backend/app/models/order_state.py`
- Create: `backend/app/models/processed_email.py`
- Create: `backend/app/models/queue_settings.py`
- Modify: `backend/app/models/order.py` — remove `OrderEvent`, update `Order` relationship
- Modify: `backend/app/models/__init__.py` — update exports
- Delete: `backend/app/models/email_scan.py`
- Delete: `backend/app/models/scan_history_settings.py`
- Delete: `backend/app/models/worker_stats.py`

**Step 1: Create `backend/app/models/queue_item.py`**

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class QueueItem(Base):
    __tablename__ = "queue_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    source_type: Mapped[str] = mapped_column(String(50))
    source_info: Mapped[str] = mapped_column(String(512), default="")
    raw_data: Mapped[dict] = mapped_column(JSON)
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    cloned_from_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("queue_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User")
    order = relationship("Order")
```

**Step 2: Create `backend/app/models/order_state.py`**

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OrderState(Base):
    __tablename__ = "order_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(50))
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_info: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    order = relationship("Order", back_populates="states")
```

**Step 3: Create `backend/app/models/processed_email.py`**

```python
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProcessedEmail(Base):
    __tablename__ = "processed_emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="CASCADE")
    )
    folder_path: Mapped[str] = mapped_column(String(512))
    email_uid: Mapped[int] = mapped_column(Integer)
    message_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    queue_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("queue_items.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    account = relationship("EmailAccount")
    queue_item = relationship("QueueItem")
```

**Step 4: Create `backend/app/models/queue_settings.py`**

```python
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueueSettings(Base):
    __tablename__ = "queue_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_age_days: Mapped[int] = mapped_column(Integer, default=7)
    max_per_user: Mapped[int] = mapped_column(Integer, default=5000)
```

**Step 5: Update `backend/app/models/order.py`**

Remove `OrderEvent` class entirely. Change the `Order.events` relationship to `Order.states` pointing to `OrderState`:

```python
# Replace:
#   events = relationship("OrderEvent", back_populates="order", cascade="all, delete-orphan")
# With:
    states = relationship("OrderState", back_populates="order", cascade="all, delete-orphan")
```

Remove the entire `OrderEvent` class definition (lines 37-53).

**Step 6: Update `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.order import Order
from app.models.order_state import OrderState
from app.models.llm_config import LLMConfig
from app.models.api_key import ApiKey
from app.models.imap_settings import ImapSettings
from app.models.queue_item import QueueItem
from app.models.processed_email import ProcessedEmail
from app.models.queue_settings import QueueSettings

__all__ = [
    "User", "EmailAccount", "WatchedFolder", "Order", "OrderState",
    "LLMConfig", "ApiKey", "ImapSettings",
    "QueueItem", "ProcessedEmail", "QueueSettings",
]
```

**Step 7: Delete old model files**

Delete these files:
- `backend/app/models/email_scan.py`
- `backend/app/models/scan_history_settings.py`
- `backend/app/models/worker_stats.py`

**Step 8: Verify models compile**

Run: `cd /home/mato/projects/tools/package-tracker/backend && python -c "from app.models import *; print('OK')"`
Expected: `OK`

**Step 9: Commit**

```
feat: add QueueItem, OrderState, ProcessedEmail, QueueSettings models

Replace EmailScan with ProcessedEmail (lightweight dedup) + QueueItem
(processing queue). Replace OrderEvent with OrderState (status timeline).
Replace ScanHistorySettings with QueueSettings. Drop WorkerStats.
```

---

## Task 2: New schemas for Queue, OrderState, QueueSettings

**Files:**
- Create: `backend/app/schemas/queue_item.py`
- Create: `backend/app/schemas/queue_settings.py`
- Modify: `backend/app/schemas/order.py` — replace OrderEventResponse with OrderStateResponse
- Delete: `backend/app/schemas/scan_history.py`

**Step 1: Create `backend/app/schemas/queue_item.py`**

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QueueItemResponse(BaseModel):
    id: int
    user_id: int
    status: str
    source_type: str
    source_info: str
    raw_data: dict
    extracted_data: dict | None
    error_message: str | None
    order_id: int | None
    cloned_from_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QueueItemListResponse(BaseModel):
    items: list[QueueItemResponse]
    total: int
    page: int
    per_page: int


class QueueStatsResponse(BaseModel):
    queued: int
    processing: int
    completed: int
    failed: int
```

**Step 2: Create `backend/app/schemas/queue_settings.py`**

```python
from pydantic import BaseModel


class QueueSettingsResponse(BaseModel):
    max_age_days: int
    max_per_user: int

    model_config = {"from_attributes": True}


class UpdateQueueSettingsRequest(BaseModel):
    max_age_days: int | None = None
    max_per_user: int | None = None
```

**Step 3: Update `backend/app/schemas/order.py`**

Replace `OrderEventResponse` with `OrderStateResponse`. Update `OrderDetailResponse`:

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


class OrderStateResponse(BaseModel):
    id: int
    status: str
    source_type: str | None
    source_info: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderDetailResponse(OrderResponse):
    states: list[OrderStateResponse]


class UpdateOrderRequest(BaseModel):
    order_number: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    vendor_name: Optional[str] = None
    status: Optional[str] = None


class LinkOrderRequest(BaseModel):
    target_order_id: int
```

**Step 4: Delete `backend/app/schemas/scan_history.py`**

**Step 5: Commit**

```
feat: add queue and order state schemas, remove scan history schemas
```

---

## Task 3: Order service layer — `services/orders/`

**Files:**
- Create: `backend/app/services/orders/__init__.py` (empty)
- Create: `backend/app/services/orders/order_service.py`
- Create: `backend/app/services/orders/order_matcher.py`
- Delete: `backend/app/services/order_matcher.py`
- Delete: `backend/app/services/email_processor.py`

**Step 1: Create `backend/app/services/orders/__init__.py`** (empty file)

**Step 2: Create `backend/app/services/orders/order_service.py`**

This is the order creation/update logic extracted from `email_processor.py`:

```python
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_state import OrderState
from app.services.llm_service import EmailAnalysis


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def create_or_update_order(
    analysis: EmailAnalysis,
    user_id: int,
    existing_order: Order | None,
    source_type: str | None = None,
    source_info: str | None = None,
    db: AsyncSession = None,
) -> Order:
    """Create a new order or update an existing one based on LLM analysis.

    Also inserts an OrderState entry if the status changed or a new order was created.
    Returns the created/updated Order.
    """
    if existing_order:
        order = existing_order
        old_status = order.status

        if analysis.tracking_number and not order.tracking_number:
            order.tracking_number = analysis.tracking_number
        if analysis.carrier and not order.carrier:
            order.carrier = analysis.carrier
        if analysis.estimated_delivery:
            order.estimated_delivery = _parse_date(analysis.estimated_delivery)
        if analysis.status:
            order.status = analysis.status

        # Only insert OrderState if status actually changed
        if order.status != old_status:
            state = OrderState(
                order_id=order.id,
                status=order.status,
                source_type=source_type,
                source_info=source_info,
            )
            db.add(state)
    else:
        status = analysis.status or "ordered"
        order = Order(
            user_id=user_id,
            order_number=analysis.order_number,
            tracking_number=analysis.tracking_number,
            carrier=analysis.carrier,
            vendor_name=analysis.vendor_name,
            vendor_domain=analysis.vendor_domain,
            status=status,
            order_date=_parse_date(analysis.order_date),
            total_amount=analysis.total_amount,
            currency=analysis.currency,
            items=[item.model_dump() for item in analysis.items] if analysis.items else None,
            estimated_delivery=_parse_date(analysis.estimated_delivery),
        )
        db.add(order)
        await db.flush()

        # Initial state entry
        state = OrderState(
            order_id=order.id,
            status=status,
            source_type=source_type,
            source_info=source_info,
        )
        db.add(state)

    return order
```

**Step 3: Create `backend/app/services/orders/order_matcher.py`**

Pluggable matcher with protocol + default implementation:

```python
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.services.llm_service import EmailAnalysis


class OrderMatcherProtocol(Protocol):
    async def find_match(
        self, analysis: EmailAnalysis, user_id: int, db: AsyncSession
    ) -> Order | None: ...


class DefaultOrderMatcher:
    """3-tier matching: exact order_number → exact tracking_number → fuzzy vendor+items."""

    async def find_match(
        self, analysis: EmailAnalysis, user_id: int, db: AsyncSession
    ) -> Order | None:
        # Priority 1: exact order_number match
        if analysis.order_number:
            result = await db.execute(
                select(Order).where(
                    Order.user_id == user_id,
                    Order.order_number == analysis.order_number,
                )
            )
            order = result.scalar_one_or_none()
            if order:
                return order

        # Priority 2: exact tracking_number match
        if analysis.tracking_number:
            result = await db.execute(
                select(Order).where(
                    Order.user_id == user_id,
                    Order.tracking_number == analysis.tracking_number,
                )
            )
            order = result.scalar_one_or_none()
            if order:
                return order

        # Priority 3: fuzzy match - same vendor_domain + item name overlap
        if analysis.vendor_domain:
            result = await db.execute(
                select(Order)
                .where(
                    Order.user_id == user_id,
                    Order.vendor_domain == analysis.vendor_domain,
                )
                .order_by(Order.created_at.desc())
                .limit(5)
            )
            candidates = result.scalars().all()

            if analysis.items and candidates:
                email_item_names = {
                    item.name.lower() for item in analysis.items if item.name
                }
                for candidate in candidates:
                    if candidate.items:
                        order_item_names = {
                            item.get("name", "").lower() for item in candidate.items
                        }
                        if email_item_names & order_item_names:
                            return candidate

        return None
```

**Step 4: Delete old service files**

- Delete `backend/app/services/order_matcher.py`
- Delete `backend/app/services/email_processor.py`

**Step 5: Commit**

```
feat: add order service layer with pluggable matcher

Extract order creation/update logic into order_service.py.
Make order matching pluggable via OrderMatcherProtocol.
```

---

## Task 4: Queue service layer — `services/queue/`

**Files:**
- Create: `backend/app/services/queue/__init__.py` (empty)
- Create: `backend/app/services/queue/queue_processor.py`
- Create: `backend/app/services/queue/queue_worker.py`
- Create: `backend/app/services/queue/queue_retention.py`
- Delete: `backend/app/services/history_cleanup.py`

**Step 1: Create `backend/app/services/queue/__init__.py`** (empty file)

**Step 2: Create `backend/app/services/queue/queue_processor.py`**

Pure transformation: takes raw_data, calls LLM, returns extracted_data.

```python
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import EmailAnalysis, analyze_email

logger = logging.getLogger(__name__)


async def process_raw_data(
    raw_data: dict, db: AsyncSession
) -> tuple[EmailAnalysis | None, dict]:
    """Process raw queue item data through the LLM.

    Returns (parsed_analysis, raw_llm_response_dict).
    Currently only handles email source type.
    """
    subject = raw_data.get("subject", "")
    sender = raw_data.get("sender", "")
    body = raw_data.get("body", "")

    return await analyze_email(subject, sender, body, db)
```

**Step 3: Create `backend/app/services/queue/queue_worker.py`**

The main worker that picks up queued items and processes them:

```python
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.queue_item import QueueItem
from app.services.queue.queue_processor import process_raw_data
from app.services.orders.order_matcher import DefaultOrderMatcher
from app.services.orders.order_service import create_or_update_order

logger = logging.getLogger(__name__)

_matcher = DefaultOrderMatcher()


async def process_next_item() -> None:
    """Pick one queued item and process it. Called by the scheduler every 5s."""
    async with async_session() as db:
        # Pick the oldest queued item
        result = await db.execute(
            select(QueueItem)
            .where(QueueItem.status == "queued")
            .order_by(QueueItem.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        item = result.scalar_one_or_none()
        if not item:
            return

        item.status = "processing"
        await db.commit()

        try:
            analysis, raw_response = await process_raw_data(item.raw_data, db)

            item.extracted_data = raw_response

            if analysis is None or not analysis.is_relevant:
                item.status = "completed"
                await db.commit()
                return

            # Find matching order
            existing_order = await _matcher.find_match(analysis, item.user_id, db)

            # Create or update order
            order = await create_or_update_order(
                analysis=analysis,
                user_id=item.user_id,
                existing_order=existing_order,
                source_type=item.source_type,
                source_info=item.source_info,
                db=db,
            )

            item.order_id = order.id
            item.status = "completed"
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to process queue item {item.id}: {e}")
            # Refresh session state in case of partial failures
            await db.rollback()
            async with async_session() as err_db:
                err_item = await err_db.get(QueueItem, item.id)
                if err_item:
                    err_item.status = "failed"
                    err_item.error_message = str(e)
                    await err_db.commit()
```

**Step 4: Create `backend/app/services/queue/queue_retention.py`**

```python
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_item import QueueItem
from app.models.queue_settings import QueueSettings

logger = logging.getLogger(__name__)


async def cleanup_queue(db: AsyncSession) -> None:
    """Delete old QueueItems based on QueueSettings."""
    result = await db.execute(select(QueueSettings))
    settings = result.scalar_one_or_none()
    if not settings:
        return

    total_removed = 0

    # 1. Delete entries older than max_age_days
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.max_age_days)
    age_stmt = delete(QueueItem).where(QueueItem.created_at < cutoff)
    age_result = await db.execute(age_stmt)
    total_removed += age_result.rowcount

    # 2. Per-user cap: delete oldest excess entries beyond max_per_user
    user_counts_stmt = (
        select(QueueItem.user_id, func.count(QueueItem.id).label("cnt"))
        .group_by(QueueItem.user_id)
        .having(func.count(QueueItem.id) > settings.max_per_user)
    )
    user_counts = await db.execute(user_counts_stmt)

    for user_id, count in user_counts:
        excess = count - settings.max_per_user
        oldest_ids_stmt = (
            select(QueueItem.id)
            .where(QueueItem.user_id == user_id)
            .order_by(QueueItem.created_at.asc())
            .limit(excess)
        )
        oldest_ids_result = await db.execute(oldest_ids_stmt)
        ids_to_delete = [row[0] for row in oldest_ids_result]

        if ids_to_delete:
            del_stmt = delete(QueueItem).where(QueueItem.id.in_(ids_to_delete))
            del_result = await db.execute(del_stmt)
            total_removed += del_result.rowcount

    await db.commit()

    if total_removed > 0:
        logger.info(f"Queue cleanup: removed {total_removed} items")
```

**Step 5: Delete `backend/app/services/history_cleanup.py`**

**Step 6: Commit**

```
feat: add queue service layer (worker, processor, retention)

QueueWorker picks queued items every 5s, processes via LLM, and
creates/updates orders. QueueRetention cleans up old items.
```

---

## Task 5: Update IMAP source — decouple from processing

**Files:**
- Modify: `backend/app/services/imap_worker.py`

**Step 1: Rewrite `_watch_folder()` to push to queue instead of processing inline**

The IMAP worker should:
1. Fetch emails as before (IMAP connection, UIDVALIDITY, search, decode)
2. Check dedup via `ProcessedEmail.message_id` instead of `EmailScan.message_id`
3. Create a `QueueItem` with `source_type="email"` and raw email data as JSON
4. Create a `ProcessedEmail` record linking to the QueueItem
5. Update `last_seen_uid` as before
6. Remove ALL references to `process_email()`, `EmailScan`, `WorkerStats`, `_record_stat()`
7. Remove the entire rescan queue block (lines 266-335) — retry is now handled by the queue UI

Key changes to imports:
- Remove: `from app.services.email_processor import process_email`
- Remove: `from app.models.email_scan import EmailScan`
- Remove: `from app.models.worker_stats import WorkerStats`
- Add: `from app.models.processed_email import ProcessedEmail`
- Add: `from app.models.queue_item import QueueItem`

In the email processing loop (around line 241), replace the `process_email()` call + `_record_stat()` with:

```python
# Dedup check
existing = await db.execute(
    select(ProcessedEmail).where(ProcessedEmail.message_id == message_id)
)
if existing.scalar_one_or_none():
    folder.last_seen_uid = uid
    await db.commit()
    continue

# Create queue item
queue_item = QueueItem(
    user_id=account.user_id,
    status="queued",
    source_type="email",
    source_info=f"{account.imap_user} / {folder.folder_path}",
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

# Record dedup entry
processed = ProcessedEmail(
    account_id=account_id,
    folder_path=folder.folder_path,
    email_uid=uid,
    message_id=message_id,
    queue_item_id=queue_item.id,
)
db.add(processed)

folder.last_seen_uid = uid
await db.commit()
```

Also remove the `_record_stat()` function entirely (lines 115-131) and the `WorkerStats` import.

Remove the entire rescan queue block (lines 266-335).

**Step 2: Commit**

```
refactor: decouple IMAP worker from email processing

IMAP worker now pushes raw email data to QueueItem instead of
calling process_email() inline. Dedup uses ProcessedEmail.
Rescan queue removed (handled by queue retry).
```

---

## Task 6: Update scheduler — register queue worker + retention

**Files:**
- Modify: `backend/app/services/scheduler.py`

**Step 1: Rewrite `scheduler.py` to register new jobs**

```python
import logging
from datetime import datetime, timezone

from apscheduler import AsyncScheduler, ConflictPolicy
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger

from app.database import async_session, engine

logger = logging.getLogger(__name__)

_job_metadata: dict[str, dict] = {}


async def _run_queue_worker() -> None:
    """Wrapper that calls process_next_item."""
    from app.services.queue.queue_worker import process_next_item

    _job_metadata["queue_worker"]["last_run"] = datetime.now(timezone.utc).isoformat()
    try:
        await process_next_item()
        _job_metadata["queue_worker"]["last_status"] = "success"
    except Exception as e:
        logger.error(f"Queue worker job failed: {e}")
        _job_metadata["queue_worker"]["last_status"] = f"error: {e}"


async def _run_retention_cleanup() -> None:
    """Wrapper that calls cleanup_queue."""
    from app.services.queue.queue_retention import cleanup_queue

    _job_metadata["retention_cleanup"]["last_run"] = datetime.now(timezone.utc).isoformat()
    try:
        async with async_session() as db:
            await cleanup_queue(db)
        _job_metadata["retention_cleanup"]["last_status"] = "success"
    except Exception as e:
        logger.error(f"Retention cleanup job failed: {e}")
        _job_metadata["retention_cleanup"]["last_status"] = f"error: {e}"


async def create_scheduler() -> AsyncScheduler:
    """Create and configure the AsyncScheduler."""
    data_store = SQLAlchemyDataStore(engine)
    scheduler = AsyncScheduler(data_store)

    _job_metadata["queue_worker"] = {
        "description": "Process next queued item",
        "interval_seconds": 5,
        "last_run": None,
        "last_status": None,
    }
    _job_metadata["retention_cleanup"] = {
        "description": "Clean up old queue items",
        "interval_seconds": 600,
        "last_run": None,
        "last_status": None,
    }

    logger.info("Scheduler created: queue worker every 5s, retention cleanup every 10min")
    return scheduler


async def register_schedules(scheduler: AsyncScheduler) -> None:
    """Register all scheduled jobs."""
    await scheduler.add_schedule(
        _run_queue_worker,
        IntervalTrigger(seconds=5),
        id="queue-worker",
        conflict_policy=ConflictPolicy.replace,
    )
    await scheduler.add_schedule(
        _run_retention_cleanup,
        IntervalTrigger(seconds=600),
        id="retention-cleanup",
        conflict_policy=ConflictPolicy.replace,
    )
    logger.info("Registered queue-worker and retention-cleanup schedules")


def get_job_metadata() -> dict[str, dict]:
    """Return metadata about scheduled jobs for the system status API."""
    return _job_metadata.copy()
```

**Step 2: Commit**

```
refactor: update scheduler for queue worker + retention jobs

Replace history-cleanup with queue-worker (5s) and
retention-cleanup (10min) scheduled jobs.
```

---

## Task 7: Update API routes — queue, orders, system, settings

**Files:**
- Create: `backend/app/api/queue.py`
- Create: `backend/app/api/queue_settings.py`
- Modify: `backend/app/api/orders.py` — use OrderState instead of OrderEvent
- Modify: `backend/app/api/system.py` — add queue stats, update for new models
- Modify: `backend/app/main.py` — swap routers
- Delete: `backend/app/api/scan_history.py`
- Delete: `backend/app/api/scan_history_settings.py`

**Step 1: Create `backend/app/api/queue.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.queue_item import QueueItem
from app.schemas.queue_item import QueueItemResponse, QueueItemListResponse, QueueStatsResponse
from app.api.deps import get_current_user, get_admin_user

router = APIRouter(prefix="/api/v1/queue", tags=["queue"])


@router.get("", response_model=QueueItemListResponse)
async def list_queue_items(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(QueueItem).where(QueueItem.user_id == user.id)

    if status:
        query = query.where(QueueItem.status == status)
    if source_type:
        query = query.where(QueueItem.source_type == source_type)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(QueueItem.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return QueueItemListResponse(
        items=[QueueItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/stats", response_model=QueueStatsResponse)
async def queue_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    counts = {}
    for s in ("queued", "processing", "completed", "failed"):
        result = await db.execute(
            select(func.count())
            .select_from(QueueItem)
            .where(QueueItem.user_id == user.id, QueueItem.status == s)
        )
        counts[s] = result.scalar() or 0
    return QueueStatsResponse(**counts)


@router.get("/{item_id}", response_model=QueueItemResponse)
async def get_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")
    await db.delete(item)
    await db.commit()


@router.post("/{item_id}/retry", response_model=QueueItemResponse)
async def retry_queue_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(QueueItem, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Queue item not found")

    clone = QueueItem(
        user_id=item.user_id,
        status="queued",
        source_type=item.source_type,
        source_info=item.source_info,
        raw_data=item.raw_data,
        extracted_data=None,
        error_message=None,
        order_id=None,
        cloned_from_id=item.id,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return clone
```

**Step 2: Create `backend/app/api/queue_settings.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.database import get_db
from app.models.queue_settings import QueueSettings
from app.schemas.queue_settings import QueueSettingsResponse, UpdateQueueSettingsRequest

router = APIRouter(
    prefix="/api/v1/settings/queue",
    tags=["settings"],
    dependencies=[Depends(get_admin_user)],
)


async def _get_or_create_settings(db: AsyncSession) -> QueueSettings:
    result = await db.execute(select(QueueSettings))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = QueueSettings(id=1, max_age_days=7, max_per_user=5000)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.get("/", response_model=QueueSettingsResponse)
async def get_queue_settings(db: AsyncSession = Depends(get_db)):
    return await _get_or_create_settings(db)


@router.put("/", response_model=QueueSettingsResponse)
async def update_queue_settings(
    body: UpdateQueueSettingsRequest,
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create_settings(db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    await db.commit()
    await db.refresh(settings)
    return settings
```

**Step 3: Update `backend/app/api/orders.py`**

Replace `OrderEvent` references with `OrderState`:

- Change import: `from app.models.order import Order` (remove `OrderEvent`)
- Add import: `from app.models.order_state import OrderState`
- In `get_order()`: change `selectinload(Order.events)` → `selectinload(Order.states)`
- In `link_orders()`: change the event migration block to migrate `OrderState` rows:

```python
# Move states from target to source
result = await db.execute(select(OrderState).where(OrderState.order_id == target.id))
for state in result.scalars().all():
    state.order_id = source.id
```

- In `update_order()`: when status changes, create an OrderState entry:

```python
old_status = order.status
for field, value in req.model_dump(exclude_unset=True).items():
    setattr(order, field, value)

# Create OrderState if status changed
if req.status and req.status != old_status:
    from app.models.order_state import OrderState
    state = OrderState(
        order_id=order.id,
        status=req.status,
        source_type="manual",
    )
    db.add(state)
```

**Step 4: Update `backend/app/api/system.py`**

- Remove imports: `WorkerStats`, `_running_tasks`, `_worker_state`
- Add imports: `QueueItem`
- In `system_status()`: remove the per-folder worker state hierarchy. Keep global summary but derive from QueueItem counts instead of WorkerStats. Keep scheduled jobs section.
- Remove `system_stats()` endpoint (WorkerStats table is gone). Can be replaced later if needed.
- Keep the IMAP watcher state reporting (`_running_tasks`, `_worker_state`) since the IMAP watcher still runs.

Actually — the IMAP worker still has `_running_tasks` and `_worker_state` for monitoring folder fetch status. Keep those imports and the folder hierarchy. Just remove the `system_stats` endpoint since `WorkerStats` is gone, and add queue stats to the status response.

Updated `system_status()` should add a `queue` section:

```python
# Add queue stats
queue_stats = {}
for s in ("queued", "processing", "completed", "failed"):
    result = await db.execute(
        select(func.count()).select_from(QueueItem).where(QueueItem.status == s)
    )
    queue_stats[s] = result.scalar() or 0

# Add to response:
return {
    "global": { ... },  # keep existing folder global stats
    "queue": queue_stats,
    "users": users_out,
    "scheduled_jobs": scheduled_jobs,
}
```

Remove the `/stats` endpoint and the `WorkerStats` import/usage.

**Step 5: Update `backend/app/main.py`**

Replace router registrations:

```python
# Remove these:
# from app.api.scan_history import router as scan_history_router
# from app.api.scan_history_settings import router as scan_history_settings_router
# app.include_router(scan_history_router)
# app.include_router(scan_history_settings_router)

# Add these:
from app.api.queue import router as queue_router
from app.api.queue_settings import router as queue_settings_router
app.include_router(queue_router)
app.include_router(queue_settings_router)
```

**Step 6: Delete old API files**

- Delete `backend/app/api/scan_history.py`
- Delete `backend/app/api/scan_history_settings.py`

**Step 7: Also delete `backend/app/services/imap_service.py`**

This was only used by `scan_history.py` to fetch email content from the server for the scan detail view. With the new design, raw email content is stored in `QueueItem.raw_data`, so this service is no longer needed.

**Step 8: Commit**

```
feat: add queue API, update orders/system for new models

Add /queue endpoints (list, detail, delete, retry, stats).
Add /settings/queue for retention config.
Update orders to use OrderState. Update system status.
Remove scan-history and scan-history-settings APIs.
```

---

## Task 8: Generate Alembic migration

**Files:**
- Create: new Alembic migration file (auto-generated)

**Step 1: Generate migration**

Since this is a major schema change and the app isn't deployed, the cleanest approach is to:
1. Delete all existing migration files in `backend/alembic/versions/`
2. Generate a single fresh migration from the current models

```bash
cd /home/mato/projects/tools/package-tracker/backend
rm alembic/versions/*.py
alembic revision --autogenerate -m "initial schema with queue architecture"
```

**Step 2: Verify migration**

```bash
cd /home/mato/projects/tools/package-tracker/backend
python -c "from app.models import *; print('Models OK')"
```

**Step 3: Update `main.py` baseline stamp**

In `main.py`, the `_run_migrations()` function stamps a baseline revision for pre-Alembic databases. Update the hardcoded revision ID to match the new single migration:

```python
# Update this line with the new migration's revision ID:
command.stamp(alembic_cfg, "<NEW_REVISION_ID>")
```

**Step 4: Commit**

```
chore: regenerate Alembic migration for queue architecture
```

---

## Task 9: Update all backend tests

**Files:**
- Modify: `backend/tests/conftest.py`
- Rewrite: `backend/tests/test_email_processor.py` → `backend/tests/test_queue_worker.py`
- Rewrite: `backend/tests/test_scan_history.py` → `backend/tests/test_queue_api.py`
- Rewrite: `backend/tests/test_history_cleanup.py` → `backend/tests/test_queue_retention.py`
- Modify: `backend/tests/test_orders.py` — update for OrderState
- Modify: `backend/tests/test_system.py` — update for new system status shape
- Modify: `backend/tests/test_order_matcher.py` — update import path

**Step 1: Update `conftest.py`**

No significant changes needed — the fixtures use in-memory SQLite and `Base.metadata.create_all` which auto-creates all tables. Just verify the client fixture still works.

**Step 2: Create `backend/tests/test_queue_worker.py`**

Tests for queue worker processing. Replace the email processor tests with queue-based equivalents:

- `test_process_queued_item_creates_order` — create a QueueItem with status=queued and relevant raw_data, call `process_next_item()`, verify Order + OrderState created, QueueItem status=completed
- `test_process_irrelevant_item` — QueueItem with irrelevant data → status=completed, no Order
- `test_process_updates_existing_order` — QueueItem that matches existing order → tracking added
- `test_process_failed_llm` — mock LLM failure → QueueItem status=failed, error_message set
- `test_no_items_to_process` — empty queue → no errors, no-op
- `test_order_state_created_on_new_order` — verify OrderState row created with initial status
- `test_order_state_created_on_status_change` — verify OrderState row when status transitions

**Step 3: Create `backend/tests/test_queue_api.py`**

Tests for queue API endpoints. Mirror the pattern from `test_scan_history.py`:

- `test_list_queue_items` — paginated list
- `test_list_queue_items_filter_status` — filter by status
- `test_get_queue_item_detail` — full detail
- `test_delete_queue_item` — deletion
- `test_retry_queue_item` — clones with cloned_from_id set
- `test_queue_stats` — counts per status
- `test_user_isolation` — users can't see other users' items

**Step 4: Create `backend/tests/test_queue_retention.py`**

Replace `test_history_cleanup.py`:

- `test_cleanup_removes_old_items` — items older than max_age_days deleted
- `test_cleanup_respects_max_per_user` — per-user cap enforced
- `test_cleanup_no_settings` — no-op when settings don't exist

**Step 5: Update `backend/tests/test_orders.py`**

- Change imports: `OrderEvent` → `OrderState`
- In `test_get_order_detail`: verify `states` field instead of `events`
- In `test_link_orders`: verify OrderState migration
- In update test: verify OrderState created on status change

**Step 6: Update `backend/tests/test_system.py`**

- Remove `WorkerStats` import and usage
- Remove `test_stats_*` tests (stats endpoint removed)
- Update `test_status_*` tests to check for `queue` section in response
- Keep folder/watcher status tests as-is (IMAP worker state unchanged)

**Step 7: Update `backend/tests/test_order_matcher.py`**

Update import path:
```python
# Old: from app.services.order_matcher import find_matching_order
# New: from app.services.orders.order_matcher import DefaultOrderMatcher
```

Update tests to use `DefaultOrderMatcher().find_match()` instead of `find_matching_order()`.

**Step 8: Delete old test files**

- Delete `backend/tests/test_email_processor.py`
- Delete `backend/tests/test_scan_history.py`
- Delete `backend/tests/test_history_cleanup.py`

**Step 9: Run all tests**

```bash
cd /home/mato/projects/tools/package-tracker/backend
pytest tests/ -v
```

Expected: All tests pass.

**Step 10: Commit**

```
test: rewrite tests for queue architecture

Add tests for queue worker, queue API, queue retention.
Update order and system tests for OrderState and new status shape.
Update order matcher tests for new import path.
```

---

## Task 10: Update frontend — stores and types

**Files:**
- Rewrite: `frontend/src/stores/scanHistory.ts` → `frontend/src/stores/queue.ts`
- Modify: `frontend/src/stores/orders.ts` — OrderState instead of OrderEvent

**Step 1: Create `frontend/src/stores/queue.ts`**

Replace `scanHistory.ts` with a queue store:

```typescript
import { ref } from 'vue'
import { defineStore } from 'pinia'
import api from '@/api/client'

export interface QueueItem {
  id: number
  user_id: number
  status: string
  source_type: string
  source_info: string
  raw_data: Record<string, unknown>
  extracted_data: Record<string, unknown> | null
  error_message: string | null
  order_id: number | null
  cloned_from_id: number | null
  created_at: string
  updated_at: string
}

export interface QueueItemList {
  items: QueueItem[]
  total: number
  page: number
  per_page: number
}

export interface QueueStats {
  queued: number
  processing: number
  completed: number
  failed: number
}

export const useQueueStore = defineStore('queue', () => {
  const items = ref<QueueItemList>({ items: [], total: 0, page: 1, per_page: 50 })
  const loading = ref(false)

  async function fetchItems(params?: { page?: number; per_page?: number; status?: string; source_type?: string }) {
    loading.value = true
    try {
      const { data } = await api.get<QueueItemList>('/queue', { params })
      items.value = data
    } finally {
      loading.value = false
    }
  }

  async function fetchItem(id: number): Promise<QueueItem> {
    const { data } = await api.get<QueueItem>(`/queue/${id}`)
    return data
  }

  async function deleteItem(id: number) {
    await api.delete(`/queue/${id}`)
  }

  async function retryItem(id: number): Promise<QueueItem> {
    const { data } = await api.post<QueueItem>(`/queue/${id}/retry`)
    return data
  }

  async function fetchStats(): Promise<QueueStats> {
    const { data } = await api.get<QueueStats>('/queue/stats')
    return data
  }

  return { items, loading, fetchItems, fetchItem, deleteItem, retryItem, fetchStats }
})
```

**Step 2: Delete `frontend/src/stores/scanHistory.ts`**

**Step 3: Update `frontend/src/stores/orders.ts`**

Replace `OrderEvent` interface with `OrderState`:

```typescript
export interface OrderState {
  id: number
  status: string
  source_type: string | null
  source_info: string | null
  created_at: string
}

export interface OrderDetail extends Order {
  states: OrderState[]
}
```

Remove the `OrderEvent` interface.

**Step 4: Commit**

```
feat(frontend): add queue store, update order types for OrderState
```

---

## Task 11: Update frontend — views

**Files:**
- Rewrite: `frontend/src/views/HistoryView.vue` → Queue view
- Modify: `frontend/src/views/OrderDetailView.vue` — OrderState timeline
- Modify: `frontend/src/views/admin/SystemView.vue` — queue stats
- Modify: `frontend/src/views/admin/SettingsView.vue` — add queue settings tab
- Create: `frontend/src/views/admin/QueueSettingsView.vue`
- Modify: `frontend/src/router/index.ts` — update route for queue settings

**Step 1: Rewrite `HistoryView.vue` as Queue view**

- Replace `useScanHistoryStore` with `useQueueStore`
- Table columns: Date, Source Type, Source Info, Status (badge), Relevant (derived from extracted_data), Order (link), Actions
- Status badge colors: queued=gray, processing=blue, completed=green, failed=red
- Detail modal with tabs: Raw Data (JSON), Extracted Data (JSON), Error (if failed)
- Filters: status dropdown, source_type dropdown
- Actions: View Detail, Retry, Delete
- Keep pagination

**Step 2: Update `OrderDetailView.vue`**

- Replace `events` usage with `states`
- Timeline shows OrderState entries: status badge + source_type/source_info + timestamp
- Remove `event_type` references, use `status` directly

**Step 3: Update `SystemView.vue`**

- Add queue stats card showing queued/processing/completed/failed counts
- Update scheduled jobs section — job metadata now has `interval_seconds` instead of `interval_hours`
- Remove the stats chart section (WorkerStats endpoint removed)

**Step 4: Create `frontend/src/views/admin/QueueSettingsView.vue`**

Simple settings form for max_age_days and max_per_user, matching the pattern from `ImapSettingsView.vue`.

**Step 5: Update `SettingsView.vue`**

Add queue tab to the tabs array:
```typescript
const tabs = computed(() => [
  { to: '/admin/settings/llm', label: t('settings.llmConfig') },
  { to: '/admin/settings/imap', label: t('settings.imap') },
  { to: '/admin/settings/queue', label: t('settings.queue') },
])
```

**Step 6: Update `router/index.ts`**

Add queue settings route as a child of `/admin/settings`:
```typescript
{
  path: 'queue',
  name: 'queue-settings',
  component: () => import('@/views/admin/QueueSettingsView.vue'),
}
```

**Step 7: Commit**

```
feat(frontend): update views for queue architecture

Rewrite HistoryView as queue view with status/source filters.
Update OrderDetailView for OrderState timeline.
Add queue stats to SystemView and queue settings page.
```

---

## Task 12: Update i18n translations

**Files:**
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Update English translations**

Replace `history.*` keys with `queue.*` equivalents:
- `queue.title`: "Processing Queue"
- `queue.status`: "Status"
- `queue.sourceType`: "Source"
- `queue.sourceInfo`: "Info"
- `queue.rawData`: "Raw Data"
- `queue.extractedData`: "Extracted Data"
- `queue.errorMessage`: "Error"
- `queue.retry`: "Retry"
- `queue.retried`: "Retried"
- `queue.clonedFrom`: "Cloned from"
- etc.

Add `settings.queue`: "Queue" for the settings tab label.
Add `settings.queueSettings`: "Queue Settings"
Add `settings.maxAgeDays`: "Max age (days)"
Add `settings.maxPerUser`: "Max items per user"

Update `orderDetail.states` (was `orderDetail.events`).

Update `system.queueStats`: "Queue"

**Step 2: Update German translations**

Mirror all English changes in German.

**Step 3: Commit**

```
feat(frontend): update i18n for queue architecture
```

---

## Task 13: Final verification and cleanup

**Files:**
- Verify: all files compile and pass

**Step 1: Run backend tests**

```bash
cd /home/mato/projects/tools/package-tracker/backend
pytest tests/ -v
```

Expected: All tests pass.

**Step 2: Run frontend type-check and build**

```bash
cd /home/mato/projects/tools/package-tracker/frontend
npm run type-check
npm run build
```

Expected: No type errors, build succeeds.

**Step 3: Run ESLint**

```bash
cd /home/mato/projects/tools/package-tracker/frontend
npm run lint
```

Expected: No errors.

**Step 4: Docker compose up (manual test)**

```bash
cd /home/mato/projects/tools/package-tracker
docker compose up --build
```

Verify the app starts, queue view loads, system view shows queue stats.

**Step 5: Commit any final fixes**

```
chore: final cleanup for queue architecture redesign
```

---

## Summary of what gets deleted

**Backend models:** `email_scan.py`, `scan_history_settings.py`, `worker_stats.py`, `OrderEvent` class from `order.py`
**Backend services:** `email_processor.py`, `order_matcher.py` (moved), `history_cleanup.py`, `imap_service.py`
**Backend API:** `scan_history.py`, `scan_history_settings.py`
**Backend schemas:** `scan_history.py`
**Backend tests:** `test_email_processor.py`, `test_scan_history.py`, `test_history_cleanup.py`
**Frontend stores:** `scanHistory.ts`

## Summary of what gets created

**Backend models:** `queue_item.py`, `order_state.py`, `processed_email.py`, `queue_settings.py`
**Backend services:** `services/orders/order_service.py`, `services/orders/order_matcher.py`, `services/queue/queue_processor.py`, `services/queue/queue_worker.py`, `services/queue/queue_retention.py`
**Backend API:** `queue.py`, `queue_settings.py`
**Backend schemas:** `queue_item.py`, `queue_settings.py`
**Backend tests:** `test_queue_worker.py`, `test_queue_api.py`, `test_queue_retention.py`
**Frontend stores:** `queue.ts`
**Frontend views:** `QueueSettingsView.vue`
