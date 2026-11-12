import asyncio
import signal
import sys
import uuid
import structlog
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.config import settings
from bullsutra.core.logging import job_id_ctx
from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories import jobs, backtests
from bullsutra.worker.context import JobContext
from bullsutra.worker.handlers import HANDLERS

logger = structlog.get_logger(__name__)

TIMEOUTS: Dict[str, int] = {
    "research": 300,
    "backtest": 3600,
    "signals_backfill": 14400,
}
DEFAULT_TIMEOUT = 1800

class WorkerRunner:
    def __init__(self, concurrency: Optional[int] = None):
        self.concurrency = concurrency or settings.WORKER_CONCURRENCY
        self.stopping = False
        self.tasks: list[asyncio.Task] = []

    async def heartbeat_loop(self, job_id: uuid.UUID, stop_ev: asyncio.Event):
        while not stop_ev.is_set():
            try:
                await asyncio.wait_for(stop_ev.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                try:
                    async with async_session_factory() as session:
                        await jobs.heartbeat(session, job_id)
                        await session.commit()
                except Exception as e:
                    logger.warning("heartbeat_failed", job_id=str(job_id), error=str(e))

    async def execute_job(self, job_obj) -> None:
        job_id = job_obj.id
        kind = job_obj.kind
        job_id_ctx.set(str(job_id))
        logger.info("job_claimed", job_id=str(job_id), kind=kind)

        ctx = JobContext(
            job_id=job_id,
            kind=kind,
            payload=job_obj.payload or {},
            session_factory=async_session_factory
        )

        await ctx.emit("job_started", data={"job_id": str(job_id), "kind": kind})

        stop_heartbeat = asyncio.Event()
        heartbeat_task = asyncio.create_task(self.heartbeat_loop(job_id, stop_heartbeat))

        timeout = TIMEOUTS.get(kind, DEFAULT_TIMEOUT)
        handler = HANDLERS.get(kind)

        try:
            if not handler:
                raise ValueError(f"Unknown job kind: '{kind}'")

            result = await asyncio.wait_for(handler(ctx), timeout=timeout)

            # Success
            async with async_session_factory() as session:
                await jobs.finish(session, job_id, status="succeeded", result=result)
                await session.commit()

            await ctx.emit("job_finished", data=result or {})
            logger.info("job_succeeded", job_id=str(job_id), kind=kind)

        except Exception as exc:
            err_msg = str(exc)[:2000]
            logger.error("job_failed", job_id=str(job_id), kind=kind, error=err_msg, exc_info=True)

            async with async_session_factory() as session:
                await jobs.finish(session, job_id, status="failed", error=err_msg)
                if kind == "backtest" and "backtest_id" in ctx.payload:
                    try:
                        bt_id = uuid.UUID(ctx.payload["backtest_id"])
                        await backtests.update_status(session, bt_id, status="failed", error=err_msg)
                    except Exception:
                        pass
                await session.commit()

            await ctx.emit("job_failed", data={"error": err_msg})

        finally:
            stop_heartbeat.set()
            await heartbeat_task
            job_id_ctx.set(None)

    async def worker_loop(self, worker_id: int):
        logger.info("worker_task_started", worker_id=worker_id)
        while not self.stopping:
            try:
                job_obj = None
                async with async_session_factory() as session:
                    job_obj = await jobs.claim_next(session)
                    if job_obj:
                        await session.commit()

                if job_obj:
                    await self.execute_job(job_obj)
                else:
                    await asyncio.sleep(2.0)
            except Exception as e:
                logger.error("worker_loop_error", worker_id=worker_id, error=str(e), exc_info=True)
                await asyncio.sleep(2.0)
        logger.info("worker_task_stopped", worker_id=worker_id)

    async def start(self):
        logger.info("starting_worker_runner", concurrency=self.concurrency)
        # Requeue stale jobs at startup
        async with async_session_factory() as session:
            count = await jobs.requeue_stale(session, older_than_minutes=15)
            await session.commit()
            if count > 0:
                logger.info("requeued_stale_jobs", count=count)

        self.tasks = [
            asyncio.create_task(self.worker_loop(i))
            for i in range(self.concurrency)
        ]

    async def stop(self):
        logger.info("stopping_worker_runner")
        self.stopping = True
        if self.tasks:
            # Wait up to 60 seconds for active jobs to conclude
            try:
                await asyncio.wait_for(asyncio.gather(*self.tasks, return_exceptions=True), timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("worker_stop_timeout_cancelling_tasks")
                for t in self.tasks:
                    t.cancel()
