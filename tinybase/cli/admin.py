"""Admin user management CLI commands."""

from typing import Annotated

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
    from tinybase.db.core import create_db_and_tables, get_engine
    from tinybase.db.models import User

    # Ensure database exists
    create_db_and_tables()

    engine = get_engine()
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
