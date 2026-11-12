"""CLI commands for backtesting operations."""
import asyncio
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Optional, Dict, Any
import typer
import yaml
from rich.console import Console
from rich.table import Table
from sqlalchemy import select

from bullsutra.db.session import async_session_factory
from bullsutra.db.models.backtests import BacktestRun
from bullsutra.db.repositories import securities, calendar, backtests
from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.signal_store import backfill_signals
from bullsutra.backtest.runner import run_backtest
from bullsutra.backtest.report import export_report

console = Console()

class ConsoleJobContext:
    def __init__(self, session_factory, payload: Optional[Dict[str, Any]] = None):
        self.job_id = uuid.uuid4()
        self.kind = "cli_backtest"
        self.payload = payload or {}
        self.session_factory = session_factory

    def session(self):
        return self.session_factory()

    async def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        console.print(f"[dim][EVENT][/dim] {event_type} {data or ''}")

    async def set_progress(self, value: float, phase: Optional[str] = None) -> None:
        console.print(f"[cyan][PROGRESS][/cyan] {value:.0%} {phase or ''}")

def register_backtest_commands(app: typer.Typer) -> None:
    @app.command("backfill-signals")
    def backfill_cmd(
        start: Optional[str] = typer.Option(None, "--start", help="Start date YYYY-MM-DD"),
        end: Optional[str] = typer.Option(None, "--end", help="End date YYYY-MM-DD"),
    ):
        """Precompute and store deterministic historical signals for universe."""
        d_start = date.fromisoformat(start) if start else None
        d_end = date.fromisoformat(end) if end else None

        async def _run():
            ctx = ConsoleJobContext(async_session_factory)
            async with async_session_factory() as session:
                latest = await calendar.get_latest_trading_day(session)
                as_of = d_end or (latest.trade_date if latest else date.today())
                universe = await securities.list_universe_asof(session, as_of)
                if not universe:
                    universe_all, _ = await securities.search(session, limit=40)
                    universe = universe_all
                sec_ids = [s.id for s in universe]

            console.print(f"[blue]Starting signal store backfill for {len(sec_ids)} universe securities...[/blue]")
            async with async_session_factory() as session:
                count = await backfill_signals(session, sec_ids, d_start, d_end, ctx=ctx)
            console.print(f"[green]Successfully backfilled {count} signal rows.[/green]")

        asyncio.run(_run())

    @app.command("run")
    def run_cmd(
        name: str = typer.Option(..., "--name", "-n", help="Backtest run name"),
        config_path: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to config YAML"),
    ):
        """Execute a complete backtest run in-process."""
        cfg_dict: Dict[str, Any] = {}
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg_dict = yaml.safe_load(f)

        config_obj = BacktestConfig(**cfg_dict)

        async def _run():
            async with async_session_factory() as session:
                run_row = await backtests.create_run(session, {
                    "name": name,
                    "config": config_obj.model_dump(mode="json"),
                    "status": "queued",
                    "created_by": "cli",
                })
                await session.commit()
                run_id = run_row.id

            console.print(f"[blue]Launching backtest '{name}' (ID: {run_id})...[/blue]")
            ctx = ConsoleJobContext(async_session_factory)
            summary = await run_backtest(ctx, run_id)
            console.print(f"[green]Backtest completed! Summary:\n{json.dumps(summary, indent=2)}[/green]")

        asyncio.run(_run())

    @app.command("list")
    def list_cmd():
        """List past backtest runs and summary stats."""
        async def _run():
            async with async_session_factory() as session:
                stmt = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(20)
                runs = (await session.execute(stmt)).scalars().all()

                table = Table(title="BullSutra Backtest Runs")
                table.add_column("Run ID", style="cyan")
                table.add_column("Name", style="bold")
                table.add_column("Status")
                table.add_column("Created At")
                table.add_column("Full Sharpe")
                table.add_column("Full CAGR")

                for r in runs:
                    summ = r.summary or {}
                    full_m = summ.get("full", {})
                    table.add_row(
                        str(r.id)[:8] + "...",
                        r.name,
                        r.status,
                        str(r.created_at)[:19],
                        f"{full_m.get('sharpe', 'N/A')}",
                        f"{full_m.get('cagr', 'N/A')}",
                    )
                console.print(table)

        asyncio.run(_run())

    @app.command("export-report")
    def export_report_cmd(
        backtest_id: str = typer.Option(..., "--id", help="UUID of backtest run"),
        out: Optional[Path] = typer.Option(None, "--out", help="Output export directory"),
    ):
        """Export comprehensive report tables and plots for a run."""
        b_id = uuid.UUID(backtest_id)
        out_dir = out or (Path("data/exports") / f"report_{b_id}")

        async def _run():
            async with async_session_factory() as session:
                res_path = await export_report(session, b_id, out_dir)
            console.print(f"[green]Report exported successfully to: {res_path}[/green]")

        asyncio.run(_run())
