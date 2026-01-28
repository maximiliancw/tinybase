---
hide:
  - navigation
  - toc
---

# TinyBase

<div class="hero" markdown>

## A lightweight BaaS for Python developers

TinyBase is a self-hosted Backend-as-a-Service (BaaS) framework that brings the simplicity of PocketBase to the Python ecosystem.

[Get Started](getting-started/index.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/maximiliancw/tinybase){ .md-button }

</div>

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } __Quick Setup__

  ______________________________________________________________________

  Get up and running in minutes with a single command. No complex configuration required.

  ```bash
  pip install tinybase
  tinybase init && tinybase serve
  ```

- :material-database:{ .lg .middle } __SQLite-Backed__

  ______________________________________________________________________

  All your data stored in a single SQLite file. Easy to backup, migrate, and understand.

- :material-api:{ .lg .middle } __FastAPI-Powered__

  ______________________________________________________________________

  Built on FastAPI for high performance and automatic OpenAPI documentation.

- :material-language-python:{ .lg .middle } __Python-First__

  ______________________________________________________________________

  Define server-side functions with Pydantic models. Full type safety and IDE support.

</div>

## Key Features

<div class="grid cards" markdown>

- :material-format-list-bulleted:{ .lg .middle } __Dynamic Collections__

  ______________________________________________________________________

  Create schema-driven collections with JSON schemas. Pydantic models are generated at runtime for validation.

  [:octicons-arrow-right-24: Learn about Collections](guide/collections.md)

- :material-function:{ .lg .middle } __Typed Functions__

  ______________________________________________________________________

  Define server-side functions with strongly-typed inputs and outputs. Exposed as HTTP endpoints with full OpenAPI docs.

  [:octicons-arrow-right-24: Learn about Functions](guide/functions.md)

- :material-clock-outline:{ .lg .middle } __Built-in Scheduling__

  ______________________________________________________________________

  Schedule functions with once, interval, or cron expressions. No external job scheduler needed.

  [:octicons-arrow-right-24: Learn about Scheduling](guide/scheduling.md)

- :material-puzzle:{ .lg .middle } __Extension System__

  ______________________________________________________________________

  Extend TinyBase with community extensions. Hook into lifecycle events, authentication, and data operations.

  [:octicons-arrow-right-24: Learn about Extensions](guide/extensions.md)

- :material-shield-account:{ .lg .middle } __Authentication__

  ______________________________________________________________________

  Built-in user authentication with JWT tokens. Role-based access control with admin and user roles. Includes access and refresh tokens.

  [:octicons-arrow-right-24: Learn about Authentication](guide/authentication.md)

- :material-view-dashboard:{ .lg .middle } __Admin UI__

  ______________________________________________________________________

  Modern admin interface built with Vue 3. Manage collections, users, functions, and schedules.

  [:octicons-arrow-right-24: Learn about Admin UI](guide/admin-ui.md)

</div>

## Quick Example

Define a server-side function in Python:

```python title="functions/greet.py"
# /// script
# dependencies = [
#   "tinybase-sdk",
# ]
# ///

from pydantic import BaseModel
from tinybase_sdk import register
from tinybase_sdk.cli import run


class GreetInput(BaseModel):
    name: str


class GreetOutput(BaseModel):
    message: str


@register(
    name="greet",
    description="Generate a greeting",
    auth="public",
)
def greet(client, payload: GreetInput) -> GreetOutput:
    return GreetOutput(message=f"Hello, {payload.name}!")


if __name__ == "__main__":
    run()
```

Call it via the REST API:

```bash
curl -X POST http://localhost:8000/api/functions/greet \
  -H "Content-Type: application/json" \
  -d '{"name": "World"}'
```

Response:

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "succeeded",
  "result": {
    "message": "Hello, World!"
  }
}
```

## Why TinyBase?

| Feature         | TinyBase | PocketBase | Firebase | Supabase |
| --------------- | -------- | ---------- | -------- | -------- |
| Language        | Python   | Go         | -        | -        |
| Self-hosted     | ✅       | ✅         | ❌       | ✅       |
| SQLite          | ✅       | ✅         | ❌       | ❌       |
| Typed Functions | ✅       | ❌         | ✅       | ✅       |
| Python SDK      | Native   | Community  | Official | Official |
| Scheduling      | ✅       | ❌         | ✅       | ❌       |
| Open Source     | ✅       | ✅         | ❌       | ✅       |

TinyBase is ideal for:

- __Python developers__ who want a simple backend without learning a new language
- __Small to medium projects__ that don't need the complexity of a full cloud platform
- __Prototypes and MVPs__ where development speed matters
- __Self-hosted applications__ where you want full control over your data

## Getting Help

- :fontawesome-brands-github: [GitHub Issues](https://github.com/maximiliancw/tinybase/issues) - Report bugs and request features
- :fontawesome-brands-github: [GitHub Discussions](https://github.com/maximiliancw/tinybase/discussions) - Ask questions and share ideas

## License

TinyBase is released under the [MIT License](https://github.com/maximiliancw/tinybase/blob/main/LICENSE).
