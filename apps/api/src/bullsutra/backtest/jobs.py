"""Background job for backfilling historical signals."""
from datetime import date
from typing import Dict, Any
from bullsutra.worker.context import JobContext
from bullsutra.agents.constants import LOGIC_VERSION
from bullsutra.db.repositories import securities
from bullsutra.backtest.signal_store import backfill_signals

async def run_signals_backfill(ctx: JobContext) -> Dict[str, Any]:
    """Execute historical signal backfill for the universe."""
    payload = ctx.payload or {}
    start_str = payload.get("start")
    end_str = payload.get("end")
    start = date.fromisoformat(start_str) if start_str else None
    end = date.fromisoformat(end_str) if end_str else None
    logic_v = payload.get("logic_version") or LOGIC_VERSION
    sec_ids = payload.get("security_ids")

    async with ctx.session() as db:
        if not sec_ids:
            universe = await securities.list_universe_asof(db, as_of=end or date.today())
            if not universe:
                universe_all, _ = await securities.search(db, limit=40)
                universe = universe_all
            sec_ids = [s.id for s in universe]

        rows_count = await backfill_signals(
            db=db,
            security_ids=sec_ids,
            start=start,
            end=end,
            logic_version=logic_v,
            ctx=ctx,
        )

    return {"rows": rows_count}
