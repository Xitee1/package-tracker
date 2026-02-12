# WIP: Package Tracker

> [!NOTE]  
> This tool was at least 99% written by AI. Altough I have tested it and it seems to work as it should, use with care and expect things to go really wrong.

A self-hosted application that monitors your email inboxes and automatically tracks your online orders and shipments. It uses an LLM to analyze incoming emails and extract order details, tracking numbers, and delivery status updates into a unified dashboard.

## Features

- **Automatic email monitoring** — connects to email accounts via IMAP and watches specified folders for new messages
- **LLM-powered extraction** — uses AI to identify purchase confirmations, shipping notifications, and delivery updates from email content
- **Multi-provider LLM support** — works with OpenAI, Anthropic, Ollama, or any custom OpenAI-compatible endpoint (via LiteLLM)
- **Order tracking dashboard** — view all orders with status, tracking numbers, carriers, items, and a timeline of events
- **Multi-user** — supports multiple users, each with their own email accounts and orders
- **Admin controls** — manage users, configure the LLM provider, and monitor system status

## Quick Start

### Prerequisites

- Docker and Docker Compose

### 1. Clone and configure

```bash
git clone <repo-url> package-tracker
cd package-tracker
cp .env.example .env
```

Edit `.env` and set secure values:

```
PT_SECRET_KEY=<random-string>
PT_ENCRYPTION_KEY=<random-string>
POSTGRES_PASSWORD=<random-string>
```

You can generate random strings with `openssl rand -hex 32`.

### 2. Start the application

**Development:**

```bash
docker compose up
```

The frontend is available at `http://localhost:5173` and the API at `http://localhost:8000`.

**Production:**

```bash
docker compose -f docker-compose.prod.yaml up -d
```

The application is available at `http://localhost` (port 80, configurable via `PORT` in `.env`).

### API Documentation

The backend provides interactive API docs powered by FastAPI:

- **Swagger UI** — `/api/docs`
- **ReDoc** — `/api/redoc`

### 3. Initial setup

Open the application in your browser. On first launch you'll be directed to a setup page to create the admin account.

### 4. Configure the LLM

Go to **Admin > LLM Configuration** and set up your LLM provider:

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

## How It Works

1. **IMAP worker** — a background task per watched folder uses IMAP IDLE (push notifications) with a polling fallback to detect new emails
2. **Email analysis** — new emails are sent to the configured LLM, which extracts structured data (order number, tracking number, carrier, vendor, items, status, etc.)
3. **Order matching** — the system matches the analysis to existing orders by order number, tracking number, or vendor + item similarity
4. **Order updates** — if a matching order is found it updates the status; otherwise it creates a new order. Every change is recorded as an event with the raw LLM response for auditability

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
| `PT_SECRET_KEY` | Production | Secret key for signing JWT tokens |
| `PT_ENCRYPTION_KEY` | Production | Key for encrypting stored IMAP passwords |
| `PT_DATABASE_URL` | No | PostgreSQL connection string (default set in Docker) |
| `POSTGRES_PASSWORD` | Production | Database password |
| `PORT` | No | Frontend port in production (default: `80`) |

## License

See [LICENSE](LICENSE) for details.
