"""
TinyBase CLI application.

Provides commands for:
- init: Initialize a new TinyBase instance
- serve: Start the TinyBase server
- functions new: Create a new function boilerplate
- functions deploy: Deploy functions to a remote server
"""

import re
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from tinybase.version import __version__

# Create CLI app
app = typer.Typer(
    name="tinybase",
    help="TinyBase - A lightweight BaaS framework for Python developers",
    add_completion=False,
)

# Create functions subcommand group
functions_app = typer.Typer(
    name="functions",
    help="Function management commands",
)
app.add_typer(functions_app, name="functions")


# =============================================================================
# Helper Functions
# =============================================================================


def snake_to_camel(name: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in name.split("_"))


def create_default_toml() -> str:
    """Generate default tinybase.toml content."""
    return '''# TinyBase Configuration
# See documentation for all available options

[server]
host = "0.0.0.0"
port = 8000
debug = false
log_level = "info"

[database]
url = "sqlite:///./tinybase.db"

[auth]
token_ttl_hours = 24

[functions]
path = "./functions"
file = "./functions.py"

[scheduler]
enabled = true
interval_seconds = 5

[cors]
allow_origins = ["*"]

[admin]
static_dir = "builtin"

# Environment-specific settings for deployment
# [environments.production]
# url = "https://tinybase.example.com"
# api_token = "your-admin-token"
'''


def create_example_function() -> str:
    """Generate example functions.py content."""
    return '''"""
TinyBase Functions

Define your server-side functions here. Functions are registered using
the @register decorator and automatically exposed as HTTP endpoints.
"""

from pydantic import BaseModel
from tinybase.functions import Context, register


# =============================================================================
# Example Function: Add Numbers
# =============================================================================


class AddInput(BaseModel):
    """Input model for add_numbers function."""
    x: int
    y: int


class AddOutput(BaseModel):
    """Output model for add_numbers function."""
    sum: int


@register(
    name="add_numbers",
    description="Add two numbers together",
    auth="public",  # Available without authentication
    input_model=AddInput,
    output_model=AddOutput,
    tags=["math", "example"],
)
def add_numbers(ctx: Context, payload: AddInput) -> AddOutput:
    """
    Add two numbers and return the sum.
    
    This is an example function showing how to:
    - Define input/output models with Pydantic
    - Use the @register decorator
    - Access the Context object
    """
    return AddOutput(sum=payload.x + payload.y)


# =============================================================================
# Example Function: Hello World
# =============================================================================


class HelloInput(BaseModel):
    """Input model for hello function."""
    name: str = "World"


class HelloOutput(BaseModel):
    """Output model for hello function."""
    message: str
    user_id: str | None = None


@register(
    name="hello",
    description="Say hello to someone",
    auth="auth",  # Requires authentication
    input_model=HelloInput,
    output_model=HelloOutput,
    tags=["example"],
)
def hello(ctx: Context, payload: HelloInput) -> HelloOutput:
    """
    Return a greeting message.
    
    Demonstrates accessing user information from the context.
    """
    return HelloOutput(
        message=f"Hello, {payload.name}!",
        user_id=str(ctx.user_id) if ctx.user_id else None,
    )
'''


def create_function_boilerplate(name: str, description: str) -> str:
    """Generate boilerplate code for a new function."""
    camel_name = snake_to_camel(name)
    
    return f'''

# =============================================================================
# Function: {name}
# =============================================================================


class {camel_name}Input(BaseModel):
    """Input model for {name} function."""
    # TODO: Define input fields
    pass


class {camel_name}Output(BaseModel):
    """Output model for {name} function."""
    # TODO: Define output fields
    pass


@register(
    name="{name}",
    description="{description}",
    auth="auth",
    input_model={camel_name}Input,
    output_model={camel_name}Output,
    tags=[],
)
def {name}(ctx: Context, payload: {camel_name}Input) -> {camel_name}Output:
    """
    {description}
    
    TODO: Implement function logic
    """
    return {camel_name}Output()
'''


# =============================================================================
# Commands
# =============================================================================


@app.command()
def version() -> None:
    """Show TinyBase version."""
    typer.echo(f"TinyBase v{__version__}")


