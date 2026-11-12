from datetime import date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.securities import ReferenceSymbol, UniverseMembership

async def get_by_symbol(db: AsyncSession, symbol: str) -> Optional[ReferenceSymbol]:
    stmt = select(ReferenceSymbol).where(ReferenceSymbol.symbol == symbol.upper())
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def get_by_id(db: AsyncSession, sec_id: int) -> Optional[ReferenceSymbol]:
    stmt = select(ReferenceSymbol).where(ReferenceSymbol.id == sec_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def search(
    db: AsyncSession,
    q: Optional[str] = None,
    sector: Optional[str] = None,
    sector_group: Optional[str] = None,
    in_universe: Optional[bool] = None,
    as_of: Optional[date] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[ReferenceSymbol], int]:
    stmt = select(ReferenceSymbol)
    count_stmt = select(func.count(ReferenceSymbol.id))

    filters = []
    if q:
        q_clean = f"%{q.strip().upper()}%"
        filters.append(or_(
            ReferenceSymbol.symbol.ilike(q_clean),
            ReferenceSymbol.name.ilike(q_clean)
        ))
    if sector:
        filters.append(ReferenceSymbol.sector.ilike(f"%{sector.strip()}%"))
    if sector_group:
        filters.append(ReferenceSymbol.sector_group == sector_group.lower())

    if as_of and in_universe is not None:
        # Evaluate point-in-time universe membership for that month
        month_start = date(as_of.year, as_of.month, 1)
        subq = select(UniverseMembership.symbol).where(
            UniverseMembership.month_start == month_start,
            UniverseMembership.in_universe == in_universe
        )
        filters.append(ReferenceSymbol.symbol.in_(subq))
    elif in_universe is not None:
        filters.append(ReferenceSymbol.in_universe == in_universe)

    if filters:
        stmt = stmt.where(and_(*filters))
        count_stmt = count_stmt.where(and_(*filters))

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(ReferenceSymbol.symbol.asc()).limit(limit).offset(offset)
    items = list((await db.execute(stmt)).scalars().all())
    return items, total

async def list_universe_asof(db: AsyncSession, as_of: date) -> List[ReferenceSymbol]:
    month_start = date(as_of.year, as_of.month, 1)
    stmt = select(ReferenceSymbol).join(
        UniverseMembership, ReferenceSymbol.symbol == UniverseMembership.symbol
    ).where(
        UniverseMembership.month_start == month_start,
        UniverseMembership.in_universe.is_(True)
    ).order_by(UniverseMembership.rank.asc())
    res = await db.execute(stmt)
    items = list(res.scalars().all())
    if not items:
        # Fallback to current in_universe flag if month membership not yet calculated
        fallback_stmt = select(ReferenceSymbol).where(ReferenceSymbol.in_universe.is_(True)).order_by(ReferenceSymbol.symbol.asc())
        return list((await db.execute(fallback_stmt)).scalars().all())
    return items

async def upsert_securities(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(ReferenceSymbol).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in ReferenceSymbol.__table__.columns
        if col.name not in ("id", "symbol")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

get_security = get_by_id
get_security_by_symbol = get_by_symbol

async def upsert_universe_membership(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(UniverseMembership).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in UniverseMembership.__table__.columns
        if col.name not in ("month_start", "symbol")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["month_start", "symbol"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

get_security = get_by_id
get_security_by_symbol = get_by_symbol
