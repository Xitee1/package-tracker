# System Status Redesign

## Problem

The current admin System Status view shows minimal information: worker count, running/stopped boolean, and error strings. Folder workers are identified only by `folder_id`. There's no visibility into scan timing, processing state, email queue, or historical activity.

## Approach

In-memory state for live worker data + DB table for historical stats. Auto-polling with manual refresh (WebSocket upgrade path later).

## Backend: In-Memory Worker State

New `_worker_state: dict[int, WorkerState]` in `imap_worker.py` alongside existing `_running_tasks`:

```python
@dataclass
class WorkerState:
    folder_id: int
    account_id: int
    mode: str              # "idle" | "polling" | "processing" | "connecting" | "error_backoff"
    last_scan_at: datetime | None
    next_scan_at: datetime | None
    last_activity_at: datetime | None
    queue_total: int       # emails found in current scan
    queue_position: int    # current email index (1-based)
    current_email_subject: str | None
    current_email_sender: str | None
    error: str | None
```

Updated at key points in `_watch_folder`:
- Loop start: `mode = "connecting"`
- After UID search: `queue_total = len(uids)`, `mode = "processing"`
- Per email: `queue_position++`, `current_email_subject/sender`, `last_activity_at = now`
- After all emails: `mode = "idle"` or `"polling"`, `last_scan_at = now`, compute `next_scan_at`
- On exception: `mode = "error_backoff"`

## Backend: Stats Persistence

New model `WorkerStats` with hourly-bucketed rows:

```python
class WorkerStats(Base):
    __tablename__ = "worker_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    folder_id: Mapped[int] = mapped_column(ForeignKey("watched_folders.id", ondelete="CASCADE"))
    hour_bucket: Mapped[datetime]  # truncated to hour
    emails_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
```

Unique constraint on `(folder_id, hour_bucket)`. Worker increments via upsert after each `process_email()` call (success or error). Rows older than 4 weeks cleaned up periodically.

## Backend: Enhanced Status API

### `GET /api/v1/system/status`

```json
{
    "global": {
        "total_folders": 5,
        "running": 4,
        "errors": 1,
        "queue_total": 7,
        "processing_folders": 2
    },
    "users": [
        {
            "user_id": 1,
            "username": "mato",
            "accounts": [
                {
                    "account_id": 1,
                    "account_name": "Gmail",
                    "is_active": true,
                    "folders": [
                        {
                            "folder_id": 3,
                            "folder_path": "INBOX/Receipts",
                            "running": true,
                            "mode": "processing",
                            "last_scan_at": "2026-02-13T14:02:00Z",
                            "next_scan_at": null,
                            "last_activity_at": "2026-02-13T14:03:12Z",
                            "queue_total": 5,
                            "queue_position": 3,
                            "current_email_subject": "Your Amazon order has shipped",
                            "current_email_sender": "ship-confirm@amazon.com",
                            "error": null
                        }
                    ]
                }
            ]
        }
    ]
}
```

Joins `WatchedFolder -> EmailAccount -> User` for the hierarchy, merges `_worker_state` for live data.

### `GET /api/v1/system/stats?period=hourly|daily|weekly`

```json
{
    "period": "hourly",
    "buckets": [
        {"timestamp": "2026-02-13T13:00:00Z", "emails_processed": 12, "errors_count": 0},
        {"timestamp": "2026-02-13T14:00:00Z", "emails_processed": 5, "errors_count": 1}
    ]
}
```

Aggregation: hourly = last 24 raw rows, daily = last 7 days summed, weekly = last 4 weeks summed.

## Frontend: Redesigned SystemView

### Top Bar
Title + refresh button with "last refreshed: Xs ago" + auto-poll every 30s.

### Global Summary Cards (row of 4)
- **Watched Folders**: `4 / 5 running`
- **Processing**: `7 emails across 2 folders` or "Idle"
- **Errors**: count, red when > 0
- **Today's Activity**: emails processed today

### Stats Graph
Chart.js + vue-chartjs. Line/bar chart with toggle tabs: Hour / Day / Week. Shows emails processed + errors over time.

### User-Grouped Folder List
Collapsible sections: User -> Account -> Folder cards.

Each user section header: username + folder count + queue summary.

Each folder card shows:
- **Folder path** as heading
- **Mode badge**: "Listening (IDLE)", "Polling", "Processing", "Connecting...", "Error (retrying in Xs)"
- **Timing**: last activity (always shown), next scan (polling mode), last scan
- **Queue state**: "idle" or "Processing email X of Y" with subject + sender
- **Error**: expandable error message if in error state

### New Dependency
- `chart.js` + `vue-chartjs` for the stats graph

## Data Flow

1. Worker loop updates `_worker_state` dict at each phase transition
2. Worker upserts `WorkerStats` row after each email processed
3. Frontend polls `GET /system/status` every 30s (or manual refresh)
4. Frontend fetches `GET /system/stats?period=hourly` independently for the graph
5. Future: WebSocket replaces polling for live state push
