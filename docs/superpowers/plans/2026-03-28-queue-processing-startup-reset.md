# Queue Processing Startup Reset — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reset stuck `"processing"` queue items to `"queued"` on application startup so they are automatically reprocessed.

**Architecture:** A single `UPDATE` query in the existing `lifespan()` function in `main.py`, placed after DB readiness but before the scheduler starts. No new files, migrations, or API changes.

**Tech Stack:** SQLAlchemy 2.0 async ORM, pytest + pytest-asyncio

---

### Task 1: Write test for startup reset logic

**Files:**
- Create: `backend/tests/test_queue_startup_reset.py`

- [ ] **Step 1: Write the test file**

```python
"""Tests for queue startup reset (stuck 'processing' items reset to 'queued')."""

from sqlalchemy import select, update

from app.core.auth import hash_password
from app.models.queue_item import QueueItem
from app.models.user import User
from app.main import reset_stuck_queue_items


import pytest


@pytest.fixture
async def test_user(db_session):
    user = User(username="resetuser", password_hash=hash_password("pass"), is_admin=False)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _make_queue_item(user_id: int, status: str = "queued") -> QueueItem:
    return QueueItem(
        user_id=user_id,
        status=status,
        source_type="email",
        source_info="test",
        raw_data={"subject": "Test"},
    )


async def test_reset_stuck_processing_items(db_session, test_user):
    """Items stuck at 'processing' should be reset to 'queued'."""
    stuck = _make_queue_item(test_user.id, status="processing")
    db_session.add(stuck)
    await db_session.commit()
    await db_session.refresh(stuck)

    count = await reset_stuck_queue_items(db_session)

    assert count == 1
    await db_session.refresh(stuck)
    assert stuck.status == "queued"


async def test_reset_does_not_touch_other_statuses(db_session, test_user):
    """Items with status queued/completed/failed must not be changed."""
    items = [
        _make_queue_item(test_user.id, status="queued"),
        _make_queue_item(test_user.id, status="completed"),
        _make_queue_item(test_user.id, status="failed"),
    ]
    for item in items:
        db_session.add(item)
    await db_session.commit()
    for item in items:
        await db_session.refresh(item)

    count = await reset_stuck_queue_items(db_session)

    assert count == 0
    for item, expected in zip(items, ["queued", "completed", "failed"]):
        await db_session.refresh(item)
        assert item.status == expected


async def test_reset_returns_zero_when_nothing_stuck(db_session):
    """Returns 0 when no items are stuck."""
    count = await reset_stuck_queue_items(db_session)
    assert count == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_queue_startup_reset.py -v`
Expected: FAIL — `ImportError: cannot import name 'reset_stuck_queue_items' from 'app.main'`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_queue_startup_reset.py
git commit -m "test: add tests for queue startup reset logic"
```

---

### Task 2: Implement the reset function and call it in lifespan

**Files:**
- Modify: `backend/app/main.py:1-57`

- [ ] **Step 1: Add the `reset_stuck_queue_items` function and call it in lifespan**

Add the import at the top of `main.py` (with the existing imports):

```python
from sqlalchemy import update
from app.models.queue_item import QueueItem
```

Add the function before the `lifespan()` function:

```python
async def reset_stuck_queue_items(session) -> int:
    """Reset queue items stuck at 'processing' back to 'queued'.

    Called on startup to recover from crashes/restarts.
    """
    result = await session.execute(
        update(QueueItem)
        .where(QueueItem.status == "processing")
        .values(status="queued")
    )
    count = result.rowcount
    if count:
        await session.commit()
        logger.info(f"Reset {count} stuck queue item(s) from 'processing' to 'queued'.")
    return count
```

In the `lifespan()` function, add the reset call between the SMTP seed block and the scheduler creation:

```python
    # Reset queue items stuck at 'processing' from a previous crash
    async with async_session() as session:
        await reset_stuck_queue_items(session)
```

The lifespan function should look like this after the change:

```python
async def lifespan(app: FastAPI):
    await wait_for_db()
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)

    # Seed singleton config rows
    async with async_session() as session:
        result = await session.execute(select(SmtpConfig))
        if not result.scalar_one_or_none():
            session.add(SmtpConfig())
            await session.commit()
            logger.info("Seeded default SMTP config.")

    # Reset queue items stuck at 'processing' from a previous crash
    async with async_session() as session:
        await reset_stuck_queue_items(session)

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
```

- [ ] **Step 2: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_queue_startup_reset.py -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Run the full test suite to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "fix: reset stuck queue items on startup after crash/restart"
```
