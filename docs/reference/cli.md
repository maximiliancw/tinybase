# CLI Reference

Complete reference for TinyBase command-line interface.

## Overview

```bash
tinybase [OPTIONS] COMMAND [ARGS]
```

## Global Options

| Option   | Description       |
| -------- | ----------------- |
| `--help` | Show help message |

## Commands

### version

Show TinyBase version.

```bash
tinybase version
```

**Output:**

```
TinyBase v0.3.0
```

______________________________________________________________________

### init

Initialize a new TinyBase instance.

```bash
tinybase init [DIRECTORY] [OPTIONS]
```

**Arguments:**

| Argument    | Description             | Default       |
| ----------- | ----------------------- | ------------- |
| `DIRECTORY` | Directory to initialize | `.` (current) |

**Options:**

| Option                 | Description         |
| ---------------------- | ------------------- |
| `--admin-email, -e`    | Admin user email    |
| `--admin-password, -p` | Admin user password |

**Examples:**

```bash
# Initialize in current directory
tinybase init

# Initialize with admin user
tinybase init --admin-email admin@example.com --admin-password secret123

# Initialize in specific directory
tinybase init ./my-app
```

**Creates:**

- `tinybase.toml` - Configuration file
- `tinybase.db` - SQLite database
- `functions/` - Functions directory (each function in its own file)
  - `__init__.py` - Package marker

______________________________________________________________________

### serve

Start the TinyBase server.

```bash
tinybase serve [OPTIONS]
```

**Options:**

| Option         | Description        | Default     |
| -------------- | ------------------ | ----------- |
| `--host, -h`   | Host to bind to    | From config |
| `--port, -p`   | Port to bind to    | From config |
| `--reload, -r` | Enable auto-reload | `false`     |

**Examples:**

```bash
# Start with defaults
tinybase serve

# Start with custom host/port
tinybase serve --host 127.0.0.1 --port 3000

# Start with auto-reload (development)
tinybase serve --reload
```

______________________________________________________________________

## functions

Function management commands.

### functions new

Create a new function with boilerplate.

```bash
tinybase functions new NAME [OPTIONS]
```

**Arguments:**

| Argument | Description                |
| -------- | -------------------------- |
| `NAME`   | Function name (snake_case) |

**Options:**

| Option              | Description          | Default                 |
| ------------------- | -------------------- | ----------------------- |
| `--description, -d` | Function description | `TODO: Add description` |

**Examples:**

```bash
# Create basic function
tinybase functions new send_email

# Create with description
tinybase functions new calculate_tax -d "Calculate tax for an order"

# Add to different file
tinybase functions new my_func -f ./functions/utils.py
```

### functions deploy

Deploy functions to a remote server.

```bash
tinybase functions deploy [OPTIONS]
```

**Options:**

| Option      | Description      | Default      |
| ----------- | ---------------- | ------------ |
| `--env, -e` | Environment name | `production` |

!!! note
Remote deployment is not yet fully implemented.

______________________________________________________________________

## db

Database management commands.

### db migrate

Generate a new migration.

```bash
tinybase db migrate [OPTIONS]
```

**Options:**

| Option          | Description       | Default          |
| --------------- | ----------------- | ---------------- |
| `--message, -m` | Migration message | `auto migration` |

**Example:**

```bash
tinybase db migrate -m "add user preferences"
```

### db upgrade

Apply pending migrations.

```bash
tinybase db upgrade [REVISION]
```

**Arguments:**

| Argument   | Description     | Default |
| ---------- | --------------- | ------- |
| `REVISION` | Target revision | `head`  |

**Examples:**

```bash
# Upgrade to latest
tinybase db upgrade

# Upgrade to specific revision
tinybase db upgrade abc123
```

### db downgrade

Revert migrations.

```bash
tinybase db downgrade [REVISION]
```

**Arguments:**

| Argument   | Description     | Default |
| ---------- | --------------- | ------- |
| `REVISION` | Target revision | `-1`    |

**Examples:**

```bash
# Downgrade one revision
tinybase db downgrade

# Downgrade to specific revision
tinybase db downgrade abc123
```

### db history

Show migration history.

```bash
tinybase db history
```

### db current

Show current database revision.

```bash
tinybase db current
```

______________________________________________________________________

## admin

Admin user management commands.

### admin add

Create or update an admin user.

```bash
tinybase admin add EMAIL PASSWORD
```

**Arguments:**

| Argument   | Description         |
| ---------- | ------------------- |
| `EMAIL`    | Admin email address |
| `PASSWORD` | Admin password      |

**Examples:**

```bash
# Create new admin
tinybase admin add admin@example.com secretpassword

# Update existing user to admin
tinybase admin add user@example.com newpassword
```

______________________________________________________________________

## extensions

Extension management commands.

### extensions install

Install an extension from GitHub.

```bash
tinybase extensions install URL [OPTIONS]
```

**Arguments:**

| Argument | Description           |
| -------- | --------------------- |
| `URL`    | GitHub repository URL |

**Options:**

| Option      | Description       |
| ----------- | ----------------- |
| `--yes, -y` | Skip confirmation |

**Examples:**

```bash
# Install with confirmation
tinybase extensions install https://github.com/user/tinybase-extension

# Install without confirmation
tinybase extensions install https://github.com/user/tinybase-extension -y
```

### extensions uninstall

Uninstall an extension.

```bash
tinybase extensions uninstall NAME [OPTIONS]
```

**Options:**

| Option      | Description       |
| ----------- | ----------------- |
| `--yes, -y` | Skip confirmation |

**Example:**

```bash
tinybase extensions uninstall my-extension
```

### extensions list

List installed extensions.

```bash
tinybase extensions list
```

**Output:**

```
Installed Extensions:
------------------------------------------------------------

  my-extension v1.0.0  [✓ enabled]
    My awesome extension
    Author: John Doe
    Source: https://github.com/user/my-extension
```

### extensions enable

Enable an extension.

```bash
tinybase extensions enable NAME
```

### extensions disable

Disable an extension.

```bash
tinybase extensions disable NAME
```

### extensions check-updates

Check for extension updates.

```bash
tinybase extensions check-updates [NAME]
```

**Arguments:**

| Argument | Description                                  |
| -------- | -------------------------------------------- |
| `NAME`   | Extension name (optional, omit to check all) |

______________________________________________________________________

## Environment Variables

The CLI respects these environment variables:

| Variable                  | Description                     |
| ------------------------- | ------------------------------- |
| `TINYBASE_ADMIN_EMAIL`    | Default admin email for init    |
| `TINYBASE_ADMIN_PASSWORD` | Default admin password for init |
| `TINYBASE_SERVER_HOST`    | Server bind host                |
| `TINYBASE_SERVER_PORT`    | Server bind port                |
| `TINYBASE_DB_URL`         | Database connection URL         |

**Example:**

```bash
export TINYBASE_ADMIN_EMAIL=admin@example.com
export TINYBASE_ADMIN_PASSWORD=secret
tinybase init  # Uses env vars for admin creation
```

## Exit Codes

| Code | Meaning           |
| ---- | ----------------- |
| `0`  | Success           |
| `1`  | General error     |
| `2`  | Invalid arguments |

## Shell Completion

Generate shell completions:

```bash
# Bash
tinybase --install-completion bash

# Zsh
tinybase --install-completion zsh

# Fish
tinybase --install-completion fish
```

## See Also

- [Configuration Guide](../getting-started/configuration.md)
- [REST API Reference](rest-api.md)
- [Python API Reference](python-api.md)
