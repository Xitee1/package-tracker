# Modular Architecture Design

## Overview

Redesign the Package Tracker architecture into a drop-in module system. Analysers and Providers become self-contained packages under `app/modules/`, each with its own models, schemas, routes, services, and a manifest. The core application discovers and registers modules at startup.

## Key Decisions

- **Registration**: Manifest-based (`MODULE_INFO` dict in each module's `__init__.py`)
- **Queue**: Core service, not a module (infrastructure that modules depend on)
- **Sidebar style**: Collapsible groups in the existing vertical tab list
- **Shared code**: `modules/_shared/email/` for IMAP utilities shared between email modules
- **Admin nav**: Users/System stay top-level; Settings sidebar contains Queue + module groups
- **Disabled UI**: Settings visible but greyed out when module is off

## Backend Architecture

### Module Base (`app/core/module_base.py`)

```python
MODULE_INFO = {
    "key": str,              # e.g. "email_user"
    "name": str,             # Human-readable
    "type": str,             # "analyser" or "provider"
    "version": str,
    "description": str,
    "router": APIRouter,     # Admin routes
    "user_router": APIRouter | None,  # User-facing routes
    "models": list,          # SQLAlchemy models for Alembic
    "startup": Callable | None,       # async startup hook
    "shutdown": Callable | None,      # async shutdown hook
}
```

### Module Registry (`app/core/module_registry.py`)

Scans `app/modules/analysers/` and `app/modules/providers/`, imports `MODULE_INFO`, registers routes and models, syncs `ModuleConfig` DB rows.

### Directory Structure

```
app/
├── core/
│   ├── auth.py
│   ├── encryption.py
│   ├── module_base.py             # ModuleManifest type definitions
│   └── module_registry.py         # Discovery, registration, lifecycle
├── modules/
│   ├── _shared/
│   │   └── email/
│   │       ├── imap_client.py     # IMAP connection, auth, folder listing
│   │       ├── imap_watcher.py    # IDLE/polling watch loop, UID tracking
│   │       ├── email_fetcher.py   # Fetch emails, dedup, enqueue
│   │       └── models.py          # ProcessedEmail
│   ├── analysers/
│   │   └── llm/
│   │       ├── __init__.py        # MODULE_INFO
│   │       ├── models.py          # LLMConfig
│   │       ├── schemas.py
│   │       ├── router.py          # Admin: /api/v1/modules/analysers/llm/
│   │       └── service.py         # LiteLLM integration
│   └── providers/
│       ├── email_global/
│       │   ├── __init__.py        # MODULE_INFO
│       │   ├── models.py          # GlobalMailConfig, UserSenderAddress
│       │   ├── schemas.py
│       │   ├── router.py          # Admin config routes
│       │   ├── user_router.py     # User sender address management
│       │   └── service.py         # Global watcher, sender gating
│       └── email_user/
│           ├── __init__.py        # MODULE_INFO
│           ├── models.py          # EmailAccount, WatchedFolder
│           ├── schemas.py
│           ├── router.py          # Admin IMAP settings
│           ├── user_router.py     # User account CRUD, folder management
│           └── service.py         # Per-user watcher
├── api/                           # Core routes only
│   ├── auth.py
│   ├── users.py
│   ├── orders.py
│   ├── queue.py
│   ├── queue_settings.py
│   ├── modules.py                 # Module toggle API
│   ├── system.py
│   └── api_keys.py
├── services/
│   ├── queue/                     # Queue worker + processor
│   └── orders/                    # Order matching + creation
├── models/                        # Core models only
│   ├── user.py
│   ├── order.py
│   ├── order_state.py
│   ├── queue_item.py
│   └── module_config.py
```

### API Routes

**Admin module routes (auto-registered):**
- `/api/v1/modules/analysers/llm/...`
- `/api/v1/modules/providers/email-global/...`
- `/api/v1/modules/providers/email-user/...`

**User module routes (auto-registered):**
- `/api/v1/providers/email-global/...` (sender addresses, inbox info)
- `/api/v1/providers/email-user/...` (accounts, folders)

**Core routes (unchanged):**
- `/api/v1/auth/...`, `/api/v1/users/...`, `/api/v1/orders/...`
- `/api/v1/queue/...`, `/api/v1/system/...`
- `/api/v1/modules` (list + toggle)

### Module Lifecycle

**Startup:**
1. Alembic migrations
2. `module_registry.discover_modules()` scans module directories
3. Mount each module's routers
4. Sync `ModuleConfig` rows in DB
5. Call `startup()` for each enabled module

**Enable/Disable (`PUT /api/v1/modules/{key}`):**
1. Update `ModuleConfig.enabled`
2. Disabling: call module's `shutdown()` (stop watchers)
3. Enabling: call module's `startup()` (start watchers)

### Module Dependency Rules

Modules can import from:
- `app.core.*`, `app.models.*`, `app.services.*`
- `app.modules._shared.*`

Modules must NOT import from each other.

## Frontend Architecture

### Directory Structure

```
frontend/src/
├── modules/
│   ├── analysers/
│   │   └── llm/
│   │       ├── index.ts                   # Module manifest
│   │       └── AdminLLMConfigView.vue
│   └── providers/
│       ├── email-global/
│       │   ├── index.ts                   # Module manifest
│       │   ├── AdminGlobalMailView.vue
│       │   ├── UserForwardingView.vue
│       │   └── store.ts
│       └── email-user/
│           ├── index.ts                   # Module manifest
│           ├── AdminImapSettingsView.vue
│           ├── UserImapAccountsView.vue
│           └── store.ts
├── core/
│   └── moduleRegistry.ts                 # Discovery + registration
├── components/
│   ├── AppLayout.vue                     # Dynamic sidebar
│   └── ModuleHeader.vue                  # Reusable on/off header
├── views/                                # Core views only
│   ├── admin/
│   │   ├── SettingsView.vue              # Collapsible sidebar shell
│   │   └── QueueSettingsView.vue
│   └── ...
```

### Frontend Module Manifest

```typescript
export const MODULE_INFO = {
  key: 'email-global',
  name: 'Email - Global/Redirect',
  type: 'provider' as const,
  adminRoutes: [
    { path: 'email-global', component: () => import('./AdminGlobalMailView.vue') }
  ],
  userRoutes: [
    { path: 'email-global', component: () => import('./UserForwardingView.vue'), label: 'Email Redirect' }
  ],
}
```

### Admin Settings Sidebar

Collapsible groups in the vertical tab list:

```
Queue
▼ Analysers
    LLM Config
▼ Providers
    Email - Global/Redirect
    Email - User
```

### User Sidebar

```
Dashboard
Orders
History
▼ Providers
    Email Redirect          (email-global, if enabled)
    Email IMAP              (email-user, if enabled)
Profile
```

### Module Header Component

Every module settings page gets a consistent header with the module name, description, and on/off toggle. When off, the form below is visible but greyed out.

## Data Flow (Post-Refactor)

```
Provider Module → enqueues QueueItem → Core Queue Worker → Analyser Module → Core Order Matcher → Order
```

## Migration Mapping

### Backend: Files That Move

| From | To |
|---|---|
| `api/llm.py` | `modules/analysers/llm/router.py` |
| `models/llm_config.py` | `modules/analysers/llm/models.py` |
| `schemas/llm.py` | `modules/analysers/llm/schemas.py` |
| `services/llm_service.py` | `modules/analysers/llm/service.py` |
| `api/global_mail.py` | `modules/providers/email_global/router.py` |
| `api/sender_addresses.py` | `modules/providers/email_global/user_router.py` |
| `models/global_mail_config.py` | `modules/providers/email_global/models.py` |
| `models/sender_address.py` | `modules/providers/email_global/models.py` |
| `schemas/global_mail.py` | `modules/providers/email_global/schemas.py` |
| `schemas/sender_address.py` | `modules/providers/email_global/schemas.py` |
| `api/accounts.py` | `modules/providers/email_user/router.py` + `user_router.py` |
| `models/email_account.py` | `modules/providers/email_user/models.py` |
| `models/watched_folder.py` | `modules/providers/email_user/models.py` |
| `schemas/account.py` | `modules/providers/email_user/schemas.py` |
| `api/imap_settings.py` | `modules/providers/email_user/router.py` |
| `services/imap_worker.py` (shared logic) | `modules/_shared/email/` |
| `models/processed_email.py` | `modules/_shared/email/models.py` |

### Frontend: Files That Move

| From | To |
|---|---|
| `views/admin/LLMConfigView.vue` | `modules/analysers/llm/AdminLLMConfigView.vue` |
| `views/admin/GlobalMailConfigView.vue` | `modules/providers/email-global/AdminGlobalMailView.vue` |
| `views/AccountsForwardingView.vue` | `modules/providers/email-global/UserForwardingView.vue` |
| `views/admin/ImapSettingsView.vue` | `modules/providers/email-user/AdminImapSettingsView.vue` |
| `views/AccountsImapView.vue` | `modules/providers/email-user/UserImapAccountsView.vue` |
| `stores/accounts.ts` | `modules/providers/email-user/store.ts` |
| `stores/senderAddresses.ts` | `modules/providers/email-global/store.ts` |

### Files Deleted

- `views/admin/ModulesView.vue` (replaced by per-module toggle headers)
- `views/AccountsView.vue` (replaced by individual module user pages)
- `api/module_deps.py` (replaced by module registry gating)

### No Schema Changes

Models stay the same, just move files. Alembic discovers models via module registry imports.
