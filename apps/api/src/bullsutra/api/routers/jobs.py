import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.errors import NotFound
from bullsutra.core.security import Principal
from bullsutra.api.deps import require_admin
from bullsutra.db.session import get_db
from bullsutra.db.repositories import jobs
from bullsutra.schemas.common import Page
from bullsutra.schemas.jobs import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("", response_model=Page[JobOut])
async def list_jobs(
    kind: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    job_rows, total = await jobs.list_jobs(db, kind=kind, status=status, limit=limit, offset=offset)
    items = [
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
    return Page(items=items, total=total, limit=limit, offset=offset)

@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: uuid.UUID,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    j = await jobs.get_by_id(db, job_id)
    if not j:
        raise NotFound(f"Job '{job_id}' not found")
    return JobOut(
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
