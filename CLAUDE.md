# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Package Tracker is a self-hosted app that connects to email inboxes via IMAP, analyzes emails using LLMs (via LiteLLM), extracts purchase/shipment info, and tracks orders in a web dashboard. Supports multiple users with admin capabilities.

## Tech Stack

- **Backend:** FastAPI (Python 3.12+, fully async), SQLAlchemy 2.0 async ORM, PostgreSQL 16, LiteLLM
- **Frontend:** Vue 3 (Composition API, `<script setup>`, TypeScript), Vite, Tailwind CSS 4, Pinia, Vue Router, Axios
- **Deployment:** Docker Compose (dev and prod configs)

## Development Commands

### Docker (recommended)

```bash
docker-compose up                              # Dev: backend:8000, frontend:5173, db:5432
docker-compose -f docker-compose.prod.yml up   # Prod: frontend on port 80
```

### Backend (from `backend/`)

```bash
pip install -e ".[dev]"                                  # Install with dev deps
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # Run dev server
pytest tests/ -v                                          # Run all tests
pytest tests/test_orders.py::test_list_orders -v           # Run single test
```

### Frontend (from `frontend/`)

```bash
npm install         # Install deps
npm run dev         # Vite dev server
npm run build       # Type-check + production build
npm run lint        # ESLint with --fix
npm run format      # Prettier
npm run type-check  # vue-tsc
```

## Architecture

### Backend (`backend/app/`)

All API routes are under `/api/v1/`. Routers live in `api/`, each included in `main.py`.

**Request flow:** API router (`api/`) → dependency injection for auth/db (`api/deps.py`) → service layer (`services/`) → ORM models (`models/`) → database

**Key services:**
- `imap_worker.py` — async IMAP IDLE/polling per watched folder, started/stopped via app lifespan in `main.py`
- `email_processor.py` — orchestrates: analyze email (LLM) → match to existing order → create/update order + event
- `llm_service.py` — calls LiteLLM with a system prompt to extract structured `EmailAnalysis` from email text
- `order_matcher.py` — 3-tier matching: exact order_number → exact tracking_number → fuzzy vendor+items

**Auth:** JWT (HS256) via HTTPBearer. Passwords hashed with bcrypt. IMAP passwords encrypted with Fernet. All sensitive config uses `PT_` env prefix (see `config.py`).

**Models:** `User` → has many `EmailAccount` → has many `WatchedFolder`. `User` → has many `Order` → has many `OrderEvent`. `LLMConfig` is a global singleton. `OrderEvent` stores `llm_raw_response` for debugging.

### Frontend (`frontend/src/`)

**Routing:** `router/index.ts` with guards — `requiresAuth`, `requiresAdmin`, `guest` meta flags. Public: `/login`, `/setup`. Protected: `/dashboard`, `/orders`, `/accounts`, `/settings`. Admin: `/admin/*`.

**State:** Pinia stores in `stores/` — `auth.ts` (JWT in localStorage, user state), `orders.ts`, `accounts.ts`.

**API client:** `api/client.ts` — Axios instance, request interceptor adds JWT, response interceptor handles 401 → logout.

**Layout:** `AppLayout.vue` wraps all authenticated views with sidebar + mobile-responsive top bar.

### Vite Proxy

In dev, Vite proxies `/api` requests to `http://backend:8000` (Docker service name). When running outside Docker, update `vite.config.ts` proxy target to `http://localhost:8000`.

## Testing

Backend uses pytest with `pytest-asyncio` (`asyncio_mode = "auto"` in pyproject.toml). Tests use in-memory SQLite via aiosqlite. Fixtures in `tests/conftest.py` provide `db_session` and `client` (httpx AsyncClient with ASGI transport). FastAPI dependency overrides swap the real DB for the test DB.

## Configuration

Environment variables use `PT_` prefix (Pydantic Settings in `config.py`):
- `PT_DATABASE_URL` — PostgreSQL connection string (asyncpg)
- `PT_SECRET_KEY` — JWT signing key
- `PT_ENCRYPTION_KEY` — Fernet key for IMAP password encryption

See `.env.example` for all options.
