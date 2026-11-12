import sys
import json
import asyncio
from datetime import date
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from bullsutra.core.security import hash_password
from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories import users, calendar

app = typer.Typer(name="bullsutra", help="BullSutra CLI management tool")
admin_app = typer.Typer(name="admin", help="Admin user & system management")
data_app = typer.Typer(name="data", help="Data pipelines management")
agents_app = typer.Typer(name="agents", help="Agent layer management")
backtest_app = typer.Typer(name="backtest", help="Backtesting management")

app.add_typer(admin_app)
app.add_typer(data_app)
app.add_typer(agents_app)
app.add_typer(backtest_app)

from bullsutra.agents.cli_commands import register_agents_commands
register_agents_commands(agents_app)

from bullsutra.backtest.cli_commands import register_backtest_commands
register_backtest_commands(backtest_app)

console = Console()

@admin_app.command("create-admin")
def create_admin(
    email: str = typer.Option(..., "--email", "-e", help="Admin email address"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Admin password (min 12 chars)")
):
    """Creates a new admin user."""
    if not password:
        password = typer.prompt("Enter admin password", hide_input=True)
        password_confirm = typer.prompt("Confirm admin password", hide_input=True)
        if password != password_confirm:
            console.print("[red]Error: Passwords do not match.[/red]")
            raise typer.Exit(code=1)

    if len(password) < 12:
        console.print("[red]Error: Password must be at least 12 characters long.[/red]")
        raise typer.Exit(code=1)

    async def _run():
        async with async_session_factory() as session:
            existing = await users.get_by_email(session, email)
            if existing:
                console.print(f"[red]Error: User with email '{email}' already exists.[/red]")
                raise typer.Exit(code=1)
            
            p_hash = hash_password(password)
            user = await users.create_user(session, email=email, password_hash=p_hash, role="admin")
            await session.commit()
            console.print(f"[green]Successfully created admin user '{user.email}' (ID: {user.id})[/green]")

    asyncio.run(_run())

@admin_app.command("reset-password")
def reset_password(
    email: str = typer.Option(..., "--email", "-e", help="Admin email address"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="New password (min 12 chars)")
):
    """Resets the password for an existing user."""
    if not password:
        password = typer.prompt("Enter new password", hide_input=True)
        password_confirm = typer.prompt("Confirm new password", hide_input=True)
        if password != password_confirm:
            console.print("[red]Error: Passwords do not match.[/red]")
            raise typer.Exit(code=1)

    if len(password) < 8:
        console.print("[red]Error: Password must be at least 8 characters long.[/red]")
        raise typer.Exit(code=1)

    async def _run():
        async with async_session_factory() as session:
            user = await users.get_by_email(session, email)
            if not user:
                console.print(f"[red]Error: User '{email}' not found.[/red]")
                raise typer.Exit(code=1)

            p_hash = hash_password(password)
            await users.update_password(session, user.id, p_hash)
            await session.commit()
            console.print(f"[green]Successfully reset password for user '{email}'.[/green]")

    asyncio.run(_run())

@admin_app.command("list-users")
def list_users():
    """Lists all registered users."""
    async def _run():
        async with async_session_factory() as session:
            user_list = await users.list_users(session)
            table = Table(title="BullSutra Users")
            table.add_column("ID", style="cyan")
            table.add_column("Email", style="magenta")
            table.add_column("Role", style="green")
            table.add_column("Active", style="yellow")
            table.add_column("Created At")
            table.add_column("Last Login At")

            for u in user_list:
                table.add_row(
                    str(u.id),
                    u.email,
                    u.role,
                    str(u.is_active),
                    str(u.created_at),
                    str(u.last_login_at) if u.last_login_at else "Never"
                )
            console.print(table)

    asyncio.run(_run())

@admin_app.command("calendar-mark")
def calendar_mark(
    date_str: str = typer.Option(..., "--date", help="Date in YYYY-MM-DD format"),
    trading: bool = typer.Option(False, "--trading", help="Mark date as trading session"),
    holiday: bool = typer.Option(False, "--holiday", help="Mark date as non-trading / holiday"),
    note: str = typer.Option("", "--note", help="Calendar note / holiday name")
):
    """Marks a calendar date as trading or holiday in dim_trading_day."""
    if not (trading ^ holiday):
        console.print("[red]Error: Specify exactly one of --trading or --holiday.[/red]")
        raise typer.Exit(code=1)

    d = date.fromisoformat(date_str)
    is_session = trading

    async def _run():
        async with async_session_factory() as session:
            await calendar.upsert_trading_day(session, d, is_session=is_session, note=note)
            await session.commit()
            status_text = "trading session" if is_session else "holiday"
            console.print(f"[green]Successfully marked {d} as {status_text} (note: {note})[/green]")

    asyncio.run(_run())

@data_app.command("build")
def data_build(
    as_of: Optional[str] = typer.Option(None, "--asof", help="Target build date YYYY-MM-DD"),
    full: bool = typer.Option(False, "--full", help="Full clean build"),
):
    """Builds the super dataset using DuckDB."""
    from bullsutra.pipelines.build_super_dataset import main as build_main
    console.print("[blue]Running Super Dataset DuckDB build pipeline...[/blue]")
    build_main()
    console.print("[green]Build completed successfully.[/green]")

@app.command("openapi")
def generate_openapi(
    out: Path = typer.Option(Path("apps/api/openapi.json"), "--out", help="Output file path")
):
    """Generates the OpenAPI JSON schema for client generation."""
    from bullsutra.main import app as fastapi_app
    schema = fastapi_app.openapi()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    console.print(f"[green]Successfully generated OpenAPI schema to {out}[/green]")

if __name__ == "__main__":
    app()
