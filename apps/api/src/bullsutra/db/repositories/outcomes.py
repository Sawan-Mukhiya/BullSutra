from datetime import date
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.agents import SignalOutcome

async def upsert_outcomes(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(SignalOutcome).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in SignalOutcome.__table__.columns
        if col.name not in ("security_id", "as_of", "agent", "horizon_days", "logic_version")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["security_id", "as_of", "agent", "horizon_days", "logic_version"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def get_outcomes(
    db: AsyncSession,
    agent: str,
    up_to_realized_on: date,
    limit_last_n: Optional[int] = None
) -> pd.DataFrame:
    stmt = select(SignalOutcome).where(
        SignalOutcome.agent == agent,
        SignalOutcome.realized_on <= up_to_realized_on,
        SignalOutcome.hit.is_not(None)
    ).order_by(SignalOutcome.realized_on.desc())
    if limit_last_n:
        stmt = stmt.limit(limit_last_n)
    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    if not rows:
        return pd.DataFrame()
    rows.reverse()
    return pd.DataFrame([{
        "security_id": r.security_id,
        "as_of": r.as_of,
        "agent": r.agent,
        "horizon_days": r.horizon_days,
        "score": r.score,
        "forward_return": float(r.forward_return) if r.forward_return is not None else None,
        "realized_on": r.realized_on,
        "hit": r.hit,
        "logic_version": r.logic_version,
    } for r in rows])

async def get_unresolved_candidates(db: AsyncSession, as_of_max: date, horizon: int) -> List[Dict[str, Any]]:
    stmt = select(SignalOutcome).where(
        SignalOutcome.as_of <= as_of_max,
        SignalOutcome.horizon_days == horizon,
        SignalOutcome.hit.is_(None)
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    return [{
        "security_id": r.security_id,
        "as_of": r.as_of,
        "agent": r.agent,
        "horizon_days": r.horizon_days,
        "score": r.score,
        "logic_version": r.logic_version,
    } for r in rows]
