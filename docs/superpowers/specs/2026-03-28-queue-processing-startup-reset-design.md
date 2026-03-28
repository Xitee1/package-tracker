# Queue Processing Startup Reset

## Problem

When the application crashes or restarts while queue items are being processed, those items remain stuck at `"processing"` status indefinitely. No mechanism exists to recover them.

The fix in commit `e804e2d` addressed a related but different issue: error recovery within a running process failing due to expired SQLAlchemy ORM attributes. That fix does not cover hard crashes or restarts.

## Solution

On application startup, reset all queue items with status `"processing"` back to `"queued"` so they are automatically reprocessed.

## Design

### Location

In the `lifespan()` function in `backend/app/main.py`, between the DB seeding block (SMTP config) and the scheduler creation. This placement ensures:

- The database is ready (migrations have run)
- The scheduler/worker has not started yet (no race condition)

### Implementation

A single SQLAlchemy `UPDATE` statement:

```python
async with async_session() as session:
    result = await session.execute(
        update(QueueItem)
        .where(QueueItem.status == "processing")
        .values(status="queued")
    )
    if result.rowcount:
        await session.commit()
        logger.info(f"Reset {result.rowcount} stuck queue item(s) from 'processing' to 'queued'.")
```

### Behavior

- Items reset to `"queued"` will be picked up by the next worker cycle (runs every 5 seconds)
- Only logs when items were actually reset (no noise on clean startups)
- No commit issued if no items were stuck (no unnecessary DB writes)

## What This Does NOT Do

- No new database fields or migrations
- No API changes
- No frontend changes
- No runtime timeout/heartbeat mechanism (YAGNI — the problem is crash recovery, not hanging workers)

## Testing

Add a test that:
1. Creates a queue item with status `"processing"`
2. Calls the reset logic
3. Verifies the item is back to `"queued"`
