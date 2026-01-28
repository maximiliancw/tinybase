"""Extension management CLI commands."""

from typing import Annotated, Optional

import typer

# Create extensions subcommand group
extensions_app = typer.Typer(
    name="extensions",
    help="Extension management commands",
)


@extensions_app.command("install")
def extensions_install(
    url: Annotated[
        str, typer.Argument(help="GitHub repository URL (e.g., https://github.com/user/repo)")
    ],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """
    Install an extension from a GitHub repository.

    Extensions can execute arbitrary Python code. Only install extensions
    from trusted sources.
    """
    from sqlmodel import Session

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.extensions import InstallError, install_extension

    # Security warning
    if not yes:
        typer.echo("")
        typer.echo("⚠️  WARNING: Extensions can execute arbitrary Python code.")
        typer.echo("   Only install extensions from sources you trust.")
        typer.echo("")
        confirm = typer.confirm(f"Install extension from {url}?")
        if not confirm:
            typer.echo("Installation cancelled.")
            raise typer.Exit(0)

    # Ensure database exists
    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        try:
            typer.echo(f"Installing extension from: {url}")
            extension = install_extension(session, url)
            typer.echo("")
            typer.echo(f"✓ Successfully installed: {extension.name} v{extension.version}")
            if extension.description:
                typer.echo(f"  {extension.description}")
            typer.echo("")
            typer.echo("Note: Restart the server to load the extension.")
        except InstallError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)


@extensions_app.command("uninstall")
def extensions_uninstall(
    name: Annotated[str, typer.Argument(help="Extension name to uninstall")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """
    Uninstall an extension.

    Removes the extension files and database record.
    """
    from sqlmodel import Session

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.extensions import uninstall_extension

    if not yes:
        confirm = typer.confirm(f"Uninstall extension '{name}'?")
        if not confirm:
            typer.echo("Uninstallation cancelled.")
            raise typer.Exit(0)

    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        if uninstall_extension(session, name):
            typer.echo(f"✓ Uninstalled extension: {name}")
            typer.echo("")
            typer.echo("Note: Restart the server to fully unload the extension.")
        else:
            typer.echo(f"Error: Extension '{name}' not found.", err=True)
            raise typer.Exit(1)


@extensions_app.command("list")
def extensions_list() -> None:
    """
    List installed extensions.

    Shows all extensions with their status, version, and description.
    """
    from sqlmodel import Session, select

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import Extension

    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        extensions = session.exec(select(Extension)).all()

        if not extensions:
            typer.echo("No extensions installed.")
            typer.echo("")
            typer.echo("Install an extension with:")
            typer.echo("  tinybase extensions install <github-url>")
            return

        typer.echo("")
        typer.echo("Installed Extensions:")
        typer.echo("-" * 60)

        for ext in extensions:
            status = "✓ enabled" if ext.is_enabled else "○ disabled"
            typer.echo(f"\n  {ext.name} v{ext.version}  [{status}]")
            if ext.description:
                typer.echo(f"    {ext.description}")
            if ext.author:
                typer.echo(f"    Author: {ext.author}")
            typer.echo(f"    Source: {ext.repo_url}")

        typer.echo("")


@extensions_app.command("enable")
def extensions_enable(
    name: Annotated[str, typer.Argument(help="Extension name to enable")],
) -> None:
    """
    Enable an extension.

    The extension will be loaded on the next server restart.
    """
    from sqlmodel import Session, select

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import Extension
    from tinybase.utils import utcnow

    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        extension = session.exec(select(Extension).where(Extension.name == name)).first()

        if not extension:
            typer.echo(f"Error: Extension '{name}' not found.", err=True)
            raise typer.Exit(1)

        if extension.is_enabled:
            typer.echo(f"Extension '{name}' is already enabled.")
            return

        extension.is_enabled = True
        extension.updated_at = utcnow()
        session.add(extension)
        session.commit()

        # Log activity
        from tinybase.activity import Actions, log_activity

        log_activity(
            action=Actions.EXTENSION_ENABLE,
            resource_type="extension",
            resource_id=extension.name,
        )

        typer.echo(f"✓ Enabled extension: {name}")
        typer.echo("")
        typer.echo("Note: Restart the server to load the extension.")


@extensions_app.command("disable")
def extensions_disable(
    name: Annotated[str, typer.Argument(help="Extension name to disable")],
) -> None:
    """
    Disable an extension.

    The extension will not be loaded on the next server restart.
    """
    from sqlmodel import Session, select

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import Extension
    from tinybase.utils import utcnow

    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        extension = session.exec(select(Extension).where(Extension.name == name)).first()

        if not extension:
            typer.echo(f"Error: Extension '{name}' not found.", err=True)
            raise typer.Exit(1)

        if not extension.is_enabled:
            typer.echo(f"Extension '{name}' is already disabled.")
            return

        extension.is_enabled = False
        extension.updated_at = utcnow()
        session.add(extension)
        session.commit()

        # Log activity
        from tinybase.activity import Actions, log_activity

        log_activity(
            action=Actions.EXTENSION_DISABLE,
            resource_type="extension",
            resource_id=extension.name,
        )

        typer.echo(f"✓ Disabled extension: {name}")
        typer.echo("")
        typer.echo("Note: Restart the server to fully unload the extension.")


@extensions_app.command("check-updates")
def extensions_check_updates(
    name: Annotated[
        Optional[str], typer.Argument(help="Extension name (omit to check all)")
    ] = None,
) -> None:
    """
    Check for extension updates.

    Compares installed versions with the latest versions from GitHub.
    """
    from sqlmodel import Session, select

    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import Extension
    from tinybase.extensions import check_for_updates

    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        if name:
            extensions = [session.exec(select(Extension).where(Extension.name == name)).first()]
            if not extensions[0]:
                typer.echo(f"Error: Extension '{name}' not found.", err=True)
                raise typer.Exit(1)
        else:
            extensions = list(session.exec(select(Extension)).all())

        if not extensions:
            typer.echo("No extensions installed.")
            return

        typer.echo("Checking for updates...")
        typer.echo("")

        updates_available = False
        for ext in extensions:
            if not ext:
                continue
            result = check_for_updates(session, ext.name)
            if result:
                current, latest = result
                typer.echo(f"  {ext.name}: {current} → {latest} (update available)")
                updates_available = True
            else:
                typer.echo(f"  {ext.name}: {ext.version} (up to date)")

        if updates_available:
            typer.echo("")
            typer.echo("To update an extension, uninstall and reinstall it:")
            typer.echo("  tinybase extensions uninstall <name>")
            typer.echo("  tinybase extensions install <github-url>")
