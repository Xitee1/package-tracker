# Refactor Log

## Iteration 1 — 2026-03-28

**Issue:** IDLE mode re-fetches all emails on every notification due to stale `ctx.last_seen_uid`
**Severity:** fragility
**Location:** `backend/app/modules/_shared/email/imap_watch_loop.py`, `fetch_new_emails()` (lines 145, 170)

**Problem:** The `fetch_new_emails` function persists the last processed UID to the database via `callbacks.save_uid(uid, db)` but never updates the in-memory `ctx.last_seen_uid`. In IDLE mode, the same `FetchContext` object is reused across notification cycles (passed from `watch_loop` → `idle_loop` → `fetch_new_emails`). This means the IMAP UID search (`UID {last_seen_uid + 1}:*`) always starts from the original position, causing every previously-processed email to be re-fetched from the IMAP server and re-checked against the dedup table on each IDLE notification. The overhead grows linearly with the number of emails received during an IDLE session. Polling mode is unaffected because it creates a fresh `FetchContext` from the database each cycle.

**Fix:** Added `ctx.last_seen_uid = uid` after each `callbacks.save_uid(uid, db)` call (both the route-skipped path on line 145 and the normal processing path on line 170). This keeps the in-memory context in sync with what was persisted, so subsequent IDLE cycles only fetch genuinely new emails.

**Verification:** All 222 existing tests pass. Added 3 new tests in `tests/test_fetch_new_emails.py` covering: (1) ctx updates after processing emails, (2) ctx updates when emails are skipped by routing, (3) ctx unchanged when no new emails. Full suite: 225 passed.

**Risk:** None identified. The `FetchContext` is a non-frozen dataclass, mutation is safe. The `ctx` is only used within the `fetch_new_emails` → `idle_loop` call chain. Polling mode already creates fresh contexts and is unaffected.
