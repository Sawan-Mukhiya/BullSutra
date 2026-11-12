import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from bullsutra.core.errors import ValidationError
from bullsutra.core.security import Principal
from bullsutra.api.deps import require_admin
from bullsutra.db.session import get_db
from bullsutra.db.models.securities import ReferenceSymbol
from bullsutra.db.models.prices import DailyBar
from bullsutra.db.models.news import NewsArticle
from bullsutra.db.models.agents import ResearchBriefRow
from bullsutra.db.models.backtests import BacktestRun
from bullsutra.db.models.jobs import Job
from bullsutra.db.repositories import jobs
from bullsutra.schemas.jobs import JobOut

router = APIRouter(prefix="/admin", tags=["admin"])

ALLOWED_PIPELINES = {
    "eod_prices",
    "news_scrape",
    "news_score",
    "signals_daily",
    "weights_update"
}

class PipelineRunRequest(BaseModel):
    date: Optional[str] = None

class AdminStatsResponse(BaseModel):
    counts: Dict[str, int]
    latest_jobs: List[JobOut]

@router.post("/pipelines/{name}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_pipeline(
    name: str,
    body: Optional[PipelineRunRequest] = None,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    if name not in ALLOWED_PIPELINES:
        raise ValidationError(f"Invalid pipeline '{name}'. Allowed: {sorted(ALLOWED_PIPELINES)}")

    payload = {}
    if body and body.date:
        payload["date"] = body.date

    job = await jobs.enqueue(db, kind=name, payload=payload, created_by=p.id)
    await db.commit()
    return {"job_id": str(job.id)}

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    sec_count = (await db.execute(select(func.count(ReferenceSymbol.id)))).scalar() or 0
    univ_count = (await db.execute(select(func.count(ReferenceSymbol.id)).where(ReferenceSymbol.in_universe.is_(True)))).scalar() or 0
    price_count = (await db.execute(select(func.count(DailyBar.security_id)))).scalar() or 0
    news_count = (await db.execute(select(func.count(NewsArticle.id)))).scalar() or 0
    brief_count = (await db.execute(select(func.count(ResearchBriefRow.id)))).scalar() or 0
    bt_count = (await db.execute(select(func.count(BacktestRun.id)))).scalar() or 0

    job_stmt = select(Job).order_by(Job.created_at.desc()).limit(10)
    job_res = await db.execute(job_stmt)
    job_rows = job_res.scalars().all()
    latest_jobs = [
        JobOut(
            id=str(j.id),
            kind=j.kind,
            status=j.status,
            progress=float(j.progress),
            payload=j.payload or {},
            result=j.result,
            error=j.error,
            created_at=j.created_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in job_rows
    ]

    return AdminStatsResponse(
        counts={
            "securities": sec_count,
            "universe": univ_count,
            "prices": price_count,
            "news": news_count,
            "briefs": brief_count,
            "backtests": bt_count,
        },
        latest_jobs=latest_jobs
    )
