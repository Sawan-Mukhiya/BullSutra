"""CLI commands for agent research and operations."""
import asyncio
import json
import uuid
from datetime import date
from typing import Optional, Dict, Any
import typer
from rich.console import Console

from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories.securities import get_security_by_symbol, list_universe_asof
from bullsutra.db.repositories.calendar import get_latest_trading_day
from bullsutra.db.repositories.briefs import get_brief_by_id
from bullsutra.agents.graph.runner import run_research
from bullsutra.agents.jobs import run_signals_daily, run_weights_update

console = Console()

class ConsoleJobContext:
    """Minimal JobContext that outputs events and progress to stdout."""
    def __init__(self, session_factory, payload: Optional[Dict[str, Any]] = None):
        self.job_id = uuid.uuid4()
        self.kind = "cli_run"
        self.payload = payload or {}
        self.session_factory = session_factory

    def session(self):
        return self.session_factory()

    async def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        console.print(f"[dim][EVENT][/dim] {event_type} {data or ''}")

    async def set_progress(self, value: float, phase: Optional[str] = None) -> None:
        console.print(f"[cyan][PROGRESS][/cyan] {value:.0%} {phase or ''}")

def register_agents_commands(app: typer.Typer) -> None:
    @app.command("run")
    def run_command(
        symbol: str = typer.Option(..., "--symbol", "-s", help="Security symbol e.g. NABIL"),
        as_of_str: Optional[str] = typer.Option(None, "--as-of", help="Target date YYYY-MM-DD"),
        no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM narrative generation"),
    ):
        """Run research graph for a symbol in-process and print the brief JSON."""
        async def _run():
            async with async_session_factory() as session:
                sec = await get_security_by_symbol(session, symbol)
                if not sec:
                    console.print(f"[red]Error: Security '{symbol}' not found.[/red]")
                    raise typer.Exit(code=1)
                sec_id = sec.id

                if as_of_str:
                    as_of = date.fromisoformat(as_of_str)
                else:
                    latest = await get_latest_trading_day(session)
                    as_of = latest.trade_date if latest else date.today()

            ctx = ConsoleJobContext(async_session_factory)
            console.print(f"[blue]Running research on {symbol} as of {as_of} (LLM: {not no_llm})...[/blue]")
            brief_id_str = await run_research(ctx, sec_id, as_of, use_llm=(not no_llm))
            
            async with async_session_factory() as session:
                brief_row = await get_brief_by_id(session, uuid.UUID(brief_id_str))
                if brief_row:
                    console.print(json.dumps(brief_row.brief, indent=2))
                else:
                    console.print(f"[green]Brief created with id {brief_id_str}[/green]")

        asyncio.run(_run())

    @app.command("seed-briefs")
    def seed_briefs(
        no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM generation"),
    ):
        """Run research sequentially for every universe security at the latest date."""
        async def _run():
            async with async_session_factory() as session:
                latest = await get_latest_trading_day(session)
                as_of = latest.trade_date if latest else date.today()
                universe = await list_universe_asof(session, as_of)

            console.print(f"[blue]Seeding briefs for {len(universe)} securities as of {as_of}...[/blue]")
            for idx, sec in enumerate(universe):
                console.print(f"[{idx+1}/{len(universe)}] Running {sec.symbol}...")
                ctx = ConsoleJobContext(async_session_factory)
                try:
                    await run_research(ctx, sec.id, as_of, use_llm=(not no_llm))
                except Exception as e:
                    console.print(f"[red]Failed for {sec.symbol}: {e}[/red]")
            console.print("[green]Seeding completed.[/green]")

        asyncio.run(_run())

    @app.command("signals-daily")
    def signals_daily(
        date_str: Optional[str] = typer.Option(None, "--date", help="Target date YYYY-MM-DD"),
    ):
        """Run daily signals job."""
        async def _run():
            ctx = ConsoleJobContext(async_session_factory, payload={"date": date_str} if date_str else {})
            res = await run_signals_daily(ctx)
            console.print(f"[green]Signals daily complete: {res}[/green]")

        asyncio.run(_run())

    @app.command("weights-update")
    def weights_update():
        """Run outcomes, weights, and calibration update job."""
        async def _run():
            ctx = ConsoleJobContext(async_session_factory)
            res = await run_weights_update(ctx)
            console.print(f"[green]Weights update complete: {res}[/green]")

        asyncio.run(_run())
