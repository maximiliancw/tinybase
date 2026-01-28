# Getting Started

Welcome to TinyBase! This guide will help you get up and running with TinyBase in just a few minutes.

## What is TinyBase?

TinyBase is a lightweight, self-hosted Backend-as-a-Service (BaaS) framework designed specifically for Python developers. Think of it as PocketBase, but written in Python and designed to integrate seamlessly with your Python applications.

## Core Concepts

Before diving in, here are the key concepts you'll work with:

<div class="grid cards" markdown>

- :material-database-outline: **Collections**

  Schema-driven data tables stored in SQLite. Define fields, types, and validation rules using JSON schemas.

- :material-function: **Functions**

  Server-side Python functions with typed inputs and outputs. Automatically exposed as REST endpoints.

- :material-clock-outline: **Schedules**

  Run functions automatically using once, interval, or cron expressions.

- :material-account-key: **Authentication**

  Built-in user management with token-based authentication and role-based access control.

</div>

## Prerequisites

- **Python 3.11+** - TinyBase requires Python 3.11 or later
- **pip or uv** - For installing packages

!!! tip "Recommended: Use uv"
We recommend using [uv](https://github.com/astral-sh/uv) for faster dependency management:

````
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
````

## Quick Installation

=== "pip"

````
```bash
pip install tinybase
```
````

=== "uv"

````
```bash
uv add tinybase
```
````

## Your First TinyBase App

### 1. Initialize your project

```bash
mkdir my-app && cd my-app
tinybase init
```

This creates:

- `tinybase.toml` - Configuration file
- `tinybase.db` - SQLite database
- `functions.py` - Example functions file
- `functions/` - Directory for additional function modules

### 2. Start the server

```bash
tinybase serve
```

Your TinyBase server is now running at:

- **API**: `http://localhost:8000`
- **OpenAPI Docs**: `http://localhost:8000/docs`
- **Admin UI**: `http://localhost:8000/admin`

### 3. Create an admin user

```bash
tinybase admin add admin@example.com yourpassword
```

### 4. Access the Admin UI

Open `http://localhost:8000/admin` in your browser and log in with your admin credentials.

## Next Steps

<div class="grid cards" markdown>

- :material-download: [**Installation Guide**](installation.md)

  Detailed installation instructions for different environments

- :material-play: [**Quickstart Tutorial**](quickstart.md)

  Build your first TinyBase application step by step

- :material-cog: [**Configuration**](configuration.md)

  Learn how to configure TinyBase for your needs

</div>

## Getting Help

If you run into issues:

1. Check the [Troubleshooting](../guide/index.md#troubleshooting) section
1. Search [GitHub Issues](https://github.com/maximiliancw/tinybase/issues)
1. Ask in [GitHub Discussions](https://github.com/maximiliancw/tinybase/discussions)
