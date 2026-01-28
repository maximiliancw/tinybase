"""
Example CLI implementation for TinyBase SDK.

This module demonstrates how to build a CLI using the SDK's deployment functionality.
The actual TinyBase CLI (installed with the `tinybase` package) uses these same
functions to implement `tinybase functions deploy`.

Note: This is NOT registered as a CLI entrypoint. It's provided as an example
and for potential standalone use cases.
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from tinybase_sdk.config import ConfigurationError, load_deployment_config
from tinybase_sdk.deployment import DeploymentClient, DeploymentError, DeploymentResult

app = typer.Typer(
    name="tinybase",
    help="TinyBase SDK - Deploy and manage serverless functions",
    no_args_is_help=True,
)

console = Console()


@app.command("deploy")
def deploy(
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
        tinybase deploy functions/my_func.py

        # Deploy all functions in directory
        tinybase deploy functions/

        # Deploy from default functions directory
        tinybase deploy

        # Deploy to staging environment
        tinybase deploy --env staging

        # Add deployment notes
        tinybase deploy --notes "Fixed bug in validation"
    """
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
    _display_results(results)

    # Exit with error if any deployments failed
    if any(isinstance(r, DeploymentError) for r in results):
        raise typer.Exit(1)


@app.command("list-versions")
def list_versions(
    function_name: Annotated[str, typer.Argument(help="Function name")],
    env: Annotated[
        str, typer.Option("--env", "-e", help="Environment name from tinybase.toml")
    ] = "production",
    limit: Annotated[
        int, typer.Option("--limit", "-l", help="Maximum number of versions to show")
    ] = 10,
) -> None:
    """
    List deployed versions of a function.

    Example:
        tinybase list-versions my_function
        tinybase list-versions my_function --limit 20
    """
    # Load configuration
    try:
        config = load_deployment_config(env)
    except ConfigurationError as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)

    # Get versions
    with DeploymentClient(config.api_url, config.api_token, config.timeout) as client:
        versions = client.list_versions(function_name, limit)

    if versions is None:
        console.print(f"[red]Error:[/red] Failed to retrieve versions for '{function_name}'")
        raise typer.Exit(1)

    if not versions:
        console.print(f"[yellow]No versions found for function '{function_name}'[/yellow]")
        raise typer.Exit(0)

    # Display versions table
    table = Table(title=f"Versions for '{function_name}'")
    table.add_column("Deployed At", style="cyan")
    table.add_column("Hash", style="dim")
    table.add_column("Size", justify="right")
    table.add_column("Executions", justify="right")
    table.add_column("Notes", style="dim")

    for version in versions:
        deployed_at = version["deployed_at"][:19].replace("T", " ")  # Format datetime
        content_hash = version["content_hash"][:8]  # Short hash
        file_size = f"{version['file_size']:,} B"
        exec_count = str(version.get("execution_count", 0))
        notes = version.get("notes", "")[:50] or "-"  # Truncate notes

        table.add_row(deployed_at, content_hash, file_size, exec_count, notes)

    console.print(table)


def _display_results(results: list[DeploymentResult | DeploymentError]) -> None:
    """Display deployment results in a table."""
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


def main():
    """Entry point for the tinybase CLI."""
    app()
