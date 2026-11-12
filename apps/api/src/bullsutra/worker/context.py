import uuid
from dataclasses import dataclass
from typing import AsyncIterator, Optional, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from bullsutra.db.repositories import jobs

@dataclass
class JobContext:
    job_id: uuid.UUID
    kind: str
    payload: Dict[str, Any]
    session_factory: async_sessionmaker

    async def emit(self, event_type: str, node: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> None:
        """Opens its own short session, calls jobs.append_event, commits."""
        async with self.session() as db:
            await jobs.append_event(db, self.job_id, event_type=event_type, node=node, data=data)
            await db.commit()

    async def set_progress(self, value: float, phase: Optional[str] = None) -> None:
        """0..1; updates jobs.progress AND emits event_type="progress" with data {"value": value, "phase": phase}."""
        async with self.session() as db:
            await jobs.set_progress(db, self.job_id, value)
            await jobs.append_event(
                db,
                self.job_id,
                event_type="progress",
                node=None,
                data={"value": value, "phase": phase}
            )
            await db.commit()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as s:
            try:
                yield s
            finally:
                await s.close()
