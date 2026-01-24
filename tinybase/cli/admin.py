"""Admin user management CLI commands."""

from typing import Annotated, Optional
from uuid import UUID

import typer

# Create admin subcommand group
admin_app = typer.Typer(
    name="admin",
    help="Admin user management commands",
)


@admin_app.command("add")
def admin_add(
    email: Annotated[str, typer.Argument(help="Admin user email address")],
    password: Annotated[str, typer.Argument(help="Admin user password")],
) -> None:
    """
    Add or update an admin user.

    Creates a new admin user with the given email and password.
    If the user already exists, updates their password and grants admin privileges.
    """
    from sqlmodel import Session, select

    from tinybase.auth import hash_password
    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import User

    # Ensure database exists
    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        # Check if user already exists
        existing = session.exec(select(User).where(User.email == email)).first()

        if existing:
            existing.password_hash = hash_password(password)
            existing.is_admin = True
            session.add(existing)
            session.commit()
            typer.echo(f"Updated admin user: {email}")
        else:
            user = User(
                email=email,
                password_hash=hash_password(password),
                is_admin=True,
            )
            session.add(user)
            session.commit()
            typer.echo(f"Created admin user: {email}")


@admin_app.command("token")
def admin_token(
    action: Annotated[
        str,
        typer.Argument(help="Action: 'create', 'list', 'revoke', or 'show'"),
    ],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Token name")] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", "-d", help="Token description")
    ] = None,
    expires_days: Annotated[
        Optional[int],
        typer.Option("--expires-days", "-e", help="Token expiration in days (0 = never)"),
    ] = None,
    token_id: Annotated[
        Optional[str], typer.Option("--id", "-i", help="Token ID (for revoke/show)")
    ] = None,
) -> None:
    """
    Manage application tokens for system-to-system authentication.

    Application tokens are used to authenticate orchestration systems,
    monitoring tools, and other automated services.
    """
    from sqlmodel import Session, select

    from tinybase.auth import create_application_token, revoke_application_token
    from tinybase.db.core import get_db_engine, init_db
    from tinybase.db.models import ApplicationToken
    from tinybase.utils import utcnow

    # Ensure database exists
    init_db()

    engine = get_db_engine()
    with Session(engine) as session:
        if action == "create":
            if not name:
                typer.echo("Error: --name is required for 'create' action", err=True)
                raise typer.Exit(1)

            expires_at = None
            if expires_days is not None:
                if expires_days > 0:
                    from datetime import timedelta

                    expires_at = utcnow() + timedelta(days=expires_days)
                # If expires_days is 0, expires_at stays None (never expires)

            token = create_application_token(session, name, description, expires_at)
            typer.echo(f"Created application token: {token.name}")
            typer.echo(f"  ID: {token.id}")
            typer.echo(f"  Token: {token.token}")
            typer.echo("  ⚠️  Save this token securely - it cannot be retrieved later!")
            if expires_at:
                typer.echo(f"  Expires: {expires_at.isoformat()}")

        elif action == "list":
            tokens = session.exec(
                select(ApplicationToken).order_by(ApplicationToken.created_at.desc())
            ).all()
            if not tokens:
                typer.echo("No application tokens found.")
                return

            typer.echo(f"Found {len(tokens)} application token(s):\n")
            for token in tokens:
                status = "✓ Active" if token.is_valid() else "✗ Inactive/Expired"
                typer.echo(f"  {token.id}")
                typer.echo(f"    Name: {token.name}")
                typer.echo(f"    Status: {status}")
                typer.echo(f"    Created: {token.created_at.isoformat()}")
                if token.last_used_at:
                    typer.echo(f"    Last used: {token.last_used_at.isoformat()}")
                if token.expires_at:
                    typer.echo(f"    Expires: {token.expires_at.isoformat()}")
                if token.description:
                    typer.echo(f"    Description: {token.description}")
                typer.echo("")

        elif action == "revoke":
            if not token_id:
                typer.echo("Error: --id is required for 'revoke' action", err=True)
                raise typer.Exit(1)

            try:
                token_uuid = UUID(token_id)
            except ValueError:
                typer.echo(f"Error: Invalid token ID: {token_id}", err=True)
                raise typer.Exit(1)

            if revoke_application_token(session, token_uuid):
                typer.echo(f"Revoked application token: {token_id}")
            else:
                typer.echo(f"Error: Token not found: {token_id}", err=True)
                raise typer.Exit(1)

        elif action == "show":
            if not token_id:
                typer.echo("Error: --id is required for 'show' action", err=True)
                raise typer.Exit(1)

            try:
                token_uuid = UUID(token_id)
            except ValueError:
                typer.echo(f"Error: Invalid token ID: {token_id}", err=True)
                raise typer.Exit(1)

            token = session.get(ApplicationToken, token_uuid)
            if not token:
                typer.echo(f"Error: Token not found: {token_id}", err=True)
                raise typer.Exit(1)

            status = "✓ Active" if token.is_valid() else "✗ Inactive/Expired"
            typer.echo(f"Application Token: {token.id}")
            typer.echo(f"  Name: {token.name}")
            typer.echo(f"  Status: {status}")
            typer.echo(f"  Created: {token.created_at.isoformat()}")
            if token.last_used_at:
                typer.echo(f"  Last used: {token.last_used_at.isoformat()}")
            if token.expires_at:
                typer.echo(f"  Expires: {token.expires_at.isoformat()}")
            if token.description:
                typer.echo(f"  Description: {token.description}")
            typer.echo("  ⚠️  Token value is not shown for security reasons")

        else:
            typer.echo(f"Error: Unknown action: {action}", err=True)
            typer.echo("Valid actions: create, list, revoke, show")
            raise typer.Exit(1)
