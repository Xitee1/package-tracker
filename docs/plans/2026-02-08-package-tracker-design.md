# Package Tracker - Design Document

## Overview

A self-hosted application that connects to email inboxes via IMAP, uses AI (LLM) to analyze incoming emails for purchase and shipment information, and displays order/delivery status in a web dashboard. Supports multiple users, multiple email accounts, and multiple LLM providers.

## Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Vue 3 + Vite + Tailwind CSS |
| Backend | FastAPI (Python, async) |
| Database | PostgreSQL 16 |
| LLM Integration | LiteLLM (unified API for Ollama, OpenAI, Claude, etc.) |
| Auth | Built-in JWT, admin-managed users |
| Deployment | Docker Compose |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Docker Compose                  │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Frontend │  │ Backend  │  │  PostgreSQL   │  │
│  │ Vue 3    │──│ FastAPI  │──│              │  │
│  │ (nginx)  │  │          │  └──────────────┘  │
│  └──────────┘  │          │                     │
│                │  ┌───────┤                     │
│                │  │ IMAP  │── Email Servers      │
│                │  │Workers│                      │
│                │  └───────┤                     │
│                │  ┌───────┤                     │
│                │  │ LLM   │── Ollama/OpenAI/    │
│                │  │Client │   Claude/etc.        │
│                │  └───────┘                     │
│                └──────────┘                     │
└─────────────────────────────────────────────────┘
```

Three Docker Compose services:
- **frontend**: Vue 3 SPA served by nginx, proxies `/api` to backend
- **backend**: FastAPI app + async IMAP workers (one task per watched folder)
- **db**: PostgreSQL 16

The backend runs two concerns in one process: the REST API server and background IMAP workers. IMAP workers use IMAP IDLE for real-time push notifications with a configurable polling fallback (interval set per email account by the user).

## Data Model

### User
- `id`, `username`, `password_hash`, `is_admin`, `created_at`

### EmailAccount (many per user)
- `id`, `user_id`, `name`, `imap_host`, `imap_port`, `imap_user`
- `imap_password` (encrypted), `use_ssl`, `polling_interval_sec`
- `is_active`

### WatchedFolder (many per email account)
- `id`, `account_id`, `folder_path` (e.g. "INBOX/Orders")
- `last_seen_uid`

### Order (many per user)
- `id`, `user_id`
- `order_number` (nullable - shipment-only updates may not include it)
- `tracking_number` (nullable - added when shipment email arrives)
- `carrier` (nullable - DHL, UPS, FedEx, etc.)
- `vendor_name`, `vendor_domain`
- `status`: `ordered` | `shipment_preparing` | `shipped` | `in_transit` | `out_for_delivery` | `delivered`
- `order_date`, `total_amount`, `currency`
- `items` (JSON array: `[{name, quantity, price}]`)
- `estimated_delivery` (nullable)
- `created_at`, `updated_at`

### OrderEvent (many per order - audit trail)
- `id`, `order_id`
- `event_type`: `order_confirmed` | `shipment_added` | `status_update`
- `old_status`, `new_status`
- `source_email_message_id` (Message-ID header, for deduplication)
- `source_email_uid`, `source_folder`, `source_account_id`
- `llm_raw_response` (JSON - full LLM output for debugging)
- `created_at`

### LLMConfig (global, admin-only)
- `id`, `provider`, `model_name`, `api_key` (encrypted)
- `api_base_url` (for Ollama/custom endpoints)
- `is_active`

### Order Lifecycle

1. **Order confirmation email** → LLM detects `order_confirmation` → New Order created with status `ordered`
2. **Shipment confirmation email** → LLM detects `shipment_confirmation` → Matched to existing Order via `order_number` → `tracking_number` and `carrier` added, status updated to `shipped` (or `shipment_preparing`)
3. **Delivery service update email** → LLM detects `shipment_update` → Matched via `tracking_number` → Status updated (e.g. `in_transit` → `out_for_delivery`)
4. **Delivery confirmation email** → Matched via `tracking_number` → Status updated to `delivered`

### Matching Logic (priority order)
1. Exact match on `order_number`
2. Exact match on `tracking_number`
3. Fuzzy: same `vendor_domain` + overlapping item names + time proximity

## Email Processing Pipeline

```
New email detected (IMAP IDLE / poll)
        │
        ▼
  Fetch email content
  (subject, from, body as plain text + HTML)
        │
        ▼
  Dedup check: has this Message-ID been processed?
  ── yes ──▶ skip
        │ no
        ▼
  Convert HTML to plain text (html2text)
  Send to LLM via LiteLLM
        │
        ▼
  LLM returns structured JSON
  ── is_relevant: false ──▶ skip
        │ is_relevant: true
        ▼
  Validate response against Pydantic schema
  (retry once with correction prompt if invalid)
        │
        ▼
  Match to existing Order
  (order_number → tracking_number → fuzzy)
        │
   ┌────┴─────┐
   │ matched  │ no match
   ▼          ▼
  Update    Create new
  Order     Order
        │
        ▼
  Create OrderEvent (audit log with raw LLM response)
