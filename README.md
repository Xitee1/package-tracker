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
curl -O https://raw.githubusercontent.com/Xitee1/package-tracker/main/docker-compose.prod.yaml
```

Create a `.env` file with secure values:

```
PT_SECRET_KEY=<random-string>
PT_ENCRYPTION_KEY=<random-string>
POSTGRES_PASSWORD=<random-string>
```

You can generate random strings with `openssl rand -hex 32`.

### 2. Start the application

```bash
docker compose -f docker-compose.prod.yaml up -d
```

The application is available at `http://localhost` (port 80).

### 3. Initial setup

Open the application in your browser. On first launch you'll be directed to a setup page to create the admin account.

### 4. Configure the LLM

Go to **Admin > Analysers** and configure the LLM module:

| Provider | Required fields |
|----------|----------------|
| **OpenAI** | Model name (e.g. `gpt-4o`), API key |
| **Anthropic** | Model name (e.g. `claude-sonnet-4-5-20250929`), API key |
| **Ollama** | Model name (e.g. `llama3`), Base URL (e.g. `http://host.docker.internal:11434`) |
| **Custom** | Model name, API key and/or Base URL |

Use the **Test** button to verify the connection works.

### 5. Add an email account

Go to **Accounts** and add an email account:

1. Enter your IMAP server details (host, port, username, password)
2. Use **Test Connection** to verify it works
3. Browse the available folders and add one or more to watch (e.g. `INBOX`)

The application will begin monitoring the watched folders for new emails. When it finds a purchase or shipping-related email, it analyzes it with the LLM and creates or updates an order on your dashboard.

### API Documentation

The backend provides interactive API docs powered by FastAPI:

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

## Development Setup (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a PostgreSQL database — set `PT_DATABASE_URL` accordingly.

### Frontend

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PT_SECRET_KEY` | Yes | Secret key for signing JWT tokens |
| `PT_ENCRYPTION_KEY` | Yes | Key for encrypting stored IMAP/SMTP passwords |
| `PT_DATABASE_URL` | No | PostgreSQL connection string (default set in Docker) |
| `PT_FRONTEND_URL` | No | Frontend URL used in email verification links (default: `http://localhost:5173`) |
| `POSTGRES_PASSWORD` | Yes | Database password |
