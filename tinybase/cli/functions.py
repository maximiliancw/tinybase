"""Functions management CLI commands."""

import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from tinybase.settings import config

from .utils import create_function_boilerplate, snake_to_camel

if TYPE_CHECKING:
    from rich.console import Console
    from tinybase_sdk.deployment import DeploymentError, DeploymentResult

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

    # Use config functions_dir if available, otherwise use provided dir
    try:
        functions_dir = Path(config.functions_dir)
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
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Path to function file or directory. If omitted, deploys all functions in configured functions directory."
        ),
    ] = None,
    env: Annotated[
        str, typer.Option("--env", "-e", help="Environment name from tinybase.toml")
    ] = "production",
    notes: Annotated[
        str | None,
        typer.Option("--notes", "-n", help="Deployment notes for version tracking"),
    ] = None,
    batch: Annotated[
        bool,
        typer.Option(
            "--batch",
            "-b",
            help="Use batch upload (faster for multiple functions)",
        ),
    ] = True,
) -> None:
    """
    Deploy function(s) to a TinyBase instance.

    Examples:
        # Deploy single function
        tinybase functions deploy functions/my_func.py

        # Deploy all functions in directory
        tinybase functions deploy functions/

        # Deploy from default functions directory
        tinybase functions deploy

        # Deploy to staging environment
        tinybase functions deploy --env staging

        # Add deployment notes
        tinybase functions deploy --notes "Fixed bug in validation"
    """
    from rich.console import Console

    try:
        from tinybase_sdk.config import ConfigurationError, load_deployment_config
        from tinybase_sdk.deployment import DeploymentClient, DeploymentError
    except ImportError:
        typer.echo("Error: tinybase-sdk not installed", err=True)
        typer.echo("Install it with: pip install tinybase-sdk", err=True)
        raise typer.Exit(1)

    console = Console()

    # Load configuration
    try:
        config = load_deployment_config(env)
    except ConfigurationError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

    # Determine what to deploy
    if path is None:
        # Deploy all functions from configured directory
        path = config.functions_dir

    path = path.resolve()

    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        raise typer.Exit(1)

    # Collect function files
    function_files: list[Path] = []
    if path.is_file():
        if path.suffix == ".py":
            function_files = [path]
        else:
            console.print(f"[red]Error:[/red] Not a Python file: {path}")
            raise typer.Exit(1)
    elif path.is_dir():
        function_files = [f for f in path.glob("*.py") if not f.name.startswith("_")]
        if not function_files:
            console.print(f"[yellow]Warning:[/yellow] No function files found in {path}")
            raise typer.Exit(0)
    else:
        console.print(f"[red]Error:[/red] Invalid path: {path}")
        raise typer.Exit(1)

    console.print(f"[cyan]Deploying to:[/cyan] {config.api_url}")
    console.print(f"[cyan]Environment:[/cyan] {env}")
    console.print(f"[cyan]Functions:[/cyan] {len(function_files)}")
    if notes:
        console.print(f"[cyan]Notes:[/cyan] {notes}")
    console.print()

    # Deploy functions
    with DeploymentClient(config.api_url, config.api_token, config.timeout) as client:
        if len(function_files) == 1 or not batch:
            # Deploy individually
            results = []
            for func_file in function_files:
                console.print(f"Deploying {func_file.name}...", end=" ")
                result = client.deploy_function(func_file, notes)
                results.append(result)

                if isinstance(result, DeploymentError):
                    console.print("[red]✗ Failed[/red]")
                else:
                    status = (
                        "[green]✓ New version[/green]"
                        if result.is_new_version
                        else "[yellow]○ Same version[/yellow]"
                    )
                    console.print(status)

        else:
            # Deploy as batch
            console.print(f"Uploading {len(function_files)} functions as batch...")
            results = client.deploy_batch(function_files, notes)

    # Display results
    console.print()
    _display_deployment_results(console, results)

    # Exit with error if any deployments failed
    if any(isinstance(r, DeploymentError) for r in results):
        raise typer.Exit(1)


def _display_deployment_results(
    console: "Console", results: list["DeploymentResult | DeploymentError"]
) -> None:
    """Display deployment results in a table."""
    from rich.table import Table
    from tinybase_sdk.deployment import DeploymentError, DeploymentResult

    # Separate successes and errors
    successes = [r for r in results if isinstance(r, DeploymentResult)]
    errors = [r for r in results if isinstance(r, DeploymentError)]

    # Display successes
    if successes:
        table = Table(title="[green]Successfully Deployed[/green]")
        table.add_column("Function", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Version ID", style="dim")
        table.add_column("Warnings", style="yellow")

        for result in successes:
            status = "New version" if result.is_new_version else "Same version"
            version_id = result.version_id[:8]  # Show short hash
            warnings = ", ".join(result.warnings) if result.warnings else "-"

            table.add_row(result.function_name, status, version_id, warnings)

        console.print(table)

    # Display errors
    if errors:
        if successes:
            console.print()  # Add spacing

        table = Table(title="[red]Failed Deployments[/red]")
        table.add_column("Function", style="cyan")
        table.add_column("Error", style="red")

        for error in errors:
            table.add_row(error.function_name, error.error)

        console.print(table)

    # Summary
    console.print()
    total = len(results)
    success_count = len(successes)
    error_count = len(errors)

    if error_count == 0:
        console.print(f"[green]✓ All {total} function(s) deployed successfully[/green]")
    else:
        console.print(f"[yellow]⚠ {success_count}/{total} deployed, {error_count} failed[/yellow]")