```

All emails go to the LLM (no pre-filtering) to avoid false negatives from keyword heuristics.

## LLM Prompt Design

### System Prompt
```
You are an email analysis assistant. Analyze the provided email and
extract purchase/shipping information. Return ONLY valid JSON matching
the schema below. If the email is not related to a purchase or
shipment, return {"is_relevant": false}.
```

### Expected JSON Schema
```json
{
  "is_relevant": true,
  "email_type": "order_confirmation | shipment_confirmation | shipment_update | delivery_confirmation",
  "order_number": "ABC-12345 or null",
  "tracking_number": "1Z999AA... or null",
  "carrier": "DHL | UPS | FedEx | ... or null",
  "vendor_name": "Amazon",
  "vendor_domain": "amazon.de",
  "status": "ordered | shipment_preparing | shipped | in_transit | out_for_delivery | delivered",
  "order_date": "2026-02-08 or null",
  "estimated_delivery": "2026-02-12 or null",
  "total_amount": 49.99,
  "currency": "EUR or null",
  "items": [
    {"name": "USB-C Cable", "quantity": 2, "price": 9.99}
  ]
}
```

For providers supporting structured output (OpenAI JSON mode, Claude tool use), those features are used. For others, prompt engineering + Pydantic validation with a single retry.

Raw LLM responses are always stored in `OrderEvent.llm_raw_response` for debugging.

## Authentication & Authorization

- **No self-registration** - admin manages all users
- **First-run setup**: `POST /auth/setup` creates the first admin account (only works when no users exist)
- **JWT tokens** for session management
- **Two roles**: admin and regular user
- **Admin-only**: user management, LLM configuration, system status
- **User**: manage own email accounts/folders, view own orders
- **Future**: API key support for external service integration

## API Design

All endpoints under `/api/v1`.

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user info |
| POST | `/auth/setup` | Create first admin (one-time) |

### Users (admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List users |
| POST | `/users` | Create user |
| PATCH | `/users/:id` | Update role |
| DELETE | `/users/:id` | Remove user |

### Email Accounts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts` | User's accounts |
| POST | `/accounts` | Add IMAP account |
| PATCH | `/accounts/:id` | Update account |
| DELETE | `/accounts/:id` | Remove account |
| POST | `/accounts/:id/test` | Test IMAP connection |
| GET | `/accounts/:id/folders` | List IMAP folders |

### Watched Folders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/accounts/:id/folders/watched` | List watched folders |
| POST | `/accounts/:id/folders/watched` | Add folder to watch |
| DELETE | `/accounts/:id/folders/watched/:fid` | Stop watching |

### Orders
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/orders` | List orders (filterable by status) |
| GET | `/orders/:id` | Order detail + events timeline |
| PATCH | `/orders/:id` | Manual edit |
| POST | `/orders/:id/link` | Manually link orders |
| DELETE | `/orders/:id` | Remove order |

### LLM Config (admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/llm/config` | Current LLM settings |
| PUT | `/llm/config` | Update LLM config |
| POST | `/llm/test` | Test LLM connection |

### System (admin only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/system/status` | Worker status, queue depth, error log |

## Frontend Views

1. **Dashboard** - Overview with status counts (ordered/shipped/in transit/delivered), recent activity feed
2. **Orders List** - Filterable table with status badges, search by vendor/order number
3. **Order Detail** - Full order info + event timeline showing each email that updated it
4. **Email Accounts** - Add/edit/remove IMAP accounts, select folders, test connection
5. **Settings** - User profile, password change
6. **Admin: Users** - Create/manage users, assign roles
7. **Admin: LLM Config** - Configure provider, model, API key, test connection
8. **Admin: System** - Worker status, processing queue, error log

## Project Structure

```
package-tracker/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/                    # DB migrations
│   ├── app/
│   │   ├── main.py                 # FastAPI app, startup/shutdown
│   │   ├── config.py               # Settings from env vars
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── email_account.py
│   │   │   ├── order.py
│   │   │   └── llm_config.py
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── api/                    # Route handlers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── accounts.py
│   │   │   ├── orders.py
│   │   │   ├── llm.py
│   │   │   └── system.py
│   │   ├── services/               # Business logic
│   │   │   ├── email_processor.py  # LLM analysis + order matching
│   │   │   ├── imap_worker.py      # IMAP IDLE + polling
│   │   │   ├── llm_service.py      # LiteLLM wrapper
│   │   │   └── order_matcher.py    # Matching logic
│   │   └── core/
│   │       ├── auth.py             # JWT + password hashing
│   │       └── encryption.py       # IMAP password / API key encryption
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   ├── src/
│   │   ├── views/                  # Dashboard, Orders, Settings, Admin
│   │   ├── components/             # Reusable UI components
│   │   ├── stores/                 # Pinia stores
│   │   ├── api/                    # API client
│   │   └── router/                 # Vue Router
│   └── ...
```

## Security

- IMAP passwords and LLM API keys encrypted at rest using Fernet symmetric encryption
- Encryption key provided via environment variable (`ENCRYPTION_KEY`)
- JWT secret key via environment variable (`SECRET_KEY`)
- Database URL via environment variable (`DATABASE_URL`)
- `.env.example` documents all required environment variables

## Future Enhancements (not in v1)

- Active carrier tracking via carrier APIs (DHL, UPS, FedEx, etc.)
- API key authentication for external service integration
- Push notifications (browser/mobile) for status changes
