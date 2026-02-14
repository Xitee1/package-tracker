# System Status Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the minimal admin System Status view with a rich dashboard showing live worker state (mode, scan timing, queue, current email), user-grouped folder hierarchy, historical stats with Chart.js graphs, and auto-polling with manual refresh.

**Architecture:** In-memory `_worker_state` dict for live worker data (mode, timing, queue), new `WorkerStats` DB model for hourly-bucketed processing counts, enhanced `/system/status` API returning user-grouped hierarchy, separate `/system/stats` endpoint for chart data. Frontend rebuilt with summary cards, Chart.js graph, and collapsible user/account/folder tree.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Vue 3 Composition API, TypeScript, Tailwind CSS 4, Chart.js + vue-chartjs, Pinia, vue-i18n

---

### Task 1: WorkerState dataclass and in-memory state dict

**Files:**
- Modify: `backend/app/services/imap_worker.py`

**Step 1: Add WorkerState dataclass and state dict**

Add at the top of `imap_worker.py`, after the existing `_running_tasks` dict:

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

@dataclass
class WorkerState:
    folder_id: int
    account_id: int
    mode: str = "connecting"  # "idle" | "polling" | "processing" | "connecting" | "error_backoff"
    last_scan_at: datetime | None = None
    next_scan_at: datetime | None = None
    last_activity_at: datetime | None = None
    queue_total: int = 0
    queue_position: int = 0
    current_email_subject: str | None = None
    current_email_sender: str | None = None
    error: str | None = None

_worker_state: dict[int, WorkerState] = {}
```

**Step 2: Instrument `_watch_folder` with state updates**

Update the `_watch_folder` function to set state at each phase:

1. At loop start (after `while True`, before `try`): init/update state to `mode="connecting"`, clear queue fields
2. After `imap.select()` succeeds and UIDs are fetched: set `queue_total=len(uids)`, `mode="processing"` (or `"idle"` if no UIDs)
3. Inside the per-UID loop, before `process_email()`: set `queue_position`, `current_email_subject`, `current_email_sender`, `last_activity_at=now`
4. After the UID loop completes: set `last_scan_at=now`, clear queue/current fields
5. Before IDLE: set `mode="idle"`, `last_activity_at=now`
6. Before polling sleep (IDLE fallback): set `mode="polling"`, compute `next_scan_at=now+polling_interval`
7. In the `except Exception` block: set `mode="error_backoff"`, `error=str(e)`, `next_scan_at=now+30s`
8. In `start_all_watchers`: init `_worker_state[folder.id]` when creating task
9. In `stop_all_watchers`: clear `_worker_state`

**Step 3: Export `_worker_state` for the API**

It's already module-level, so the system API can import it like it imports `_running_tasks`.

**Step 4: Commit**

```bash
git add backend/app/services/imap_worker.py
git commit -m "feat(worker): add in-memory WorkerState tracking to IMAP worker"
```

---

### Task 2: WorkerStats DB model

**Files:**
- Create: `backend/app/models/worker_stats.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create the model**

```python
# backend/app/models/worker_stats.py
from datetime import datetime

from sqlalchemy import Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkerStats(Base):
    __tablename__ = "worker_stats"
    __table_args__ = (
        UniqueConstraint("folder_id", "hour_bucket", name="uq_worker_stats_folder_hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id: Mapped[int] = mapped_column(Integer, ForeignKey("watched_folders.id", ondelete="CASCADE"))
    hour_bucket: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    emails_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
```

**Step 2: Register in models/__init__.py**

Add to imports and `__all__`:

```python
from app.models.worker_stats import WorkerStats
# Add "WorkerStats" to __all__
```

**Step 3: Commit**

```bash
git add backend/app/models/worker_stats.py backend/app/models/__init__.py
git commit -m "feat(models): add WorkerStats model for hourly processing stats"
```

---

### Task 3: Alembic migration for worker_stats table

