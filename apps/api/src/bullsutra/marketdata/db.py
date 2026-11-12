from datetime import date
from typing import Optional, List
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.core.time import get_regime_id
from bullsutra.db.models.securities import CorporateAction, IndexDaily, ReferenceSymbol
from bullsutra.db.repositories import prices, fundamentals, securities, calendar, floorsheet, news
from bullsutra.marketdata.base import MarketDataProvider, MarketSnapshot

class DbMarketData(MarketDataProvider):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_bars(self, symbol: str, as_of: date, lookback_sessions: int = 250, adjusted: bool = True) -> pd.DataFrame:
        df = await prices.get_price_frame(self.db, security_id=symbol, end=as_of, lookback_bars=lookback_sessions)
        if not adjusted and not df.empty:
            df["close"] = df["raw_close"]
            df["open"] = df["raw_open"]
            df["high"] = df["raw_high"]
            df["low"] = df["raw_low"]
        return df

    async def get_financials(self, symbol: str, as_of: date) -> pd.DataFrame:
        return await fundamentals.get_fundamentals_asof(self.db, symbol=symbol, as_of=as_of)

    async def get_actions(self, symbol: str, as_of: date) -> list[dict]:
        stmt = select(CorporateAction).where(
            CorporateAction.symbol == symbol.upper(),
            CorporateAction.usable_from.is_not(None),
            CorporateAction.usable_from <= as_of
        ).order_by(CorporateAction.usable_from.asc())
        res = await self.db.execute(stmt)
        actions = res.scalars().all()
        return [{
            "id": a.id,
            "symbol": a.symbol,
            "fiscal_year": a.fiscal_year,
            "action_type": a.action_type,
            "announced_at": a.announced_at,
            "usable_from": a.usable_from,
            "ex_date": a.ex_date,
            "cash_pct": float(a.cash_pct) if a.cash_pct is not None else None,
            "bonus_pct": float(a.bonus_pct) if a.bonus_pct is not None else None,
        } for a in actions]

    async def get_universe(self, as_of: date) -> list[str]:
        sec_list = await securities.list_universe_asof(self.db, as_of=as_of)
        return [s.symbol for s in sec_list]

    async def get_regime(self, d: date) -> str:
        day = await calendar.get_trading_day(self.db, d)
        return day.regime_id if day else get_regime_id(d)

    async def get_index(self, as_of: date, lookback_sessions: int = 250) -> pd.DataFrame:
        stmt = select(IndexDaily).where(
            IndexDaily.index_name == "NEPSE",
            IndexDaily.trade_date <= as_of
        ).order_by(IndexDaily.trade_date.desc()).limit(lookback_sessions)
        res = await self.db.execute(stmt)
        rows = list(res.scalars().all())
        if not rows:
            return pd.DataFrame()
        rows.reverse()
        return pd.DataFrame([{
            "date": r.trade_date,
            "open": float(r.open) if r.open is not None else None,
            "high": float(r.high) if r.high is not None else None,
            "low": float(r.low) if r.low is not None else None,
            "close": float(r.close),
            "volume": r.volume,
            "turnover": float(r.turnover) if r.turnover is not None else None,
        } for r in rows]).set_index("date")

    async def get_floorsheet_agg(self, symbol: str, as_of: date, lookback_sessions: int = 20) -> pd.DataFrame:
        return await floorsheet.get_floorsheet_agg_asof(self.db, symbol=symbol, as_of=as_of, lookback_sessions=lookback_sessions)

async def build_snapshot_db(db: AsyncSession, security_id: int | str, as_of: date) -> MarketSnapshot:
    """Build a complete point-in-time MarketSnapshot for a given security and as_of date."""
    if isinstance(security_id, str):
        sec = await securities.get_security_by_symbol(db, security_id)
    else:
        sec = await securities.get_security(db, security_id)
        
    if sec is None:
        raise ValueError(f"Security '{security_id}' not found.")

    bars_df = await prices.get_price_frame(db, security_id=sec.id, end=as_of, lookback_bars=250)
    fund_df = await fundamentals.get_fundamentals_asof(db, symbol=sec.symbol, as_of=as_of)
    news_df = await news.get_news_asof(db, security_id=sec.id, as_of=as_of, window_days=14)
    fs_df = await floorsheet.get_floorsheet_agg_asof(db, symbol=sec.symbol, as_of=as_of, lookback_sessions=20)
    day = await calendar.get_trading_day(db, as_of)
    regime = day.regime_id if day else get_regime_id(as_of)

    return MarketSnapshot(
        symbol=sec.symbol,
        security_id=sec.id,
        as_of=as_of,
        prices=bars_df,
        fundamentals=fund_df,
        news=news_df,
        company_name=getattr(sec, "name", sec.symbol),
        sector=sec.sector,
        sector_group=sec.sector_group or "other",
        floorsheet_agg=fs_df,
        regime_id=regime,
    )
