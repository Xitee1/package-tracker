# Queue Architecture Redesign

## Problem

The backend logic is too clustered and tightly coupled. Email fetching, LLM processing, order matching, and order creation all happen inline in the IMAP worker. This makes it hard to extend with new sources, retry failed processing, or inspect what's happening.

## Solution

Separate the backend into three clean layers:

- **Source layer** — fetches data (IMAP emails, future: manual input, API)
- **Queue layer** — decoupled processing pipeline with inspectable state
- **Order layer** — creates/updates orders with status history

```
Source (IMAP) → ProcessedEmail (dedup) → QueueItem → QueueWorker → Order + OrderState
```

## Data Model

### QueueItem (new table)

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | FK → User | Owner |
| status | enum | `queued`, `processing`, `completed`, `failed` |
| source_type | string | `email`, future: `manual`, `api` |
| source_info | string | Human-readable origin, e.g. `"user@mail.com / Inbox.Tracking"` |
| raw_data | JSON | Source-provided data (email subject, body, sender, date, uid, message_id) |
| extracted_data | JSON, nullable | LLM/processor output (structured order data) |
| error_message | string, nullable | Error details when status=failed |
| order_id | FK → Order, nullable | Set after successful order matching |
| cloned_from_id | FK → self, nullable | For retry: points to original item |
| created_at | datetime | |
| updated_at | datetime | |

### Order (revised — keeps stable fields)

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | FK → User | |
| status | string | Denormalized from latest OrderState for fast queries |
| order_number | string, nullable | Stable identifier |
| tracking_number | string, nullable | Stable identifier |
| carrier | string, nullable | |
| vendor_name | string, nullable | |
| vendor_domain | string, nullable | |
| order_date | date, nullable | |
| total_amount | decimal, nullable | |
| currency | string, nullable | |
| items | JSON | |
| estimated_delivery | date, nullable | |
| created_at | datetime | |
| updated_at | datetime | |

### OrderState (new table — status timeline)

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| order_id | FK → Order | |
| status | string | `ordered`, `shipment_preparing`, `shipped`, `in_transit`, `out_for_delivery`, `delivered` |
| source_type | string, nullable | What triggered this transition |
| source_info | string, nullable | Human-readable source details |
| created_at | datetime | When this state was recorded |

Linked to Order, not QueueItem. Survives queue retention cleanup.

### ProcessedEmail (replaces EmailScan — lightweight dedup)

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| account_id | FK → EmailAccount | |
| folder_path | string | |
| email_uid | int | IMAP UID |
| message_id | string, unique | RFC message ID for dedup |
| queue_item_id | FK → QueueItem, nullable | Links to queue item created for this email |
| created_at | datetime | |

No subject, sender, is_relevant, llm_raw_response — all of that moves to QueueItem.

### Dropped Tables

- `EmailScan` → replaced by `ProcessedEmail` + `QueueItem`
- `OrderEvent` → replaced by `OrderState`
- `ScanHistorySettings` → replaced by queue retention settings
- `WorkerStats` → derivable from QueueItem counts

### Unchanged Tables

`User`, `EmailAccount`, `WatchedFolder`, `LLMConfig`, `ImapSettings`, `ApiKey`

## Services & Workers

### Source Layer (`services/sources/`)

- `imap_source.py` — IMAP watcher. Fetches emails, records in `ProcessedEmail` for dedup, creates `QueueItem` with `source_type="email"` and raw email data. No LLM calls, no order logic.

### Queue Layer (`services/queue/`)

- `queue_worker.py` — scheduled job (every 5s). Picks one `QueueItem` with `status=queued`, sets to `processing`, calls processor, updates to `completed`/`failed`. Sequential processing, architected for future concurrency.
- `queue_processor.py` — takes raw_data, calls LLM, returns extracted_data. Pure transformation.
- `queue_retention.py` — scheduled job (every 10 min). Cleans up old QueueItems based on admin-configured max_age_days (default: 7) and max_per_user (default: 5000).

### Order Layer (`services/orders/`)

- `order_service.py` — creates/updates Orders and inserts OrderState entries.
- `order_matcher.py` — pluggable matching interface. Default: 3-tier matching (exact order_number → exact tracking_number → fuzzy vendor+items). Strategy can be swapped.

### Existing Services

