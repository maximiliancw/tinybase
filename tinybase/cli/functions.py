"""Functions management CLI commands."""

import re
from pathlib import Path
from typing import Annotated

import typer

from tinybase.config import settings

from .utils import create_function_boilerplate, snake_to_camel

# Create functions subcommand group
functions_app = typer.Typer(
    name="functions",
    help="Function management commands",
)


@functions_app.command("new")
def functions_new(
    name: Annotated[str, typer.Argument(help="Function name (snake_case)")],
    description: Annotated[
        str, typer.Option("--description", help="Function description")
    ] = "TODO: Add description",
    functions_dir: Annotated[
        Path, typer.Option("--dir", help="Functions directory (default: from config)")
    ] = Path("./functions"),
) -> None:
    """
    Create a new function with boilerplate code.

    Creates a new function file in the functions/ package directory.
    """
    # Validate function name
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        typer.echo("Error: Function name must be lowercase with underscores (snake_case)", err=True)
        raise typer.Exit(1)

    # Use config functions_path if available, otherwise use provided dir
    try:
        config = settings()
        functions_dir = Path(config.functions_path)
    except Exception:
        # If config can't be loaded, use provided dir or default
        functions_dir = functions_dir.resolve()

    # Ensure functions directory exists
    if not functions_dir.exists():
        functions_dir.mkdir(parents=True)
        typer.echo(f"Created functions directory: {functions_dir}")

    # Ensure __init__.py exists
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

    # Create function file
    func_file = functions_dir / f"{name}.py"

    if func_file.exists():
        typer.echo(f"Error: Function file already exists: {func_file}", err=True)
        raise typer.Exit(1)

    # Check if function name is already registered (by checking other files)
    for py_file in functions_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            content = py_file.read_text()
            if f'name="{name}"' in content:
                typer.echo(f"Error: Function '{name}' already exists in {py_file.name}", err=True)
                raise typer.Exit(1)
        except Exception:
            pass

    # Generate boilerplate
    camel_name = snake_to_camel(name)
    boilerplate = create_function_boilerplate(name, description)

    func_file.write_text(boilerplate)

    typer.echo(f"Created function '{name}' in {func_file}")
    typer.echo(f"  Edit the {camel_name}Input and {camel_name}Output classes to define your schema")


@functions_app.command("deploy")
def functions_deploy(
    env: Annotated[
        str, typer.Option("--env", "-e", help="Environment name from tinybase.toml")
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
