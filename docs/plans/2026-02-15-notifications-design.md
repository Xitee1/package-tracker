# Notification System Design

## Overview

Add a notification system that lets users receive alerts about order lifecycle events (new order, tracking update, package delivered) through configurable channels (email, webhooks). Uses a two-layer architecture: core SMTP infrastructure for app-level emails, plus pluggable notifier modules for user-facing notification channels.

## Architecture: Two-Layer Split

### Layer 1: Core SMTP (Infrastructure)

SMTP configuration is a core admin setting, not a module. It lives alongside Queue in the admin settings sidebar.

- `SmtpConfig` singleton model: host, port, username, password (Fernet-encrypted), use_tls, sender_address, sender_name
- `email_service.py` in `app/services/`: provides `send_email(to, subject, html_body)` async function usable by any part of the app
- Admin endpoints: `GET/PUT /api/v1/admin/smtp`, `POST /api/v1/admin/smtp/test`
- Used directly for: email verification (notification module), password resets and account invitations (future)

### Layer 2: Notifier Modules (User-Facing)

New module type `"notifier"` alongside `"analyser"` and `"provider"`.

- Auto-discovered from `app/modules/notifiers/`
- Admin routes: `/api/v1/modules/notifiers/{key}`
- User routes: `/api/v1/notifiers/{key}`
- Each module exports a `send(user_id, event_type, event_data)` async function

## Notification Modules

### Email Notifier (`notify-email`)

- Depends on core SMTP being configured (shows message if not)
- Admin view: enable/disable toggle only
- User view: email input with verification flow, event checkboxes (disabled until verified)
- Module key: `notify-email`

### Webhook Notifier (`notify-webhook`)

- Self-contained, no infrastructure dependency
- Admin view: enable/disable toggle only
- User view: webhook URL input, optional Authorization header (masked), event checkboxes, test button
- Module key: `notify-webhook`

## Notification Events

Enum with three values for now:
- `new_order` — new order detected from email analysis
- `tracking_update` — tracking number or status changed
- `package_delivered` — order marked as delivered

## Data Models

### SmtpConfig (singleton)

| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| host | str | SMTP server hostname |
| port | int | SMTP port |
| username | str | nullable |
| password | str | Fernet-encrypted, nullable |
| use_tls | bool | default True |
| sender_address | str | From address |
| sender_name | str | From display name |

### UserNotificationConfig (per user per module)

| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| user_id | int | FK to User |
| module_key | str | e.g. "notify-email" |
| enabled | bool | user toggle |
| config | JSON | module-specific (email address, webhook URL, auth header) |
| events | JSON | array of subscribed event types |

Unique constraint on (user_id, module_key).

### EmailVerification

| Field | Type | Notes |
|-------|------|-------|
| id | int | PK |
| user_id | int | FK to User |
| email | str | address to verify |
| token | UUID | verification token |
| created_at | datetime | |
| expires_at | datetime | 24h from creation |
| verified_at | datetime | nullable, set on verification |

## Notification Dispatch

### Unified dispatch function

`notify_user(user_id, event_type, event_data)` in `app/services/notification_service.py`:

1. Load all enabled notifier modules from registry
2. For each module, load `UserNotificationConfig` for this user
3. Skip if user hasn't enabled it or hasn't subscribed to this event
4. Call module's `send()` function
5. Log success/failure (application logs, not DB)

### Integration point

Called from `email_processor.py` after order creation or update.

## Email Verification Flow

1. User enters email in notification settings
2. `POST /api/v1/notifiers/notify-email/config` with `{email: "..."}`
3. Backend creates `EmailVerification` record (UUID token, 24h expiry)
4. Sends verification email via core SMTP with link: `{frontend_url}/verify-email/{token}`
5. Frontend route `/verify-email/{token}` calls `POST /api/v1/notifiers/notify-email/verify/{token}`
6. Backend marks verified, stores email in `UserNotificationConfig.config`
7. User can now toggle on and select events

## Frontend

### Core SMTP admin UI

- Route: `/admin/settings/smtp`
- Static entry in admin settings sidebar (alongside Queue, not in module groups)
- `AdminSmtpSettingsView.vue`: SMTP config form + test button

### Sidebar — Notifications section

- New collapsible "Benachrichtigungen" section in `AppLayout.vue`
- Between provider items and admin section
- Only shown if at least one notifier module is enabled and configured
- Items from `moduleRegistry.getUserSidebarItems()` filtered to `type === 'notifier'`

### Notification user views

- Routes under `/notifications/{moduleKey}`
- Secondary sidebar pattern (like admin settings): module list left, config right
- Each module provides its own user view component

### Email notifier user view

- Toggle switch (top), email input + verify button, verification status, event checkboxes
- All event controls disabled until email is verified

### Webhook notifier user view

- Toggle switch (top), URL input, auth header input (masked), event checkboxes, test button

### Admin settings for notifier modules

- Appear under "Notifiers" group in admin settings sidebar (same grouping pattern as Analysers/Providers)

### i18n

- Shared keys: `notifications.*`
- Module keys: `modules.notify-email.*`, `modules.notify-webhook.*`
- Both `en.json` and `de.json`