**Files:**
- Create: new migration in `backend/alembic/versions/`

**Step 1: Generate the migration**

```bash
cd /home/mato/projects/tools/package-tracker/backend
alembic revision --autogenerate -m "add worker_stats table"
```

**Step 2: Review the generated migration**

Verify it creates the `worker_stats` table with columns: `id`, `folder_id`, `hour_bucket`, `emails_processed`, `errors_count`, the foreign key, and the unique constraint.

**Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): add migration for worker_stats table"
```

---

### Task 4: Stats recording helper in imap_worker

**Files:**
- Modify: `backend/app/services/imap_worker.py`

**Step 1: Add upsert helper function**

Add a function that increments stats using PostgreSQL `INSERT ... ON CONFLICT UPDATE`:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.worker_stats import WorkerStats

async def _record_stat(db, folder_id: int, *, processed: int = 0, errors: int = 0):
    """Increment hourly stats for a folder using upsert."""
    bucket = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    stmt = pg_insert(WorkerStats).values(
        folder_id=folder_id,
        hour_bucket=bucket,
        emails_processed=processed,
        errors_count=errors,
    ).on_conflict_do_update(
        constraint="uq_worker_stats_folder_hour",
        set_={
            "emails_processed": WorkerStats.emails_processed + processed,
            "errors_count": WorkerStats.errors_count + errors,
        },
    )
    await db.execute(stmt)
    await db.commit()
```

**Step 2: Call `_record_stat` in `_watch_folder`**

- After successful `process_email()`: call `await _record_stat(db, folder_id, processed=1)`
- In per-email exception handling (if added): call `await _record_stat(db, folder_id, errors=1)`
- In the outer `except Exception` block: call `await _record_stat(db, folder_id, errors=1)` (wrap in try/except to not break error recovery)

**Step 3: Commit**

```bash
git add backend/app/services/imap_worker.py
git commit -m "feat(worker): record hourly processing stats via upsert"
```

---

### Task 5: Enhanced system status API endpoint

**Files:**
- Modify: `backend/app/api/system.py`

**Step 1: Rewrite the `/status` endpoint**

Replace the current minimal endpoint with one that:
1. Queries `WatchedFolder -> EmailAccount -> User` grouped by user
2. Merges `_worker_state` for each folder's live data
3. Merges `_running_tasks` for running/error status
4. Returns the hierarchical response structure from the design

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.email_account import EmailAccount, WatchedFolder
from app.models.user import User
from app.services.imap_worker import _running_tasks, _worker_state

@router.get("/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    # Query all watched folders with account and user info
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.email_accounts)
            .selectinload(EmailAccount.watched_folders)
        )
    )
    users = result.scalars().unique().all()

    total_folders = 0
    running = 0
    errors = 0
    queue_total = 0
    processing_folders = 0

    users_data = []
    for user in users:
        accounts_data = []
        for account in user.email_accounts:
            folders_data = []
            for folder in account.watched_folders:
                total_folders += 1
                task = _running_tasks.get(folder.id)
                state = _worker_state.get(folder.id)
                is_running = task is not None and not task.done()
                task_error = str(task.exception()) if task and task.done() and task.exception() else None

                if is_running:
                    running += 1
                if task_error or (state and state.error):
                    errors += 1
                if state:
                    queue_total += max(0, state.queue_total - state.queue_position)
                    if state.mode == "processing":
                        processing_folders += 1

                folders_data.append({
                    "folder_id": folder.id,
                    "folder_path": folder.folder_path,
                    "running": is_running,
                    "mode": state.mode if state else ("stopped" if not is_running else "unknown"),
                    "last_scan_at": state.last_scan_at.isoformat() if state and state.last_scan_at else None,
                    "next_scan_at": state.next_scan_at.isoformat() if state and state.next_scan_at else None,
                    "last_activity_at": state.last_activity_at.isoformat() if state and state.last_activity_at else None,
                    "queue_total": state.queue_total if state else 0,
                    "queue_position": state.queue_position if state else 0,
                    "current_email_subject": state.current_email_subject if state else None,
                    "current_email_sender": state.current_email_sender if state else None,
                    "error": task_error or (state.error if state else None),
                })

            accounts_data.append({
                "account_id": account.id,
                "account_name": account.name,
                "is_active": account.is_active,
                "folders": folders_data,
            })

        if accounts_data:
            users_data.append({
                "user_id": user.id,
                "username": user.username,
                "accounts": accounts_data,
            })

    return {
        "global": {
            "total_folders": total_folders,
            "running": running,
            "errors": errors,
            "queue_total": queue_total,
            "processing_folders": processing_folders,
        },
        "users": users_data,
    }
