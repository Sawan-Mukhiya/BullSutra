import uuid
from datetime import date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.agents import ResearchBriefRow

async def insert_brief(db: AsyncSession, row: Dict[str, Any]) -> uuid.UUID:
    brief_id = row.get("id") or uuid.uuid4()
    row["id"] = brief_id
    stmt = insert(ResearchBriefRow).values(row)
    await db.execute(stmt)
    return brief_id

async def get_latest_brief(
    db: AsyncSession,
    security_id: int,
    as_of: Optional[date] = None
) -> Optional[ResearchBriefRow]:
    stmt = select(ResearchBriefRow).where(ResearchBriefRow.security_id == security_id)
    if as_of:
        stmt = stmt.where(ResearchBriefRow.as_of <= as_of)
    stmt = stmt.order_by(ResearchBriefRow.as_of.desc(), ResearchBriefRow.created_at.desc()).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def get_brief_by_id(db: AsyncSession, brief_id: uuid.UUID) -> Optional[ResearchBriefRow]:
    stmt = select(ResearchBriefRow).where(ResearchBriefRow.id == brief_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_brief_history(
    db: AsyncSession,
    security_id: int,
    limit: int = 50
) -> List[ResearchBriefRow]:
    stmt = select(ResearchBriefRow).where(
        ResearchBriefRow.security_id == security_id
    ).order_by(ResearchBriefRow.as_of.desc(), ResearchBriefRow.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def list_latest_per_security(
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[ResearchBriefRow], int]:
    # Distinct on security_id ordered by security_id, as_of desc, created_at desc
    subq = select(
        ResearchBriefRow.id,
        func.row_number().over(
            partition_by=ResearchBriefRow.security_id,
            order_by=(ResearchBriefRow.as_of.desc(), ResearchBriefRow.created_at.desc())
        ).label("rn")
    ).subquery()

    count_stmt = select(func.count(subq.c.id)).where(subq.c.rn == 1)
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = select(ResearchBriefRow).join(
        subq, ResearchBriefRow.id == subq.c.id
    ).where(subq.c.rn == 1).order_by(ResearchBriefRow.created_at.desc()).limit(limit).offset(offset)

    res = await db.execute(stmt)
    items = list(res.scalars().all())
    return items, total
