"""Core CLI commands: version, init, serve."""

import os
from pathlib import Path
from typing import Annotated, Optional

import typer

from tinybase.settings import config
from tinybase.version import __version__

from .utils import create_default_toml, get_example_functions

# Create main app
app = typer.Typer(
    name="tinybase",
    help="TinyBase - A lightweight BaaS framework for Python developers",
    add_completion=False,
)


@app.command()
def version() -> None:
    """Show TinyBase version."""
    typer.echo(f"TinyBase v{__version__}")


@app.command()
def init(
    directory: Annotated[
        Path, typer.Argument(help="Directory to initialize (default: current directory)")
    ] = Path("."),
    admin_email: Annotated[
        Optional[str], typer.Option("--admin-email", "-e", help="Admin user email")
    ] = None,
    admin_password: Annotated[
        Optional[str], typer.Option("--admin-password", "-p", help="Admin user password")
    ] = None,
) -> None:
    """
    Initialize a new TinyBase instance.

    Creates configuration files, initializes the database, and optionally
    creates an admin user.
    """
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

    # Create functions directory and example functions if missing
    functions_dir = directory / "functions"
    if not functions_dir.exists():
        functions_dir.mkdir()
        typer.echo("  Created functions/ directory")

    # Create __init__.py if missing
    init_file = functions_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            '"""\n'
            "TinyBase Functions Package\n"
            "\n"
            "User-defined functions should be placed in individual files within this package.\n"
            "Each function file can use uv's single-file script feature to define inline dependencies.\n"
            '"""\n'
        )
        typer.echo("  Created functions/__init__.py")

    # Create example functions if they don't exist
    example_functions = get_example_functions()

    for filename, content in example_functions:
        func_file = functions_dir / filename
        if not func_file.exists():
            func_file.write_text(content)

    if any(not (functions_dir / name).exists() for name, _ in example_functions):
        typer.echo("  Created example functions in functions/ directory")

    # Initialize database
    typer.echo("  Initializing database...")
    from tinybase.db.core import init_db

    init_db()
    typer.echo("  Database initialized")

    # Create admin user if credentials provided
    admin_email = admin_email or os.environ.get("TINYBASE_ADMIN_EMAIL")
    admin_password = admin_password or os.environ.get("TINYBASE_ADMIN_PASSWORD")

    if admin_email and admin_password:
        from sqlmodel import Session, select

        from tinybase.auth import hash_password
        from tinybase.db.core import get_db_engine
        from tinybase.db.models import User

        engine = get_db_engine()
        with Session(engine) as session:
            # Check if admin already exists
            existing = session.exec(select(User).where(User.email == admin_email)).first()

            if existing:
                # Update password and ensure admin flag is set
                existing.password_hash = hash_password(admin_password)
                existing.is_admin = True
                session.add(existing)
                session.commit()
                typer.echo(f"  Updated admin user: {admin_email}")
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
        typer.echo("  Tip: Run 'tinybase admin add <email> <password>' to create an admin user")

    typer.echo("")
    typer.echo("TinyBase initialized successfully!")
    typer.echo("Run 'tinybase serve' to start the server.")


@app.command()
def serve(
    host: Annotated[Optional[str], typer.Option("--host", "-h", help="Host to bind to")] = None,
    port: Annotated[Optional[int], typer.Option("--port", "-p", help="Port to bind to")] = None,
    reload: Annotated[
        bool, typer.Option("--reload", "-r", help="Enable auto-reload for development")
    ] = False,
) -> None:
    """
    Start the TinyBase server.

    Runs the FastAPI application with Uvicorn.
    """
    import uvicorn

    # Validate workspace is initialized
    toml_path = Path.cwd() / "tinybase.toml"
    functions_dir = Path(config.functions_dir)

    if not toml_path.exists():
        typer.secho("Error: Workspace not initialized!", fg=typer.colors.RED, bold=True)
        typer.echo("")
        typer.echo("TinyBase requires a configuration file to run.")
        typer.echo("Please initialize your workspace first:")
        typer.echo("")
        typer.secho("  tinybase init", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        raise typer.Exit(1)

    if not functions_dir.exists():
        typer.secho("Error: Functions directory not found!", fg=typer.colors.RED, bold=True)
        typer.echo("")
        typer.echo(f"Expected functions directory at: {functions_dir.absolute()}")
        typer.echo("Please initialize your workspace first:")
        typer.echo("")
        typer.secho("  tinybase init", fg=typer.colors.GREEN, bold=True)
        typer.echo("")
        raise typer.Exit(1)

    # Use CLI options or fall back to config
    bind_host = host or config.server_host
    bind_port = port or config.server_port

    # Set log level based on environment (debug mode = development)
    uvicorn_log_level = "debug" if config.debug else "warning"

    typer.echo(f"Starting TinyBase server on {bind_host}:{bind_port}")
    typer.echo(f"  API docs: http://{bind_host}:{bind_port}/docs")
    typer.echo(f"  Admin UI: http://{bind_host}:{bind_port}/admin")
    typer.echo(f"  Environment: {'development' if config.debug else 'production'}")
    typer.echo("")

    uvicorn.run(
        "tinybase.api.app:create_app",
        host=bind_host,
        port=bind_port,
        reload=reload,
        factory=True,
        log_level=uvicorn_log_level,
        log_config=None,  # Let our setup_logging() handle all configuration
    )


@app.command()
def templates(
    destination: Annotated[
        Path, typer.Argument(help="Destination directory (default: current directory)")
    ] = Path("."),
) -> None:
    """
    Copy email templates to your workspace for customization.

    This command copies the default email templates to your workspace,
    allowing you to customize them (e.g., change wording or language).
    Templates in your workspace take precedence over the built-in templates.
    """
    import shutil

    source_dir = Path(__file__).parent.parent.parent / "templates" / "emails"
    dest_dir = destination.resolve() / "templates" / "emails"

    if not source_dir.exists():
        typer.secho("Error: Internal templates not found!", fg=typer.colors.RED, bold=True)
        raise typer.Exit(1)

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy all template files
    template_files = list(source_dir.glob("*.tpl"))
    if not template_files:
        typer.secho("Warning: No template files found to copy", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    copied_count = 0
    for template_file in template_files:
        dest_file = dest_dir / template_file.name
        if dest_file.exists():
            typer.echo(f"  Skipping {template_file.name} (already exists)")
        else:
            shutil.copy2(template_file, dest_file)
            typer.echo(f"  Copied {template_file.name}")
            copied_count += 1

    if copied_count > 0:
        typer.echo("")
        typer.secho(
            f"Successfully copied {copied_count} template(s) to {dest_dir}", fg=typer.colors.GREEN
        )
        typer.echo("")
        typer.echo(
            "You can now customize these templates. They will be used instead of the built-in ones."
        )
    else:
        typer.echo("")
        typer.secho("All templates already exist in destination directory", fg=typer.colors.YELLOW)
