from datetime import date
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.core.time import is_trading_day_fallback, get_regime_id
from bullsutra.db.models.securities import DimTradingDay

async def is_trading_session(db: AsyncSession, d: date) -> bool:
    stmt = select(DimTradingDay.is_session).where(DimTradingDay.date == d)
    res = await db.execute(stmt)
    row = res.first()
    if row is not None:
        return bool(row[0])
    return is_trading_day_fallback(d)

async def get_trading_day(db: AsyncSession, d: date) -> Optional[DimTradingDay]:
    stmt = select(DimTradingDay).where(DimTradingDay.date == d)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def upsert_trading_days(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(DimTradingDay).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in DimTradingDay.__table__.columns
        if col.name != "date"
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["date"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def next_trading_session(db: AsyncSession, d: date) -> Optional[date]:
    stmt = select(DimTradingDay.date).where(
        DimTradingDay.date > d,
        DimTradingDay.is_session.is_(True)
    ).order_by(DimTradingDay.date.asc()).limit(1)
    res = await db.execute(stmt)
    row = res.first()
    return row[0] if row else None

async def upsert_trading_day(db: AsyncSession, d: date, is_session: bool, note: str = "") -> None:
    regime = get_regime_id(d)
    is_r3 = (regime == "regime_3")
    row = {
        "date": d,
        "is_session": is_session,
        "is_holiday": not is_session,
        "holiday_name": note if not is_session else None,
        "dow": d.weekday(),
        "regime_id": regime,
        "trading_week_id": d.isocalendar()[1],
        "stock_limit_pct": 15.0 if is_r3 else 10.0,
        "preopen_limit_pct": 5.0 if is_r3 else 2.0,
        "order_band_pct": 3.0 if is_r3 else 2.0,
        "mkt_breaker_id": "new_v2" if is_r3 else "old_v1",
        "after_market_orders": is_r3,
    }
    await upsert_trading_days(db, [row])

async def get_latest_trading_day(db: AsyncSession) -> Optional[DimTradingDay]:
    stmt = select(DimTradingDay).where(DimTradingDay.is_session.is_(True)).order_by(DimTradingDay.date.desc()).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()

async def list_trading_days(
    db: AsyncSession,
    start: Optional[date] = None,
    end: Optional[date] = None
) -> List[DimTradingDay]:
    stmt = select(DimTradingDay).where(DimTradingDay.is_session.is_(True))
    if start:
        stmt = stmt.where(DimTradingDay.date >= start)
    if end:
        stmt = stmt.where(DimTradingDay.date <= end)
    stmt = stmt.order_by(DimTradingDay.date.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