- `llm_service.py` — unchanged, called by `queue_processor.py`
- `scheduler.py` — registers all scheduled jobs. Single source of truth for job metadata.

### Scheduled Jobs

| Job | Interval | Description |
|---|---|---|
| QueueWorker | 5 seconds | Process next queued item |
| RetentionCleanup | 10 minutes | Clean up old QueueItems |

### Data Flow

```
IMAP Watcher (source)
  │ fetches new emails
  │ dedup via ProcessedEmail.message_id
  ▼
QueueItem created (status=queued, source_type="email", raw_data={...})
  │
  │ ← QueueWorker picks up (every 5s)
  │    sets status=processing
  ▼
QueueProcessor
  │ calls LLM via llm_service
  │ returns extracted_data
  ▼
QueueWorker
  │ sets extracted_data on QueueItem
  │ if not relevant: status=completed, done
  │ if relevant:
  │   ▼
  │ OrderMatcher.find_match()
  │   ▼
  │ OrderService.create_or_update()
  │   ├── creates/updates Order
  │   ├── inserts OrderState (if status changed)
  │   └── sets QueueItem.order_id
  │   ▼
  │ QueueItem status=completed
  │
  │ On error: status=failed, error_message set
```

### Error Handling

- **LLM unavailable:** status=failed, error_message set. Retryable from UI.
- **Unparseable LLM response:** same, error_message captures details.
- **Order matching/creation fails:** status=failed, extracted_data preserved so retry skips LLM.
- **Retry from UI:** clones QueueItem (new row, cloned_from_id set, status=queued, extracted_data=null).

## API

### Queue Endpoints (replace /scan-history)

| Method | Path | Description |
|---|---|---|
| GET | `/queue` | Paginated list. Filters: status, source_type, user_id (admin) |
| GET | `/queue/{id}` | Full detail including raw_data and extracted_data |
| DELETE | `/queue/{id}` | Delete item |
| POST | `/queue/{id}/retry` | Clone with status=queued, cloned_from_id set |
| GET | `/queue/stats` | Counts: `{queued, processing, completed, failed}` |

### Order Endpoints (updated)

| Method | Path | Description |
|---|---|---|
| GET | `/orders` | List orders (status on Order for fast filtering) |
| GET | `/orders/{id}` | Detail with `states: OrderState[]` ordered by created_at |
| PATCH | `/orders/{id}` | Update — creates OrderState if status changes |
| DELETE | `/orders/{id}` | Cascade deletes OrderStates |

### System Endpoints (updated)

| Method | Path | Description |
|---|---|---|
| GET | `/system/status` | Includes queue worker status and queue stats |

### Admin Settings (retention)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/settings/queue` | Get retention config (max_age_days, max_per_user) |
| PATCH | `/admin/settings/queue` | Update retention config |

### Dropped Endpoints

`/scan-history/*` — replaced by `/queue/*`

## UI

### Queue View (`/history` route, renamed)

- Table: Date, Source, Info, Status (badge), Relevant (badge), Order (link), Actions
- Actions: View Detail (modal), Retry (if failed/completed), Delete
- Detail modal tabs: Raw Data (JSON), Extracted Data (JSON), Error (if failed)
- Filters: status dropdown, source_type dropdown

### Order Detail View (`/orders/:id`)

- Timeline shows OrderState[] instead of OrderEvent[]
- Each entry: status badge, source_type/source_info, timestamp
- Visual status progression timeline

### System View (`/admin/system`)

- Queue Worker card: status, last execution, next execution
- Queue Stats card: queued / completed / failed counts
- Retention Cleanup card: last run, next run

### Admin Settings (`/admin/settings`)

- Queue settings section: max age (days), max items per user

## Design Decisions

1. **Sequential processing** — one item at a time, architected for future concurrency
2. **EmailScan → ProcessedEmail** — separate lightweight dedup from processing queue
3. **OrderState not OrderActivity** — status timeline with proper DB columns, linked to Order (survives queue retention)
4. **IMAP as pure source** — fetch and queue everything, no filtering or LLM calls
5. **Pluggable order matching** — strategy interface for future flexibility
6. **DB-backed queue with polling** — simple, inspectable, retryable from UI
7. **No HistoryCleanup job** — ProcessedEmail is tiny and kept for dedup; RetentionCleanup handles QueueItems
