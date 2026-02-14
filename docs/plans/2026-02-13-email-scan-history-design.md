# Email Scan History Design

## Overview

Add a scan history feature that records every email the system processes (relevant or not), shows LLM analysis results as formatted JSON, and allows fetching the original email from the IMAP server on demand. Includes a centralized scheduler framework using APScheduler for background tasks like history cleanup.

## Data Model

### New `EmailScan` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | int PK | |
| `account_id` | int FK → email_accounts | non-nullable, cascade delete |
| `folder_path` | str | IMAP folder path |
| `email_uid` | int | IMAP UID |
| `message_id` | str | RFC Message-ID header, indexed, used for dedup |
| `subject` | str | |
| `sender` | str | |
| `email_date` | datetime | Date header from the email |
| `is_relevant` | bool | LLM determined it's package-related |
| `llm_raw_response` | JSON | Full LLM output (or error info) |
| `order_id` | int FK → orders | nullable, set if it created/updated an order |
| `rescan_queued` | bool | default false, signals worker to re-process |
| `created_at` | datetime | when scan happened |

User is reachable via `account.user_id` — no redundant `user_id` column.

### Dedup changes

`email_processor.py` checks `EmailScan.message_id` instead of `OrderEvent.source_email_message_id`.

### Rescan mechanism

Setting `rescan_queued = true` signals the worker to re-fetch and re-process that UID. After reprocessing, the existing row is updated with new LLM results (not a new row).

## Scheduler Framework

APScheduler 4 with async support, integrated into FastAPI's lifespan.

- `AsyncScheduler` with `SQLAlchemyDataStore` (reuses existing async engine)
- Jobs registered on startup, scheduler reference stored on `app.state`
- Job state persists across restarts via PostgreSQL

### Admin settings

- `scan_history_max_age_days` — delete entries older than N days (default: 7)
- `scan_history_max_per_user` — cap per user (default: 1000)
- `scan_history_cleanup_interval_hours` — how often cleanup runs (default: 1)

### System status extension

`/api/v1/system/status` extended with:

```json
{
  "scheduled_jobs": [
    {
      "id": "history_cleanup",
      "description": "Clean up old email scan history",
      "interval": "1h",
      "last_run_at": "2026-02-13T10:00:00Z",
      "next_run_at": "2026-02-13T11:00:00Z"
    }
  ]
}
```

## API Endpoints

### New: `/api/v1/scan-history`

| Method | Path | Description |
|--------|------|-------------|
| `GET /` | List scan history | Paginated, filterable by account, folder, is_relevant, date range |
| `GET /{scan_id}` | Single scan detail | Full LLM response JSON |
| `GET /{scan_id}/email` | Fetch original email | Connects to IMAP, fetches body by UID |
| `POST /{scan_id}/rescan` | Queue for rescan | Sets `rescan_queued = true` |
| `DELETE /{scan_id}` | Delete entry | Removes from history |

### Fetch email flow (`GET /{scan_id}/email`)

1. Look up `EmailScan` → get `account_id`, `folder_path`, `email_uid`
2. Open temporary IMAP connection (decrypt password, connect, login)
3. Select folder, fetch message by UID
4. Convert HTML → plaintext (same as existing processing)
5. Return `{ subject, sender, date, body_text }` or 404 if unavailable
6. Close connection immediately after

### Rescan flow

1. User clicks "Rescan" → `POST /{scan_id}/rescan` sets `rescan_queued = true`
2. User triggers "Scan Now" on the watched folder
3. Worker starts normal UID watermark scan, also queries `EmailScan` for `rescan_queued = true` rows matching that folder/account
4. For each queued entry: fetch by UID, re-run `process_email`, update row, set `rescan_queued = false`
5. If email no longer on server, mark error on the scan entry

### Changes to `email_processor.py`

- After LLM analysis (relevant or not), create/update `EmailScan` row
- Dedup: check `EmailScan.message_id` instead of `OrderEvent.source_email_message_id`
- If relevant and order created/matched, set `EmailScan.order_id`

## Frontend

### Routing & sidebar

- New "History" sidebar entry in `AppLayout.vue`, between Orders and Accounts
- Route: `/history` → `HistoryView.vue` (requiresAuth)

### History list view

- Table: Date, Subject, Sender, Account, Relevant (badge), Order (link), Actions
- Filters: account dropdown, relevant/not-relevant/all toggle, date range
- Pagination (backend-driven)
- Row actions: View, Rescan, Delete
- Rescan button shows indicator when `rescan_queued = true`

### History detail (modal or expandable row)

- Basic info: subject, sender, date, account, folder
- LLM result: formatted JSON in collapsible code block
- Linked order: clickable link to `/orders/:id`
- "Fetch Email" button → loads plain text body from IMAP
  - Loading state while connecting
  - "Email no longer available on server" on 404
- Rescan button available here too

### System view changes

- New "Scheduled Jobs" section in `SystemView.vue`
- Each job: name, description, interval, last run, next run

### i18n

All new strings added to existing translation files.
