import uuid
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.errors import BriefNotFound, SymbolNotFound
from bullsutra.db.session import get_db
from bullsutra.db.repositories import securities, briefs
from bullsutra.schemas.common import Page
from bullsutra.schemas.contracts import ResearchBrief
from bullsutra.schemas.research import BriefSummary, BriefSummaryList

router = APIRouter(prefix="/research", tags=["research"])

@router.get("", response_model=Page[BriefSummary])
async def list_latest_briefs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    items, total = await briefs.list_latest_per_security(db, limit=limit, offset=offset)
    summaries = []
    for b in items:
        sec = await securities.get_by_id(db, b.security_id)
        if sec:
            b_data = b.brief
            summaries.append(BriefSummary(
                id=str(b.id),
                symbol=sec.symbol,
                company_name=sec.name,
                as_of=b.as_of,
                label=b.label or "HOLD",
                score=float(b.consensus_score or 0.0),
                confidence=float(b.confidence or 0.0),
                conflicted=bool(b.conflicted) if b.conflicted is not None else False,
                used_llm=bool(b.used_llm),
                generated_at=b.created_at,
            ))
    return Page(items=summaries, total=total, limit=limit, offset=offset)

@router.get("/briefs/{brief_id}", response_model=ResearchBrief)
async def get_brief_by_id(brief_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    b = await briefs.get_brief_by_id(db, brief_id)
    if not b:
        raise BriefNotFound(f"Brief '{brief_id}' not found")
    return ResearchBrief.model_validate(b.brief)

@router.get("/{symbol}", response_model=ResearchBrief)
async def get_research(
    symbol: str,
    as_of: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Symbol '{symbol.upper()}' not found")

    b = await briefs.get_latest_brief(db, security_id=sec.id, as_of=as_of)
    if not b:
        raise BriefNotFound(f"No brief found for '{symbol.upper()}'" + (f" as of {as_of}" if as_of else ""))

    return ResearchBrief.model_validate(b.brief)

@router.get("/{symbol}/history", response_model=Dict[str, List[BriefSummary]])
async def get_research_history(
    symbol: str,
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Symbol '{symbol.upper()}' not found")

    items = await briefs.list_brief_history(db, security_id=sec.id, limit=limit)
    summaries = [
        BriefSummary(
            id=str(b.id),
            symbol=sec.symbol,
            company_name=sec.name,
            as_of=b.as_of,
            label=b.label or "HOLD",
            score=float(b.consensus_score or 0.0),
            confidence=float(b.confidence or 0.0),
            conflicted=bool(b.conflicted) if b.conflicted is not None else False,
            used_llm=bool(b.used_llm),
            generated_at=b.created_at,
        )
        for b in items
    ]
    return {"items": summaries}
