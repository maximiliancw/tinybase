# Scheduling

TinyBase includes a built-in scheduler for running functions automatically. Schedule one-time tasks, recurring jobs, or complex cron-based schedules.

## Overview

The scheduler:

- Runs as a **background process** within TinyBase
- Supports **once**, **interval**, and **cron** schedules
- Creates **FunctionCall records** for each execution
- Handles **timezones** correctly
- Provides **Admin UI** for management

## Schedule Types

### Once Schedule

Run a function at a specific date and time:

```json
{
  "method": "once",
  "timezone": "Europe/Berlin",
  "date": "2024-12-25",
  "time": "09:00:00"
}
```

| Field | Description |
|-------|-------------|
| `method` | `"once"` |
| `timezone` | IANA timezone name |
| `date` | Date in `YYYY-MM-DD` format |
| `time` | Time in `HH:MM:SS` format |

### Interval Schedule

Run a function at regular intervals:

```json
{
  "method": "interval",
  "timezone": "UTC",
  "unit": "hours",
  "value": 1
}
```

| Field | Description |
|-------|-------------|
| `method` | `"interval"` |
| `timezone` | IANA timezone name |
| `unit` | `"seconds"`, `"minutes"`, `"hours"`, or `"days"` |
| `value` | Number of units between runs |

### Cron Schedule

Run a function using cron expressions:

```json
{
  "method": "cron",
  "timezone": "America/New_York",
  "cron": "0 9 * * 1-5",
  "description": "Weekdays at 9 AM"
}
```

| Field | Description |
|-------|-------------|
| `method` | `"cron"` |
| `timezone` | IANA timezone name |
| `cron` | Standard cron expression |
| `description` | Optional human-readable description |

## Cron Expression Reference

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday = 0)
│ │ │ │ │
* * * * *
```

### Common Patterns

| Pattern | Description |
|---------|-------------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour |
| `0 0 * * *` | Daily at midnight |
| `0 9 * * *` | Daily at 9 AM |
| `0 9 * * 1` | Every Monday at 9 AM |
| `0 9 * * 1-5` | Weekdays at 9 AM |
| `0 0 1 * *` | First of every month |
| `0 0 1 1 *` | January 1st |
| `*/5 * * * *` | Every 5 minutes |
| `0 */2 * * *` | Every 2 hours |

## Creating Schedules

### Via Admin UI

1. Go to **Schedules** in the sidebar
2. Click **New Schedule**
3. Select a function
4. Configure the schedule
5. Enable and save

### Via API

```bash
# Create an interval schedule
curl -X POST http://localhost:8000/api/admin/schedules \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "cleanup_old_records",
    "payload": {"days": 30},
    "schedule": {
      "method": "interval",
      "timezone": "UTC",
      "unit": "hours",
      "value": 24
    },
    "enabled": true
  }'
```

```bash
# Create a cron schedule
curl -X POST http://localhost:8000/api/admin/schedules \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "send_daily_report",
    "payload": {},
    "schedule": {
      "method": "cron",
      "timezone": "America/New_York",
      "cron": "0 8 * * 1-5",
      "description": "Weekday mornings at 8 AM ET"
    },
    "enabled": true
  }'
```

## Managing Schedules

### List Schedules

```bash
curl http://localhost:8000/api/admin/schedules \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Get Schedule Details

```bash
curl http://localhost:8000/api/admin/schedules/$SCHEDULE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Update Schedule

```bash
curl -X PATCH http://localhost:8000/api/admin/schedules/$SCHEDULE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'
```

### Delete Schedule

```bash
curl -X DELETE http://localhost:8000/api/admin/schedules/$SCHEDULE_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Schedule Structure

A schedule record contains:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "function_name": "my_function",
  "payload": {"key": "value"},
  "schedule": {
    "method": "cron",
    "timezone": "UTC",
    "cron": "0 * * * *"
  },
  "enabled": true,
  "last_run_at": "2024-01-01T12:00:00Z",
  "next_run_at": "2024-01-01T13:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

## Writing Schedulable Functions

Functions that will be scheduled should:

1. **Accept empty payloads** or have defaults
2. **Be idempotent** when possible
3. **Handle errors gracefully**
4. **Log progress** for debugging

```python
from pydantic import BaseModel
from tinybase.functions import Context, register
import logging

logger = logging.getLogger(__name__)


class CleanupInput(BaseModel):
    """Input for cleanup function."""
    days: int = 30  # Default: clean records older than 30 days


class CleanupOutput(BaseModel):
    """Cleanup result."""
    deleted_count: int
    errors: list[str]


@register(
    name="cleanup_old_records",
    description="Delete records older than specified days",
    auth="admin",
    input_model=CleanupInput,
    output_model=CleanupOutput,
    tags=["maintenance", "scheduled"],
)
def cleanup_old_records(ctx: Context, payload: CleanupInput) -> CleanupOutput:
    """
    Clean up old records from the database.
    
    This function is designed to run on a schedule.
    """
    from datetime import timedelta
    from sqlmodel import select
    from tinybase.db.models import Record
    
    cutoff = ctx.now - timedelta(days=payload.days)
    logger.info(f"Cleaning records older than {cutoff}")
    
    # Find old records
    old_records = ctx.db.exec(
        select(Record).where(Record.created_at < cutoff)
    ).all()
    
    deleted = 0
    errors = []
    
    for record in old_records:
        try:
            ctx.db.delete(record)
            deleted += 1
        except Exception as e:
            errors.append(f"Failed to delete {record.id}: {e}")
            logger.error(f"Cleanup error: {e}")
    
    ctx.db.commit()
    logger.info(f"Cleaned up {deleted} records")
    
    return CleanupOutput(deleted_count=deleted, errors=errors)
```

