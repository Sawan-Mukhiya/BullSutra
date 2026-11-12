import math
from datetime import date
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.db.models.prices import DailyBar, AdjEvent
from bullsutra.db.models.securities import DimTradingDay, ReferenceSymbol

async def get_price_frame(
    db: AsyncSession,
    security_id: int | str,
    end: date,
    lookback_bars: Optional[int] = None,
    start: Optional[date] = None,
) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by trade_date (DatetimeIndex, name 'date'), ascending,
    only rows with trade_date <= end.
    Columns: open, high, low, close (adjusted dynamically relative to anchor 'end' using adj_events:
             adj_close(t) = close(t) / PROD(t < ex_date <= end, step_factor)),
             raw_open, raw_high, raw_low, raw_close, prev_close_exchange,
             ret_adj_1d, volume, turnover, trades, regime_id, limit_pct, hit_upper, hit_lower, ret_over_limit.
    Property: the last row's adjusted close equals its raw close.
    """
    # Resolve symbol if security_id is str or int
    if isinstance(security_id, str):
        sym_stmt = select(ReferenceSymbol.id, ReferenceSymbol.symbol).where(ReferenceSymbol.symbol == security_id.upper())
        res = await db.execute(sym_stmt)
        row = res.first()
        if not row:
            return pd.DataFrame()
        sec_id, sym = row[0], row[1]
    else:
        sec_id = security_id
        sym_stmt = select(ReferenceSymbol.symbol).where(ReferenceSymbol.id == sec_id)
        res = await db.execute(sym_stmt)
        row = res.first()
        sym = row[0] if row else ""

    stmt = select(DailyBar).where(
        DailyBar.security_id == sec_id,
        DailyBar.trade_date <= end
    )
    if start:
        stmt = stmt.where(DailyBar.trade_date >= start)
    stmt = stmt.order_by(DailyBar.trade_date.asc())

    bars_res = await db.execute(stmt)
    bars = bars_res.scalars().all()
    if not bars:
        return pd.DataFrame()

    if lookback_bars and len(bars) > lookback_bars:
        bars = bars[-lookback_bars:]

    # Fetch adjustment events for this symbol up to end
    adj_stmt = select(AdjEvent).where(
        AdjEvent.symbol == sym,
        AdjEvent.ex_date <= end
    ).order_by(AdjEvent.ex_date.asc())
    adj_res = await db.execute(adj_stmt)
    adj_events = adj_res.scalars().all()

    # Build base DataFrame
    data = []
    for b in bars:
        data.append({
            "trade_date": b.trade_date,
            "raw_open": float(b.open) if b.open is not None else None,
            "raw_high": float(b.high) if b.high is not None else None,
            "raw_low": float(b.low) if b.low is not None else None,
            "raw_close": float(b.close),
            "prev_close_exchange": float(b.prev_close_exchange) if b.prev_close_exchange is not None else None,
            "ret_adj_1d": float(b.ret_over_limit * float(b.limit_pct)) if b.ret_over_limit is not None else None,
            "volume": int(b.volume),
            "turnover": float(b.turnover),
            "trades": b.trades,
            "regime_id": b.regime_id,
            "limit_pct": float(b.limit_pct),
            "hit_upper": b.hit_upper,
            "hit_lower": b.hit_lower,
            "ret_over_limit": b.ret_over_limit,
        })
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("date")

    # Compute dynamic cumulative adjustment relative to anchor 'end'
    # adj_factor(t) = 1 / PROD(t < ex_date <= end, step_factor)
    event_dict = {e.ex_date: float(e.step_factor) for e in adj_events}
    n = len(df)
    cum_factor = np.ones(n, dtype=np.float64)

    # For every bar at index i with trade_date t, find product of steps where t < ex_date <= end
    trade_dates = df["trade_date"].values
    for i, t in enumerate(trade_dates):
        prod = 1.0
        for ex_dt, step in event_dict.items():
            if t < ex_dt <= end:
                prod *= step
        cum_factor[i] = 1.0 / prod

    df["adj_factor"] = cum_factor
    df["close"] = df["raw_close"] * df["adj_factor"]
    df["open"] = np.where(df["raw_open"].notna(), df["raw_open"] * df["adj_factor"], np.nan)
    df["high"] = np.where(df["raw_high"].notna(), df["raw_high"] * df["adj_factor"], np.nan)
    df["low"] = np.where(df["raw_low"].notna(), df["raw_low"] * df["adj_factor"], np.nan)

    # Compute anchor-independent 1-day adjusted return if missing
    # ret_adj_1d(t) = close(t) / (close(t-1) / step_factor_if_ex(t)) - 1
    if "ret_adj_1d" not in df.columns or df["ret_adj_1d"].isna().any():
        raw_close = df["raw_close"].values
        ret_1d = np.full(n, np.nan, dtype=np.float64)
        for i in range(1, n):
            t = trade_dates[i]
            step = event_dict.get(t, 1.0)
            adj_prev = raw_close[i - 1] / step
            if adj_prev > 0:
                ret_1d[i] = (raw_close[i] / adj_prev) - 1.0
        df["ret_adj_1d"] = ret_1d

    return df

async def get_latest_trade_date(db: AsyncSession) -> Optional[date]:
    stmt = select(func.max(DailyBar.trade_date))
    res = await db.execute(stmt)
    return res.scalar()

async def get_trading_dates(db: AsyncSession, start: date, end: date) -> List[date]:
    stmt = select(DimTradingDay.date).where(
        DimTradingDay.date >= start,
        DimTradingDay.date <= end,
        DimTradingDay.is_session.is_(True)
    ).order_by(DimTradingDay.date.asc())
    res = await db.execute(stmt)
    return [r[0] for r in res.fetchall()]

async def upsert_bars(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(DailyBar).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in DailyBar.__table__.columns
        if col.name not in ("security_id", "trade_date")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["security_id", "trade_date"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def upsert_adj_events(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(AdjEvent).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in AdjEvent.__table__.columns
        if col.name not in ("symbol", "ex_date", "id")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "ex_date"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def get_all_prices_for_backtest(
    db: AsyncSession,
    symbols: List[str],
    start: date,
    end: date
) -> pd.DataFrame:
    stmt = select(DailyBar).where(
        DailyBar.symbol.in_(symbols),
        DailyBar.trade_date >= start,
        DailyBar.trade_date <= end
    ).order_by(DailyBar.trade_date.asc(), DailyBar.symbol.asc())
    res = await db.execute(stmt)
    bars = res.scalars().all()
    if not bars:
        return pd.DataFrame()

    data = [{
        "symbol": b.symbol,
        "date": b.trade_date,
        "raw_open": float(b.open) if b.open is not None else None,
        "raw_high": float(b.high) if b.high is not None else None,
        "raw_low": float(b.low) if b.low is not None else None,
        "raw_close": float(b.close),
        "prev_close_exchange": float(b.prev_close_exchange) if b.prev_close_exchange is not None else None,
        "volume": int(b.volume),
        "turnover": float(b.turnover),
        "regime_id": b.regime_id,
        "limit_pct": float(b.limit_pct),
        "ret_over_limit": b.ret_over_limit,
    } for b in bars]
    return pd.DataFrame(data)

async def get_latest_price_date_for_security(db: AsyncSession, security_id: int) -> Optional[date]:
    stmt = select(func.max(DailyBar.trade_date)).where(DailyBar.security_id == security_id)
    res = await db.execute(stmt)
    return res.scalar()

async def has_price_on_date(db: AsyncSession, security_id: int, dt: date) -> bool:
    stmt = select(DailyBar.trade_date).where(
        DailyBar.security_id == security_id,
        DailyBar.trade_date == dt
    ).limit(1)
    res = await db.execute(stmt)
    return res.scalar_one_or_none() is not None