@app.command()
def init(
    directory: Annotated[
        Path,
        typer.Argument(help="Directory to initialize (default: current directory)")
    ] = Path("."),
    admin_email: Annotated[
        Optional[str],
        typer.Option("--admin-email", "-e", help="Admin user email")
    ] = None,
    admin_password: Annotated[
        Optional[str],
        typer.Option("--admin-password", "-p", help="Admin user password")
    ] = None,
) -> None:
    """
    Initialize a new TinyBase instance.
    
    Creates configuration files, initializes the database, and optionally
    creates an admin user.
    """
    import os
    
    # Ensure directory exists
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    os.chdir(directory)
    
    typer.echo(f"Initializing TinyBase in {directory}")
    
    # Create tinybase.toml if missing
    toml_path = directory / "tinybase.toml"
    if not toml_path.exists():
        toml_path.write_text(create_default_toml())
        typer.echo("  Created tinybase.toml")
    else:
        typer.echo("  tinybase.toml already exists")
    
    # Create functions.py if missing
    functions_path = directory / "functions.py"
    if not functions_path.exists():
        functions_path.write_text(create_example_function())
        typer.echo("  Created functions.py with example functions")
    else:
        typer.echo("  functions.py already exists")
    
    # Create functions directory if missing
    functions_dir = directory / "functions"
    if not functions_dir.exists():
        functions_dir.mkdir()
        typer.echo("  Created functions/ directory")
    
    # Initialize database
    typer.echo("  Initializing database...")
    from tinybase.db.core import create_db_and_tables
    create_db_and_tables()
    typer.echo("  Database initialized")
    
    # Create admin user if credentials provided
    admin_email = admin_email or os.environ.get("TINYBASE_ADMIN_EMAIL")
    admin_password = admin_password or os.environ.get("TINYBASE_ADMIN_PASSWORD")
    
    if admin_email and admin_password:
        from sqlmodel import Session, select
        from tinybase.auth import hash_password
        from tinybase.db.core import get_engine
        from tinybase.db.models import User
        
        engine = get_engine()
        with Session(engine) as session:
            # Check if admin already exists
            existing = session.exec(
                select(User).where(User.email == admin_email)
            ).first()
            
            if existing:
                typer.echo(f"  Admin user {admin_email} already exists")
            else:
                user = User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    is_admin=True,
                )
                session.add(user)
                session.commit()
                typer.echo(f"  Created admin user: {admin_email}")
    else:
        typer.echo("  Tip: Use --admin-email and --admin-password to create an admin user")
    
    typer.echo("")
    typer.echo("TinyBase initialized successfully!")
    typer.echo("Run 'tinybase serve' to start the server.")


@app.command()
def serve(
    host: Annotated[
        Optional[str],
        typer.Option("--host", "-h", help="Host to bind to")
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option("--port", "-p", help="Port to bind to")
    ] = None,
    reload: Annotated[
        bool,
        typer.Option("--reload", "-r", help="Enable auto-reload for development")
    ] = False,
) -> None:
    """
    Start the TinyBase server.
    
    Runs the FastAPI application with Uvicorn.
    """
    import uvicorn
    
    from tinybase.config import settings
    
    config = settings()
    
    # Use CLI options or fall back to config
    bind_host = host or config.server_host
    bind_port = port or config.server_port
    
    typer.echo(f"Starting TinyBase server on {bind_host}:{bind_port}")
    typer.echo(f"  API docs: http://{bind_host}:{bind_port}/docs")
    typer.echo(f"  Admin UI: http://{bind_host}:{bind_port}/admin")
    typer.echo("")
    
    uvicorn.run(
        "tinybase.api.app:create_app",
        host=bind_host,
        port=bind_port,
        reload=reload,
        factory=True,
        log_level=config.log_level,
    )


@functions_app.command("new")
def functions_new(
    name: Annotated[
        str,
        typer.Argument(help="Function name (snake_case)")
    ],
    description: Annotated[
        str,
        typer.Option("--description", "-d", help="Function description")
    ] = "TODO: Add description",
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Functions file to add to")
    ] = Path("./functions.py"),
) -> None:
    """
    Create a new function with boilerplate code.
    
    Appends a new function template to the specified functions file.
    """
    # Validate function name
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        typer.echo(
            "Error: Function name must be lowercase with underscores (snake_case)",
            err=True
        )
        raise typer.Exit(1)
    
    # Check if file exists
    if not file.exists():
        typer.echo(f"Error: Functions file not found: {file}", err=True)
        typer.echo("Run 'tinybase init' first or specify a different file with --file")
        raise typer.Exit(1)
    
    # Check if function already exists
    content = file.read_text()
    if f'name="{name}"' in content:
        typer.echo(f"Error: Function '{name}' already exists in {file}", err=True)
        raise typer.Exit(1)
    
    # Append boilerplate
    boilerplate = create_function_boilerplate(name, description)
    
    with open(file, "a") as f:
        f.write(boilerplate)
    
    typer.echo(f"Created function '{name}' in {file}")
    typer.echo(f"  Edit the {snake_to_camel(name)}Input and {snake_to_camel(name)}Output classes to define your schema")


@functions_app.command("deploy")
def functions_deploy(
    env: Annotated[
        str,
        typer.Option("--env", "-e", help="Environment name from tinybase.toml")
    ] = "production",
) -> None:
    """
    Deploy functions to a remote TinyBase server.
    
    Reads environment configuration from tinybase.toml and uploads
    the function code to the specified server.
    """
    # This is a placeholder for the deploy functionality
    # In a full implementation, this would:
    # 1. Read environment config from tinybase.toml
    # 2. Package the function files
    # 3. Upload to the remote server
    
    typer.echo(f"Deploying functions to environment: {env}")
    typer.echo("")
    typer.echo("Note: Remote deployment is not yet implemented.")
    typer.echo("For now, deploy your functions manually by copying them to the server.")
    raise typer.Exit(1)


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()