## Checking Scheduled Functions

### Detect Schedule Trigger

```python
@register(name="my_task", ...)
def my_task(ctx: Context, payload: Input) -> Output:
    if ctx.trigger_type == "schedule":
        # Running from scheduler
        logger.info(f"Scheduled run, trigger: {ctx.trigger_id}")
    else:
        # Manual invocation
        logger.info(f"Manual run by user: {ctx.user_id}")
    
    # ... rest of function
```

### Use Different Logic

```python
@register(name="send_report", ...)
def send_report(ctx: Context, payload: ReportInput) -> ReportOutput:
    if ctx.trigger_type == "schedule":
        # Scheduled: send to all subscribers
        recipients = get_all_subscribers()
    else:
        # Manual: send only to requesting user
        recipients = [get_user_email(ctx.user_id)]
    
    send_email(recipients, generate_report())
    return ReportOutput(sent_to=len(recipients))
```

## Scheduler Configuration

Configure the scheduler in `tinybase.toml`:

```toml
[scheduler]
enabled = true           # Enable/disable scheduler
interval_seconds = 5     # How often to check for due tasks
token_cleanup_interval = 60  # Token cleanup interval in scheduler ticks
```

**Token Cleanup Interval**: Controls how often expired authentication tokens are cleaned up. The value is in scheduler ticks - for example, with `interval_seconds = 5` and `token_cleanup_interval = 60`, cleanup runs every 5 minutes (60 × 5s). This can also be configured via the Admin UI Settings page.

### Disabling the Scheduler

For workers that shouldn't run schedules:

```toml
[scheduler]
enabled = false
```

Or via environment variable:

```bash
TINYBASE_SCHEDULER_ENABLED=false tinybase serve
```

## Monitoring Scheduled Tasks

### View Execution History

In the Admin UI, go to **Function Calls** and filter by:

- Function name
- Trigger type: "schedule"
- Status: "succeeded" or "failed"

### API Query

```bash
# Get recent scheduled executions
curl "http://localhost:8000/api/admin/function-calls?trigger_type=schedule&limit=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Timezone Handling

TinyBase uses IANA timezone names (e.g., `America/New_York`, `Europe/London`).

### Common Timezones

| Zone | Description |
|------|-------------|
| `UTC` | Coordinated Universal Time |
| `America/New_York` | US Eastern |
| `America/Los_Angeles` | US Pacific |
| `Europe/London` | UK |
| `Europe/Berlin` | Central Europe |
| `Asia/Tokyo` | Japan |
| `Australia/Sydney` | Australia Eastern |

### Daylight Saving Time

Cron schedules automatically handle DST transitions. A schedule for "9 AM" will run at 9 AM local time regardless of DST.

## Best Practices

### 1. Use Appropriate Intervals

```python
# Too frequent - may overload system
{"method": "interval", "unit": "seconds", "value": 1}

# Better - reasonable interval
{"method": "interval", "unit": "minutes", "value": 5}
```

### 2. Make Functions Idempotent

```python
@register(name="sync_data", ...)
def sync_data(ctx: Context, payload: Input) -> Output:
    # Check if already synced (idempotent)
    last_sync = get_last_sync_time()
    if last_sync and (ctx.now - last_sync).seconds < 300:
        return Output(synced=0, message="Recently synced")
    
    # Perform sync...
```

### 3. Handle Long-Running Tasks

```python
@register(name="process_batch", ...)
def process_batch(ctx: Context, payload: BatchInput) -> BatchOutput:
    processed = 0
    batch_size = 100
    
    while True:
        items = get_unprocessed_items(limit=batch_size)
        if not items:
            break
        
        for item in items:
            process_item(item)
            processed += 1
        
        # Commit progress periodically
        ctx.db.commit()
    
    return BatchOutput(processed=processed)
```

### 4. Add Alerting for Failures

```python
@register(name="critical_task", ...)
def critical_task(ctx: Context, payload: Input) -> Output:
    try:
        result = do_critical_work()
        return Output(success=True, result=result)
    except Exception as e:
        # Alert on failure
        send_alert(f"Critical task failed: {e}")
        raise
```

## See Also

- [Functions Guide](functions.md) - Writing functions
- [Extensions Guide](extensions.md) - Hook into scheduled executions
- [CLI Reference](../reference/cli.md) - Scheduler commands

