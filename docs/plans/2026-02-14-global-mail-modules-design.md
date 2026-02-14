# Global Mail & Module System Design

## Summary

Add a global mail account (admin-configured, singleton IMAP inbox) that users forward emails to. The system maps incoming emails to users by their registered sender addresses before processing. Additionally, introduce a module system so admins can enable/disable `email-imap` (user-managed IMAP accounts) and `email-global` (forwarding to global inbox) independently.

## Data Models

### GlobalMailConfig (singleton)

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK |
| imap_host | str | |
| imap_port | int | default 993 |
| imap_user | str | |
| imap_password_encrypted | str | Fernet-encrypted |
| use_ssl | bool | default True |
| polling_interval_sec | int | default 300 |
| use_polling | bool | default False |
| idle_supported | bool \| None | detected at runtime |
| is_active | bool | default False |
| watched_folder_path | str | default "INBOX" |
| last_seen_uid | int | default 0 |
| uidvalidity | int \| None | IMAP UID validity |

### UserSenderAddress

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK |
| user_id | int | FK to User |
| email_address | str | unique across all users |
| created_at | datetime | |

### ModuleConfig

| Column | Type | Notes |
|--------|------|-------|
| id | int | PK |
| module_key | str | unique, e.g. "email-imap", "email-global" |
| enabled | bool | default True |

### ProcessedEmail changes

- `account_id` becomes nullable
- New `source` column: `"user_account"` (default) or `"global_mail"`

## Backend API

### `/api/v1/settings/global-mail` (admin only)

- `GET /` — Get global mail config (or defaults)
- `PUT /` — Upsert global mail config
- `POST /test` — Test IMAP connection
- `GET /folders` — List available IMAP folders

### `/api/v1/settings/global-mail/info` (authenticated users)

- `GET /` — Returns just the email address to forward to (not credentials)

### `/api/v1/modules`

- `GET /` — List all modules with enabled status (authenticated users)
- `PUT /{module_key}` — Toggle module (admin only)

### `/api/v1/sender-addresses` (authenticated users)

- `GET /` — List current user's sender addresses
- `POST /` — Register new address (409 if duplicate across any user)
- `DELETE /{id}` — Remove a sender address

### Module enforcement

- Accounts router (`/api/v1/accounts`): returns 403 if `email-imap` disabled
- Sender-addresses router: returns 403 if `email-global` disabled

## IMAP Worker Changes

### Global account watcher

`start_all_watchers()` also starts a `_watch_global_folder()` task if `GlobalMailConfig` is active and `email-global` module is enabled.

`_watch_global_folder()` uses the same IDLE/polling logic but with a sender gate:

1. Fetch new email
2. Extract FROM address
3. Look up in `UserSenderAddress`
4. No match: log and discard
5. Match: create `QueueItem` with matched user's `user_id`

`ProcessedEmail` records for global mail have `account_id=NULL` and `source="global_mail"`.

Module state is checked at worker startup and enforced on all relevant API endpoints.

### Module-aware worker behavior

- Disabling `email-imap`: user account watchers stop, accounts stay in DB
- Disabling `email-global`: global watcher stops, sender addresses stay in DB
- Re-enabling restarts the respective watchers

## Frontend Changes

### Accounts page (user-facing)

`/accounts` becomes a tabbed shell (`AccountsView.vue`) with sub-navigation:

- `/accounts/imap` — `AccountsImapView.vue` (existing content extracted)
- `/accounts/forwarding` — `AccountsForwardingView.vue` (new)

Tabs are conditionally rendered based on module state from `GET /api/v1/modules`. Hidden tabs for disabled modules. Default redirect to first enabled module.

If neither module is enabled, show empty state message.

### AccountsForwardingView.vue

- Info box showing the global inbox address to forward to
- List of registered sender addresses with delete
- Add email address form with duplicate error handling

### Admin Settings page

Two new sub-tabs:

- `/admin/settings/email` — `GlobalMailConfigView.vue` (IMAP config for global account)
- `/admin/settings/modules` — `ModulesView.vue` (toggle switches)

### Pinia stores

- `modules.ts` — Fetch module state on app init, `isEnabled(key)` helper
- `senderAddresses.ts` — CRUD for sender addresses

## Migration

Single Alembic migration:
- Create `global_mail_config`, `user_sender_address`, `module_config` tables
- Alter `processed_email`: make `account_id` nullable, add `source` column
- Seed `module_config`: `email-imap` enabled (preserves current behavior), `email-global` disabled

Zero breaking changes on upgrade.
