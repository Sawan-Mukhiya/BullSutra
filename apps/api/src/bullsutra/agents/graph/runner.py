"""Research brief graph runner."""
from datetime import date
from typing import Optional
from bullsutra.worker.context import JobContext
from bullsutra.db.repositories.securities import get_security
from bullsutra.agents.graph.build import GRAPH

async def run_research(
    ctx: JobContext,
    security_id: int,
    as_of: date,
    use_llm: bool = False,
) -> str:
    """Run research graph for a security as of a given date and persist the brief."""
    if hasattr(ctx, "session"):
        async with ctx.session() as db:
            sec = await get_security(db, security_id)
            sym = sec.symbol if sec else f"SEC_{security_id}"
            await ctx.set_progress(0.05)
            initial_state = {
                "security_id": security_id,
                "symbol": sym,
                "as_of": as_of,
                "use_llm": use_llm,
                "signals": {},
                "debate_rounds": [],
            }
            final_state = await GRAPH.ainvoke(
                initial_state,
                config={"configurable": {"ctx": ctx, "db": db}},
            )
            return str(final_state["brief_id"])
    else:
        db = getattr(ctx, "db", None)
        sec = await get_security(db, security_id) if db else None
        sym = sec.symbol if sec else f"SEC_{security_id}"
        await ctx.set_progress(0.05)
        initial_state = {
            "security_id": security_id,
            "symbol": sym,
            "as_of": as_of,
            "use_llm": use_llm,
            "signals": {},
            "debate_rounds": [],
        }
        final_state = await GRAPH.ainvoke(
            initial_state,
            config={"configurable": {"ctx": ctx, "db": db}},
        )
        return str(final_state["brief_id"])
