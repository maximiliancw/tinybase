"""
TinyBase CLI application.

Provides commands for:
- init: Initialize a new TinyBase instance
- serve: Start the TinyBase server
- functions new: Create a new function boilerplate
- functions deploy: Deploy functions to a remote server
- admin add: Create or update an admin user
- extensions install/uninstall/list/enable/disable: Manage extensions
"""

from .admin import admin_app
from .db import db_app
from .extensions import extensions_app
from .functions import functions_app
from .main import app

# Register subcommand groups
app.add_typer(functions_app, name="functions")
app.add_typer(db_app, name="db")
app.add_typer(admin_app, name="admin")
app.add_typer(extensions_app, name="extensions")


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
