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
    image: docker pull ghcr.io/xitee1/package-tracker:latest
    environment:
      PT_DATABASE_URL: 'postgresql+asyncpg://tracker:your-postgres-password@db:5432/tracker' # Make sure the credentials match with the ones set above
      PT_SECRET_KEY: 'change-me-to-a-random-string'
      PT_ENCRYPTION_KEY: 'change-me-to-a-random-string'
      PT_FRONTEND_URL: 'http://localhost:8055' # Used for generating links, e.g. for email verifications
    ports:
      - "8055:80"
    depends_on:
      - db
    restart: unless-stopped
```

### 2. Start the application

```bash
docker compose up -d
```

The application is available at `http://localhost:8055`.

### API Documentation

The backend provides interactive API docs:

- **Swagger UI** — `/api/docs`
- **ReDoc** — `/api/redoc`

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