```

**Step 2: Commit**

```bash
git add backend/app/api/system.py
git commit -m "feat(api): enhanced system status with user-grouped folder hierarchy"
```

---

### Task 6: Stats API endpoint

**Files:**
- Modify: `backend/app/api/system.py`

**Step 1: Add `/stats` endpoint**

```python
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from app.models.worker_stats import WorkerStats

@router.get("/stats")
async def system_stats(
    period: str = "hourly",
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    if period == "hourly":
        since = now - timedelta(hours=24)
        # Raw hourly rows, summed across all folders
        stmt = (
            select(
                WorkerStats.hour_bucket,
                func.sum(WorkerStats.emails_processed).label("emails_processed"),
                func.sum(WorkerStats.errors_count).label("errors_count"),
            )
            .where(WorkerStats.hour_bucket >= since)
            .group_by(WorkerStats.hour_bucket)
            .order_by(WorkerStats.hour_bucket)
        )
    elif period == "daily":
        since = now - timedelta(days=7)
        day_trunc = func.date_trunc("day", WorkerStats.hour_bucket)
        stmt = (
            select(
                day_trunc.label("bucket"),
                func.sum(WorkerStats.emails_processed).label("emails_processed"),
                func.sum(WorkerStats.errors_count).label("errors_count"),
            )
            .where(WorkerStats.hour_bucket >= since)
            .group_by(day_trunc)
            .order_by(day_trunc)
        )
    elif period == "weekly":
        since = now - timedelta(weeks=4)
        week_trunc = func.date_trunc("week", WorkerStats.hour_bucket)
        stmt = (
            select(
                week_trunc.label("bucket"),
                func.sum(WorkerStats.emails_processed).label("emails_processed"),
                func.sum(WorkerStats.errors_count).label("errors_count"),
            )
            .where(WorkerStats.hour_bucket >= since)
            .group_by(week_trunc)
            .order_by(week_trunc)
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid period. Use: hourly, daily, weekly")

    result = await db.execute(stmt)
    rows = result.all()

    buckets = [
        {
            "timestamp": row[0].isoformat() if row[0] else None,
            "emails_processed": row[1] or 0,
            "errors_count": row[2] or 0,
        }
        for row in rows
    ]

    return {"period": period, "buckets": buckets}
```

**Step 2: Add cleanup for old stats (optional helper)**

Add a function to delete rows older than 4 weeks, called at the start of the stats endpoint or as a periodic task:

```python
async def _cleanup_old_stats(db):
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=4)
    await db.execute(
        WorkerStats.__table__.delete().where(WorkerStats.hour_bucket < cutoff)
    )
    await db.commit()
```

**Step 3: Commit**

```bash
git add backend/app/api/system.py
git commit -m "feat(api): add /system/stats endpoint with hourly/daily/weekly aggregation"
```

---

### Task 7: Backend tests for system status and stats APIs

**Files:**
- Create: `backend/tests/test_system.py`

**Step 1: Write tests**

Tests should:
1. Create test user, account, watched folder in the DB
2. Test `GET /system/status` returns the hierarchical structure with correct fields
3. Test `GET /system/stats?period=hourly` returns empty buckets when no stats exist
4. Insert `WorkerStats` rows and verify aggregation for hourly/daily/weekly
5. Test invalid period returns 400

Use the existing `client` and `db_session` fixtures from conftest.py. Create admin user + JWT token for auth.

**Step 2: Run tests**

```bash
cd /home/mato/projects/tools/package-tracker/backend
pytest tests/test_system.py -v
```

Note: Stats tests using `date_trunc` will need to handle SQLite limitations in tests. Either mock the query or use simpler assertions for the test DB. The upsert in `_record_stat` uses PostgreSQL-specific `pg_insert`, so unit tests for the worker stats recording should mock the DB call or use a separate test that doesn't go through the upsert.

**Step 3: Commit**

```bash
git add backend/tests/test_system.py
git commit -m "test: add tests for system status and stats API endpoints"
```

---

### Task 8: Install Chart.js frontend dependencies

**Files:**
- Modify: `frontend/package.json` (via npm install)

**Step 1: Install chart.js and vue-chartjs**

```bash
cd /home/mato/projects/tools/package-tracker/frontend
npm install chart.js vue-chartjs
```

**Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add chart.js and vue-chartjs dependencies"
```

---

### Task 9: Update i18n locale files

**Files:**
- Modify: `frontend/src/i18n/locales/en.json`
- Modify: `frontend/src/i18n/locales/de.json`

**Step 1: Replace the `system` section in en.json**

```json
"system": {
    "title": "System Status",
    "loadingStatus": "Loading system status...",
    "loadFailed": "Failed to load system status.",
    "refresh": "Refresh",
    "lastRefreshed": "Last refreshed {seconds}s ago",
    "watchedFolders": "Watched Folders",
    "watchedFoldersValue": "{running} / {total} running",
    "processing": "Processing",
    "processingValue": "{count} emails across {folders} folders",
    "processingIdle": "Idle",
    "errors": "Errors",
    "todayActivity": "Today's Activity",
    "todayEmails": "{count} emails processed",
    "statsTitle": "Processing Activity",
    "statsHour": "Hour",
    "statsDay": "Day",
    "statsWeek": "Week",
    "emailsProcessed": "Emails Processed",
    "errorsCount": "Errors",
    "foldersCount": "{count} folders",
    "emailsQueued": "{count} emails queued",
    "noFolders": "No watched folders configured.",
    "modeIdle": "Listening (IDLE)",
    "modePolling": "Polling",
    "modeProcessing": "Processing",
    "modeConnecting": "Connecting...",
    "modeErrorBackoff": "Error (retrying in {seconds}s)",
    "modeStopped": "Stopped",
    "modeUnknown": "Unknown",
    "lastActivity": "last activity: {time}",
    "lastScan": "last scan: {time}",
    "nextCheck": "next check in {time}",
    "queueIdle": "idle",
    "queueProcessing": "Processing email {position} of {total}",
    "timeAgo": "{value} ago",
    "timeSeconds": "{count}s",
    "timeMinutes": "{count}m",
    "timeHours": "{count}h",
    "noStats": "No processing data available yet."
}
```

**Step 2: Add corresponding German translations in de.json**

Translate all keys in the `system` section to German.

**Step 3: Commit**

```bash
git add frontend/src/i18n/locales/en.json frontend/src/i18n/locales/de.json
git commit -m "feat(i18n): add system status redesign translations"
```

---

### Task 10: Rewrite SystemView.vue — summary cards and polling

**Files:**
- Modify: `frontend/src/views/admin/SystemView.vue`

**Step 1: Rewrite the script section**

Replace the entire component with the new structure:
- TypeScript interfaces for the new API response shape (GlobalSummary, FolderStatus, AccountStatus, UserStatus, SystemStatus)
- `fetchStatus()` calls `GET /system/status`
- `fetchStats(period)` calls `GET /system/stats?period=<period>`
- Auto-poll with `setInterval` every 30 seconds, cleared on unmount
- `lastRefreshedAgo` computed from a reactive timestamp
- Helper function `formatTimeAgo(isoString)` for relative time display

**Step 2: Rewrite the template — top bar + summary cards**

- Title row with refresh button showing `lastRefreshedAgo`
- 4 summary cards in a grid:
  1. Watched Folders: `{running} / {total} running`
  2. Processing: `{queue_total} emails across {processing_folders} folders` or "Idle"
  3. Errors: count with red highlight
  4. Today's Activity: `{todayCount} emails processed` (sum from hourly stats for today)

**Step 3: Commit**

```bash
git add frontend/src/views/admin/SystemView.vue
git commit -m "feat(frontend): rewrite SystemView with summary cards and auto-polling"
```

---

### Task 11: SystemView — stats chart component

**Files:**
- Modify: `frontend/src/views/admin/SystemView.vue`

**Step 1: Add the chart section to the template**

Below the summary cards, add:
- A card with title "Processing Activity" and period toggle tabs (Hour / Day / Week)
- A `<Bar>` or `<Line>` chart from vue-chartjs showing `emails_processed` and `errors_count`
- Register Chart.js components (CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend)

**Step 2: Add chart data computation**

- Reactive `statsPeriod` ref defaulting to `"hourly"`
- `chartData` computed from `stats.buckets` — labels are formatted timestamps, two datasets (processed in blue/green, errors in red)
- `chartOptions` with responsive: true, proper scales

**Step 3: Wire up period toggle**

Clicking a tab calls `fetchStats(newPeriod)` and updates `statsPeriod`.

**Step 4: Commit**

```bash
git add frontend/src/views/admin/SystemView.vue
git commit -m "feat(frontend): add stats chart with period toggle to SystemView"
```

---

### Task 12: SystemView — user-grouped folder list

**Files:**
- Modify: `frontend/src/views/admin/SystemView.vue`

**Step 1: Add collapsible user sections**

Below the chart, render the folder list grouped by user:
- Each user section: collapsible with username header, folder count, queue summary
- Inside each user: account sub-sections with account name
- Inside each account: folder cards

**Step 2: Implement folder card**

Each folder card displays:
- Folder path as heading
- Mode badge with color coding:
  - `idle`: green, "Listening (IDLE)"
  - `polling`: blue, "Polling"
  - `processing`: amber/yellow, "Processing"
  - `connecting`: gray, "Connecting..."
  - `error_backoff`: red, "Error (retrying in Xs)"
  - `stopped`: gray, "Stopped"
- Timing line: "last activity: 3m ago" (always), "next check in 1m 30s" (polling), "last scan: 2m ago"
- Queue line: "idle" or "Processing email 3 of 5" with subject + sender on next line
- Error expandable section if error is present

**Step 3: Add collapse state**

Use a reactive `Set<number>` for expanded user IDs, toggle on click.

**Step 4: Commit**

```bash
git add frontend/src/views/admin/SystemView.vue
git commit -m "feat(frontend): add user-grouped collapsible folder list to SystemView"
```

---

### Task 13: Frontend build verification and lint

**Files:**
- No new files

**Step 1: Run type-check**

```bash
cd /home/mato/projects/tools/package-tracker/frontend
npm run type-check
```

Fix any TypeScript errors.

**Step 2: Run lint + format**

```bash
npm run lint
npm run format
```

**Step 3: Run build**

```bash
npm run build
```

Verify clean build with no errors.

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "style: fix lint and type errors in system status redesign"
```

---

### Task 14: Backend tests pass + final verification

**Files:**
- No new files

**Step 1: Run all backend tests**

```bash
cd /home/mato/projects/tools/package-tracker/backend
pytest tests/ -v
```

Fix any failures.

**Step 2: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test failures from system status redesign"
```
