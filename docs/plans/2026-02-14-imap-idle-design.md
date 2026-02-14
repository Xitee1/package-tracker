# IMAP IDLE & Polling Redesign

## Problem

The current IMAP worker does not implement true persistent IDLE. Each cycle it reconnects, does a full UID search, attempts IDLE for `polling_interval_sec` (default 120s), then disconnects and repeats. This means:

- Every 2 minutes: full reconnect + UID search, even for IDLE-capable servers
- No IDLE capability detection — just tries and catches errors
- No user control over IDLE vs polling
- `polling_interval_sec` serves double duty as IDLE timeout and polling interval
- System stats show "scans" even for accounts that should be push-based

## Design

### Approach

Dual-mode worker with persistent connections (Approach 1 from brainstorming). Rewrite `_watch_folder()` with two distinct inner loops:

- **`_idle_loop()`**: persistent connection, re-issues IDLE every 24 minutes per RFC 2177 best practices, reacts to server push notifications
- **`_poll_loop()`**: disconnect, sleep `polling_interval_sec`, reconnect, UID search, repeat

An outer reconnection loop wraps both for error recovery with exponential backoff.

### Data Model Changes

**`EmailAccount` — add two columns:**

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `use_polling` | `bool` | `False` | User preference. `False` = use IDLE, `True` = force polling |
| `idle_supported` | `bool \| None` | `None` | Detected capability. `None` = not yet checked. Updated by worker on every connect |

**Constraints:**
- When worker detects `idle_supported = False`, also sets `use_polling = True`
- API rejects PATCH `use_polling: false` when `idle_supported: false` (400 error)

**Default change:** `polling_interval_sec` default from `120` to `300` (5 minutes).

No changes to `WatchedFolder` — IDLE vs polling is per-account (same server capabilities for all folders).

### IMAP Worker Rewrite

```
while True:  # reconnection loop — runs on startup, then only on connection loss
    connect + login
    check CAPABILITY for IDLE → update idle_supported in DB
    if not supported and use_polling is False → force use_polling = True
    select folder → UIDVALIDITY check
    initial UID search → process new emails → enqueue

    if IDLE mode:
        _idle_loop(imap, folder)
        # Inner loop (runs indefinitely):
        #   enter IDLE (timeout=24min)
        #   wait_server_push()
        #     EXISTS → idle_done → UID search → process → re-enter IDLE
        #     STOP_WAIT_SERVER_PUSH (timeout) → idle_done → re-enter IDLE
        #     connection error → return (triggers reconnect)

    else:  # polling mode
        _poll_loop(account, folder)
        # Inner loop (runs indefinitely):
        #   disconnect → sleep polling_interval_sec
        #   reconnect → UID search → process
        #   connection error → return (triggers reconnect)

    # Connection lost — backoff and reconnect
    exponential backoff: 30s → 60s → 120s → 300s (capped)
```

**Helper functions extracted:**
- `_connect_and_select()` — connection setup + capability check + DB update
- `_fetch_new_emails()` — UID search + process + enqueue
- `_idle_loop()` — persistent IDLE wait/react cycle
- `_poll_loop()` — disconnect/sleep/reconnect cycle

**WorkerState updates:**
- IDLE path: `mode = IDLE`, no `next_scan_at`, `last_activity_at` updates on each 24-min re-issue
- Polling path: `mode = POLLING`, `next_scan_at` set after each cycle

### IDLE Capability Detection

Check `CAPABILITY` response after login for `IDLE` string. Done on every worker connect (not just account creation) to handle:
- Provider adds/removes IDLE support
- Account migrated to different server

Also check during test connection endpoint for immediate UI feedback.

### Frontend Changes

**Account form (AccountsView.vue):**
- Add "Use polling" toggle switch below polling interval field
- `idle_supported === false`: toggle forced ON, disabled, tooltip explaining IDLE not supported
- `idle_supported === null`: toggle shows preference, disabled, tooltip "Will be detected on first connection"
- `idle_supported === true`: toggle interactive, defaults to OFF

**Account card display — mode badge:**
- `use_polling === false && idle_supported === true`: green "IDLE" badge
- `use_polling === true`: blue "Polling" badge
- `idle_supported === null`: gray "Detecting..." badge

**Watched folder warning:**
- When account has 10+ watched folders, show inline warning about provider connection limits

**System dashboard (SystemView.vue):**
- No changes needed — existing mode display now accurately reflects true IDLE vs polling

### API Changes

**`POST /api/v1/accounts/{id}/test` response** — add `idle_supported: bool` field

**`PATCH /api/v1/accounts/{id}` validation** — reject `use_polling: false` when `idle_supported: false` with 400

**Schemas:**
- `CreateAccountRequest`: add `use_polling: bool = False`, change `polling_interval_sec` default to `300`
- `UpdateAccountRequest`: add `use_polling: Optional[bool] = None`
- `AccountResponse`: add `use_polling: bool`, `idle_supported: Optional[bool]`

### Migration

Alembic migration adding:
- `use_polling` (bool, default False) to `email_accounts`
- `idle_supported` (bool, nullable, default None) to `email_accounts`
- Change `polling_interval_sec` column default from 120 to 300

### i18n Keys

```
accounts.usePolling             — "Use polling"
accounts.usePollingTooltip      — "Force periodic scanning instead of push notifications"
accounts.idleNotSupported       — "This email provider does not support push notifications (IMAP IDLE)"
accounts.idleDetecting          — "Will be detected on first connection"
accounts.folderLimitWarning     — "Watching many folders requires one connection per folder. Some providers limit concurrent connections."
accounts.idleNotSupportedReject — "This email provider does not support IMAP IDLE"
accounts.modeIdle               — "IDLE"
accounts.modePolling            — "Polling"
accounts.modeDetecting          — "Detecting..."
```

## References

- RFC 2177: IMAP4 IDLE Command — 29-minute re-issue recommendation
- K-9 Mail: 24-minute re-IDLE cycle (proven in production)
- aioimaplib: `idle_start()`, `wait_server_push()`, `STOP_WAIT_SERVER_PUSH`, `idle_done()`
- Provider connection limits: Gmail 15/account, Exchange ~8/mailbox, Yahoo ~5/IP, Dovecot 10/user+IP (default)
