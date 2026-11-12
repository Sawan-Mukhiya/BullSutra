import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, update, func, and_, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.jobs import Job, JobEvent

async def enqueue(
    db: AsyncSession,
    kind: str,
    payload: Dict[str, Any],
    created_by: Optional[str] = None
) -> Job:
    job = Job(
        id=uuid.uuid4(),
        kind=kind,
        payload=payload,
        status="queued",
        created_by=created_by,
        attempts=0,
    )
    db.add(job)
    await db.flush()
    return job

async def enqueue_if_absent(
    db: AsyncSession,
    kind: str,
    payload: Dict[str, Any],
    created_by: Optional[str] = None
) -> Optional[Job]:
    """Inserts a job unless one with the same kind and payload is already queued or running."""
    # Check existing
    stmt = select(Job).where(
        Job.kind == kind,
        Job.status.in_(["queued", "running"]),
        Job.payload == payload
    ).limit(1)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()
    if existing:
        return None
    return await enqueue(db, kind, payload, created_by)

async def get_by_id(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_jobs(
    db: AsyncSession,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Job], int]:
    stmt = select(Job)
    count_stmt = select(func.count(Job.id))
    
    conds = []
    if kind:
        conds.append(Job.kind == kind)
    if status:
        conds.append(Job.status == status)
        
    if conds:
        stmt = stmt.where(and_(*conds))
        count_stmt = count_stmt.where(and_(*conds))
        
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Job.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(stmt)
    return list(res.scalars().all()), total

async def claim_next(db: AsyncSession) -> Optional[Job]:
    """
    Claims the next queued job using PostgreSQL SELECT ... FOR UPDATE SKIP LOCKED.
    Safe against concurrent worker processes.
    """
    stmt = select(Job).where(
        Job.status == "queued"
    ).order_by(
        Job.created_at.asc()
    ).with_for_update(skip_locked=True).limit(1)

    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if job:
        now = datetime.now(timezone.utc)
        job.status = "running"
        job.started_at = now
        job.heartbeat_at = now
        job.attempts += 1
        await db.flush()
    return job

async def heartbeat(db: AsyncSession, job_id: uuid.UUID) -> None:
    stmt = update(Job).where(Job.id == job_id).values(heartbeat_at=datetime.now(timezone.utc))
    await db.execute(stmt)

async def set_progress(db: AsyncSession, job_id: uuid.UUID, progress: float) -> None:
    stmt = update(Job).where(Job.id == job_id).values(progress=progress)
    await db.execute(stmt)

async def append_event(
    db: AsyncSession,
    job_id: uuid.UUID,
    event_type: str,
    node: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> int:
    max_seq_stmt = select(func.coalesce(func.max(JobEvent.seq), 0)).where(JobEvent.job_id == job_id)
    current_max = (await db.execute(max_seq_stmt)).scalar() or 0
    next_seq = current_max + 1

    event = JobEvent(
        job_id=job_id,
        seq=next_seq,
        event_type=event_type,
        node=node,
        data=data or {},
    )
    db.add(event)
    await db.flush()
    return next_seq

async def list_events(
    db: AsyncSession,
    job_id: uuid.UUID,
    after_seq: int = 0
) -> List[JobEvent]:
    stmt = select(JobEvent).where(
        JobEvent.job_id == job_id,
        JobEvent.seq > after_seq
    ).order_by(JobEvent.seq.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def finish(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    now = datetime.now(timezone.utc)
    values: Dict[str, Any] = {
        "status": status,
        "finished_at": now,
        "progress": 1.0 if status == "succeeded" else 0.0,
    }
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error"] = error

    stmt = update(Job).where(Job.id == job_id).values(**values)
    await db.execute(stmt)

async def requeue_stale(db: AsyncSession, older_than_minutes: int = 15) -> int:
    """
    Jobs running with heartbeat_at older than 15 minutes go back to queued if attempts < 2,
    else failed with error worker_lost.
    """
    threshold = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    
    # 1. Fail those with attempts >= 2
    fail_stmt = update(Job).where(
        Job.status == "running",
        Job.heartbeat_at < threshold,
        Job.attempts >= 2
    ).values(
        status="failed",
        error="worker_lost",
        finished_at=datetime.now(timezone.utc)
    )
    res_fail = await db.execute(fail_stmt)
    
    # 2. Requeue those with attempts < 2
    requeue_stmt = update(Job).where(
        Job.status == "running",
        Job.heartbeat_at < threshold,
        Job.attempts < 2
    ).values(
        status="queued"
    )
    res_requeue = await db.execute(requeue_stmt)
    
    return res_fail.rowcount + res_requeue.rowcount
