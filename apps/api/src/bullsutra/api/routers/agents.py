import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Header, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from bullsutra.core.errors import NotFound, Unauthorized, Forbidden
from bullsutra.core.security import Principal
from bullsutra.api.deps import require_admin
from bullsutra.db.session import get_db, async_session_factory
from bullsutra.db.repositories import weights, jobs
from bullsutra.schemas.agents import RunRequest, RunResponse, WeightsOut, CalibrationOut
from bullsutra.schemas.jobs import JobOut
from bullsutra.services import research_service

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/run", response_model=RunResponse)
async def run_agents(
    req: RunRequest,
    response: Response,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    status_code, res = await research_service.request_run(db, p, req)
    response.status_code = status_code
    return res

@router.get("/runs/{job_id}", response_model=JobOut)
async def get_run(
    job_id: uuid.UUID,
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    job = await jobs.get_by_id(db, job_id)
    if not job:
        raise NotFound(f"Job '{job_id}' not found")
    return JobOut(
        id=str(job.id),
        kind=job.kind,
        status=job.status,
        progress=float(job.progress),
        payload=job.payload or {},
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )

@router.get("/runs/{job_id}/events")
async def stream_run_events(
    job_id: uuid.UUID,
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    p: Principal = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    job = await jobs.get_by_id(db, job_id)
    if not job:
        raise NotFound(f"Job '{job_id}' not found")

    start_seq = 0
    if last_event_id:
        try:
            start_seq = int(last_event_id)
        except ValueError:
            start_seq = 0

    async def event_generator():
        current_seq = start_seq
        start_time = asyncio.get_event_loop().time()
        last_ping = start_time

        while True:
            if await request.is_disconnected():
                break

            now = asyncio.get_event_loop().time()
            if now - start_time > 1800:  # 30 minutes timeout
                yield {"event": "end", "data": "{}"}
                break

            async with async_session_factory() as session:
                events = await jobs.list_events(session, job_id, after_seq=current_seq)

            terminal_reached = False
            for ev in events:
                current_seq = ev.seq
                event_payload = {
                    "seq": ev.seq,
                    "type": ev.event_type,
                    "node": ev.node,
                    "data": ev.data,
                    "ts": ev.created_at.isoformat()
                }
                yield {
                    "id": str(ev.seq),
                    "event": ev.event_type,
                    "data": json.dumps(event_payload)
                }
                if ev.event_type in ("job_finished", "job_failed"):
                    terminal_reached = True

            if terminal_reached:
                yield {"event": "end", "data": "{}"}
                break

            # Send comment ping heartbeat every 15s if no events
            if not events and (now - last_ping >= 15.0):
                yield {"comment": "ping"}
                last_ping = now

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())

@router.get("/weights/latest", response_model=WeightsOut)
async def get_latest_weights(db: AsyncSession = Depends(get_db)):
    w = await weights.get_latest_weights(db, scope="live")
    if not w:
        return WeightsOut(
            fitted_on=None,
            weights={"news": 1.0, "fundamentals": 1.0, "technicals": 1.0},
            metrics={},
            calibrator_available=False
        )
    return WeightsOut(
        fitted_on=w.fitted_on,
        weights=w.weights,
        metrics=w.metrics,
        calibrator_available=bool(w.calibrator)
    )

@router.get("/calibration", response_model=CalibrationOut)
async def get_calibration(db: AsyncSession = Depends(get_db)):
    w = await weights.get_latest_weights(db, scope="live")
    if not w or not w.calibrator:
        return CalibrationOut(
            fitted_on=None,
            n_samples=0,
            brier_score=None,
            bins=[]
        )
    cal = w.calibrator
    return CalibrationOut(
        fitted_on=w.fitted_on,
        n_samples=cal.get("n_samples", 0),
        brier_score=cal.get("brier_score"),
        bins=cal.get("bins", [])
    )
