# WIP: Package Tracker

> [!NOTE]
> This tool was at least 99% written by AI. Although I have tested it and it seems to work as it should, use with care and expect things to go really wrong.

A self-hosted application that monitors your email inboxes and automatically tracks your online orders and shipments. It uses an LLM to analyze incoming emails and extract order details, tracking numbers, and delivery status updates into a unified dashboard.

## Features
### Providers
Providers provide incoming data to package-tracker.
For example, the IMAP provider extracts data from incoming emails from online shops or shipping services.
- **User-based IMAP**\* - Users can add their own IMAP credentials and scan specific email folders directly from their account
- **Global IMAP**\* - Users redirect emails to a specific email address that the admin has set up. Better security than user-based IMAP.
- **DHL** _(to be implemented, according to AI they have a free push API)_

\* IMAP idle and configurable polling interval is supported

### Analysers
Analysers are used to process data from providers that only provide raw and unformatted data, in example for emails.
- **LLM** - Use AI to analyse data (OpenAI, Anthropic, Ollama)
- **Regex** _(to be implemented)_ - Define regex templates to extract data

### Notifications
Users can enable notification to get order status update notifications.
Currently the following methods are supported:
- email
- webhook

### Planned features
- Home Assistant integration
- Native Android App
- MCP Server

### Miscellaneous
- **order matching** — prevents duplicates by matching incoming emails to existing orders
- **API keys** — long-lived tokens for programmatic access alongside JWT auth
- **Multi-user with roles** — per-user data isolation, admin controls for user management
- Dark mode
- Multi-language support


## Quick Start

### Prerequisites

- Docker and Docker Compose

### 1. Configure

Create a directory and download the compose file:

```bash
mkdir package-tracker && cd package-tracker
```

Create a `docker-compose.yaml` file:
```yaml
# You can generate a random string with: openssl rand -hex 32
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: 'tracker'
      POSTGRES_PASSWORD: 'change-me-to-a-random-string'
      POSTGRES_DB: 'tracker'
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    restart: unless-stopped

  package-tracker:
    image: ghcr.io/xitee1/package-tracker:latest
    environment:
      PT_DATABASE_URL: 'postgresql+asyncpg://tracker:your-postgres-password@db:5432/tracker' # Make sure the credentials match with the ones set above
      PT_SECRET_KEY: 'change-me-to-a-another-random-string'
      PT_ENCRYPTION_KEY: 'change-me-to-a-yet-another-random-string'
      PT_FRONTEND_URL: 'http://localhost:8055' # Used for generating links, e.g. for email verifications
    ports:
      - "8055:80"
    depends_on:
      - db
    restart: unless-stopped
```

Make sure to change the following values:
`change-me-to-a-random-string`, `your-postgres-password`, `change-me-to-a-another-random-string`, `change-me-to-a-yet-another-random-string`

### 2. Start the application

```bash
docker compose up -d
```

The application is available at `http://localhost:8055`.

### API Documentation

The backend provides interactive API docs:

- **Swagger UI** — `/api/docs`
- **ReDoc** — `/api/redoc`

## How It Works

1. **Email provider** — a background worker per watched folder uses IMAP IDLE (push notifications) with a polling fallback to detect new emails
2. **Processing queue** — new emails are added to a queue and processed asynchronously by a scheduled worker (every 5 seconds)
3. **LLM analysis** — the configured LLM extracts structured data (order number, tracking number, carrier, vendor, items, status, etc.) from the email
4. **Order matching** — the system matches the analysis to existing orders by order number, tracking number, or vendor + item similarity
5. **Order updates** — if a matching order is found it updates the status; otherwise it creates a new order. Every status change is recorded as a state entry for auditability.
6. **Notifications** — configured notifiers (email, webhook) are triggered for relevant events

## Order Statuses

Orders progress through these statuses as emails are processed:

`ordered` → `shipment_preparing` → `shipped` → `in_transit` → `out_for_delivery` → `delivered`

## Admin CLI

A built-in `pt-admin` command is available for user management tasks like listing users and resetting passwords.

### Docker (production)

```bash
docker compose -f docker-compose.prod.yaml exec package-tracker python -m app.cli list-users
docker compose -f docker-compose.prod.yaml exec package-tracker python -m app.cli reset-password <username>
```

### Docker (development)

```bash
docker compose exec backend python -m app.cli list-users
docker compose exec backend python -m app.cli reset-password <username>
```

### Without Docker

```bash
cd backend
python -m app.cli list-users
python -m app.cli reset-password <username>
```

The `reset-password` command prompts for the new password interactively. Pass `--password <pw>` to skip the prompt.

## Development Setup

### With Docker (recommended)

```bash
docker compose up
```

This starts all three services:
- **Backend** at `http://localhost:8000` (with hot-reload)
- **Frontend** at `http://localhost:5173`
- **PostgreSQL** at `localhost:5432`

To rebuild after dependency changes:

```bash
docker compose up --build
```

### Without Docker

## Development Setup
### Without Docker
#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a PostgreSQL database — set `PT_DATABASE_URL` accordingly.

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` requests to the backend. When running outside Docker, update the proxy target in `vite.config.ts` from `http://backend:8000` to `http://localhost:8000`.

### Running Tests

```bash
cd backend
pytest tests/ -v
```

Tests use an in-memory SQLite database and don't require PostgreSQL.

