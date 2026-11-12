from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.ops import IngestionRun

async def start_run(
    db: AsyncSession,
    source: str,
    kind: str,
    details: Optional[Dict[str, Any]] = None
) -> IngestionRun:
    run = IngestionRun(
        source=source,
        kind=kind,
        status="running",
        details=details or {},
    )
    db.add(run)
    await db.flush()
    return run

async def finish_run(
    db: AsyncSession,
    run_id: int,
    status: str,
    rows_fetched: int,
    rows_loaded: int,
    rows_rejected: int,
    error: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    now = datetime.now(timezone.utc)
    values = {
        "status": status,
        "finished_at": now,
        "rows_fetched": rows_fetched,
        "rows_loaded": rows_loaded,
        "rows_rejected": rows_rejected,
    }
    if error is not None:
        values["error"] = error
    if details is not None:
        values["details"] = details
    stmt = update(IngestionRun).where(IngestionRun.id == run_id).values(**values)
    await db.execute(stmt)

async def list_runs(db: AsyncSession, limit: int = 50) -> List[IngestionRun]:
    stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
