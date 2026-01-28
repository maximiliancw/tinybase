#!/usr/bin/env python3
"""TinyBase monorepo management CLI."""
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(help="TinyBase monorepo management")
version_app = typer.Typer(help="Version management")
app.add_typer(version_app, name="version")

ROOT = Path(__file__).parent.parent


@version_app.command("bump")
def version_bump(
    part: str = typer.Argument(..., help="Version part: major, minor, or patch"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change"),
):
    """Bump version across all packages."""
    typer.echo(f"Bumping {part} version (dry_run={dry_run})")
    # TODO: Implement version bumping across pyproject.toml files
    typer.echo("Version bumping not yet implemented")


@app.command()
def release(
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip actual publish"),
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip test suite"),
):
    """Run full release pipeline: test, build, publish."""
    typer.echo(f"Release pipeline (dry_run={dry_run}, skip_tests={skip_tests})")
    # TODO: Implement release workflow
    typer.echo("Release workflow not yet implemented")


@app.command("build-admin")
def build_admin(
    skip_install: bool = typer.Option(False, "--skip-install", help="Skip yarn install"),
):
    """Build admin UI and copy to backend static folder."""
    admin_dir = ROOT / "apps" / "admin"
    static_dir = ROOT / "packages" / "tinybase" / "tinybase" / "static" / "app"

    if not skip_install:
        typer.echo("Installing dependencies...")
        subprocess.run(["yarn", "install"], cwd=admin_dir, check=True)

    typer.echo("Building admin UI...")
    subprocess.run(["yarn", "build"], cwd=admin_dir, check=True)

    typer.echo("Copying to static folder...")
    if static_dir.exists():
        shutil.rmtree(static_dir)
    shutil.copytree(admin_dir / "dist", static_dir)

    typer.echo(f"Built and copied to {static_dir}")


@app.command("export-openapi")
def export_openapi(
    check: bool = typer.Option(False, "--check", help="Check if spec is up to date"),
):
    """Export OpenAPI spec from FastAPI app."""
    script = ROOT / "scripts" / "export_openapi.py"
    cmd = ["python", str(script)]
    if check:
        cmd.append("--check")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    app()
