from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.agents import AgentWeights

async def insert_weights(db: AsyncSession, row: Dict[str, Any]) -> int:
    stmt = insert(AgentWeights).values(row).returning(AgentWeights.id)
    res = await db.execute(stmt)
    return res.scalar_one()

async def get_latest_weights(db: AsyncSession, scope: str = "live") -> Optional[AgentWeights]:
    stmt = select(AgentWeights).where(
        AgentWeights.scope == scope
    ).order_by(AgentWeights.fitted_on.desc(), AgentWeights.created_at.desc()).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()
