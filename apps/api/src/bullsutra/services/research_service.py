from datetime import date, datetime, timedelta, timezone
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from bullsutra.core.errors import SymbolNotFound, NotInUniverse, ValidationError, BriefNotFound
from bullsutra.core.security import Principal
from bullsutra.db.repositories import securities, prices, briefs, jobs
from bullsutra.db.models.agents import ResearchBriefRow
from bullsutra.schemas.agents import RunRequest, RunResponse
from bullsutra.worker.context import JobContext

async def request_run(db: AsyncSession, principal: Principal, req: RunRequest) -> Tuple[int, RunResponse]:
    symbol = req.symbol.strip().upper()
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Symbol '{symbol}' not found")
    
    as_of = req.as_of
    if not as_of:
        as_of = await prices.get_latest_price_date_for_security(db, sec.id)
        if not as_of:
            raise ValidationError("No price data for that date")
    else:
        has_prices = await prices.has_price_on_date(db, sec.id, as_of)
        if not has_prices:
            raise ValidationError("No price data for that date")
            
    # Check 6-hour cache unless force is requested
    if not req.force:
        six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
        stmt = select(ResearchBriefRow).where(
            ResearchBriefRow.security_id == sec.id,
            ResearchBriefRow.as_of == as_of,
            ResearchBriefRow.used_llm == req.use_llm,
            ResearchBriefRow.created_at >= six_hours_ago
        ).order_by(ResearchBriefRow.created_at.desc()).limit(1)
        res = await db.execute(stmt)
        cached = res.scalar_one_or_none()
        if cached:
            return 200, RunResponse(
                status="cached",
                brief_id=str(cached.id),
                job_id=str(cached.job_id) if cached.job_id else None,
                events_url=None
            )
            
    # Enqueue job
    job = await jobs.enqueue(
        db,
        kind="research",
        payload={
            "symbol": symbol,
            "as_of": as_of.isoformat(),
            "use_llm": req.use_llm
        },
        created_by=principal.id
    )
    await db.commit()
    return 202, RunResponse(
        status="queued",
        job_id=str(job.id),
        brief_id=None,
        events_url=f"/api/v1/agents/runs/{job.id}/events"
    )

async def run_research_job(ctx: JobContext) -> dict:
    from bullsutra.agents.graph.runner import run_research
    from bullsutra.db.repositories.securities import get_security_by_symbol

    payload = ctx.payload
    sym = payload["symbol"]
    as_of = date.fromisoformat(payload["as_of"]) if isinstance(payload["as_of"], str) else payload["as_of"]
    use_llm = bool(payload.get("use_llm", False))

    async with ctx.session() as db:
        sec = await get_security_by_symbol(db, sym)
        if not sec:
            raise ValueError(f"Security '{sym}' not found")
        sec_id = sec.id

    brief_id = await run_research(ctx, sec_id, as_of, use_llm=use_llm)
    return {"brief_id": brief_id}
