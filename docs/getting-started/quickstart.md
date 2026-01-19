# Quickstart Tutorial

In this tutorial, you'll build a simple task management API with TinyBase in about 10 minutes.

## What You'll Learn

- Creating collections to store data
- Writing typed functions
- Using the REST API
- Scheduling automated tasks

## Prerequisites

- TinyBase installed ([Installation Guide](installation.md))
- A terminal and text editor
- Basic Python knowledge

## Step 1: Initialize Your Project

Create a new directory and initialize TinyBase:

```bash
mkdir task-api && cd task-api
tinybase init --admin-email admin@example.com --admin-password admin123
```

## Step 2: Start the Server

```bash
tinybase serve
```

Open `http://localhost:8000/admin` and log in with `admin@example.com` / `admin123`.

## Step 3: Create a Collection

Collections are schema-driven tables for your data. Let's create a "tasks" collection.

### Using the Admin UI

1. Go to **Collections** in the sidebar
2. Click **New Collection**
3. Fill in:
   - **Name**: `tasks`
   - **Label**: `Tasks`
4. Add fields:

```json
{
  "fields": [
    {
      "name": "title",
      "type": "string",
      "required": true,
      "max_length": 200
    },
    {
      "name": "description",
      "type": "string",
      "required": false
    },
    {
      "name": "completed",
      "type": "boolean",
      "required": false,
      "default": false
    },
    {
      "name": "due_date",
      "type": "string",
      "required": false
    }
  ]
}
```

### Using the API

Alternatively, create the collection via API:

```bash
curl -X POST http://localhost:8000/api/collections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{
    "name": "tasks",
    "label": "Tasks",
    "schema": {
      "fields": [
        {"name": "title", "type": "string", "required": true},
        {"name": "description", "type": "string"},
        {"name": "completed", "type": "boolean", "default": false},
        {"name": "due_date", "type": "string"}
      ]
    }
  }'
```

## Step 4: Add Records via API

Create some tasks:

```bash
# Create a task
curl -X POST http://localhost:8000/api/collections/tasks/records \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn TinyBase",
    "description": "Complete the quickstart tutorial",
    "due_date": "2024-12-31"
  }'

# Create another task
curl -X POST http://localhost:8000/api/collections/tasks/records \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build an API",
    "description": "Create a REST API with TinyBase"
  }'
```

## Step 5: Query Records

List all tasks:

```bash
curl http://localhost:8000/api/collections/tasks/records
```

Response:

```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "collection_id": "...",
      "data": {
        "title": "Learn TinyBase",
        "description": "Complete the quickstart tutorial",
        "completed": false,
        "due_date": "2024-12-31"
      },
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 100
}
```

## Step 6: Create a Custom Function

Now let's create a function to get task statistics. Create a new function file:

```bash
tinybase functions new task_stats -d "Get task completion statistics"
```

This creates `functions/task_stats.py`. Edit it:

```python title="functions/task_stats.py"
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class TaskStatsInput(BaseModel):
    """Input for task statistics - no parameters needed."""
    pass


class TaskStatsOutput(BaseModel):
    """Task statistics output."""
    total: int
    completed: int
    pending: int
    completion_rate: float


@register(
    name="task_stats",
    description="Get task completion statistics",
    auth="public",
    tags=["tasks"],
)
def task_stats(client, payload: TaskStatsInput) -> TaskStatsOutput:
    """Calculate task statistics from the database."""
    # Query all task records via API
    response = client.get("/api/collections/tasks/records")
    records = response.json().get("items", [])
    
    total = len(records)
    completed = sum(1 for r in records if r.get("data", {}).get("completed", False))
    pending = total - completed
    rate = (completed / total * 100) if total > 0 else 0.0
    
    return TaskStatsOutput(
        total=total,
        completed=completed,
        pending=pending,
        completion_rate=round(rate, 2)
    )


if __name__ == "__main__":
    run()
```

Restart the server (or use `--reload` flag) and call the function:

```bash
curl -X POST http://localhost:8000/api/functions/task_stats \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Step 7: Update a Record

Mark a task as completed:

```bash
curl -X PATCH http://localhost:8000/api/collections/tasks/records/RECORD_ID \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
```

## Step 8: Schedule a Function (Optional)

Let's create a function that sends daily task reminders, and schedule it.

Create a new function:

```bash
tinybase functions new send_task_reminders -d "Send reminders for pending tasks"
```

Edit `functions/send_task_reminders.py`:

```python
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class ReminderInput(BaseModel):
    pass


class ReminderOutput(BaseModel):
    message: str
    pending_count: int


@register(
    name="send_task_reminders",
    description="Send reminders for pending tasks",
    auth="admin",
    tags=["tasks", "notifications"],
)
def send_task_reminders(client, payload: ReminderInput) -> ReminderOutput:
    """Check for pending tasks and 'send' reminders."""
    # In production, this would send emails/notifications
    response = client.get("/api/collections/tasks/records")
    records = response.json().get("items", [])
    pending = sum(1 for r in records if not r.get("data", {}).get("completed", False))
    
    return ReminderOutput(
        message=f"Reminder: You have {pending} pending tasks!",
        pending_count=pending
    )


if __name__ == "__main__":
    run()
```

Create a schedule via the Admin UI or API:

```bash
curl -X POST http://localhost:8000/api/admin/schedules \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "function_name": "send_task_reminders",
    "payload": {},
    "schedule": {
      "method": "cron",
      "timezone": "UTC",
      "cron": "0 9 * * *",
      "description": "Every day at 9 AM"
    },
    "enabled": true
  }'
```

## What's Next?

Congratulations! You've built a functional task API with TinyBase. Here's what to explore next:

<div class="grid cards" markdown>

-   :material-book-open: [**Collections Guide**](../guide/collections.md)

    Learn about schemas, access control, and advanced queries

-   :material-function-variant: [**Functions Guide**](../guide/functions.md)

    Deep dive into typed functions and the Context object

-   :material-clock: [**Scheduling Guide**](../guide/scheduling.md)

    Master cron expressions and interval scheduling

-   :material-rocket: [**Deployment Guide**](../deployment/index.md)

    Deploy your app to production

</div>

## Complete Code

Your `functions/` directory should now contain:

```
functions/
├── __init__.py
├── task_stats.py
└── send_task_reminders.py
```

Both function files follow the SDK format with inline dependency declarations and isolated execution environments.

