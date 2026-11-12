from datetime import date
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import select, delete, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.agents import AgentSignalRow

async def upsert_signals(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(AgentSignalRow).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in AgentSignalRow.__table__.columns
        if col.name not in ("id", "security_id", "as_of", "agent", "logic_version", "origin")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["security_id", "as_of", "agent", "logic_version", "origin"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def get_signals(
    db: AsyncSession,
    security_ids: List[int],
    start: date,
    end: date,
    origin: str,
    logic_version: str
) -> pd.DataFrame:
    stmt = select(AgentSignalRow).where(
        AgentSignalRow.security_id.in_(security_ids),
        AgentSignalRow.as_of >= start,
        AgentSignalRow.as_of <= end,
        AgentSignalRow.origin == origin,
        AgentSignalRow.logic_version == logic_version
    ).order_by(AgentSignalRow.as_of.asc())
    res = await db.execute(stmt)
    rows = res.scalars().all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        "id": r.id,
        "security_id": r.security_id,
        "as_of": r.as_of,
        "agent": r.agent,
        "score": r.score,
        "confidence": r.confidence,
        "drivers": r.drivers,
        "risks": r.risks,
        "flags": r.flags,
        "meta": r.meta,
        "logic_version": r.logic_version,
        "origin": r.origin,
    } for r in rows])

async def delete_signals(
    db: AsyncSession,
    origin: str,
    logic_version: str,
    start: Optional[date] = None,
    end: Optional[date] = None
) -> int:
    stmt = delete(AgentSignalRow).where(
        AgentSignalRow.origin == origin,
        AgentSignalRow.logic_version == logic_version
    )
    if start:
        stmt = stmt.where(AgentSignalRow.as_of >= start)
    if end:
        stmt = stmt.where(AgentSignalRow.as_of <= end)
    res = await db.execute(stmt)
    return res.rowcount
