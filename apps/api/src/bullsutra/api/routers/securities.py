from datetime import date
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.core.errors import SymbolNotFound, ValidationError
from bullsutra.db.session import get_db
from bullsutra.db.models.prices import DailyBar
from bullsutra.db.models.agents import ResearchBriefRow
from bullsutra.db.repositories import securities, prices
from bullsutra.schemas.common import Page
from bullsutra.schemas.securities import (
    SecuritySummary,
    SecurityDetail,
    Candle,
    OhlcvResponse,
    IndicatorsResponse,
)
from bullsutra.agents.indicators import compute_indicators, ALLOWED_INDICATORS

router = APIRouter(prefix="/securities", tags=["securities"])

@router.get("", response_model=Page[SecuritySummary])
async def list_securities(
    q: Optional[str] = None,
    sector_group: Optional[str] = None,
    in_universe: Optional[bool] = None,
    as_of: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    items, total = await securities.search(
        db, q=q, sector_group=sector_group, in_universe=in_universe,
        as_of=as_of, limit=limit, offset=offset
    )

    summaries = []
    for s in items:
        # Get latest bar close and change
        latest_bar_stmt = select(DailyBar).where(
            DailyBar.security_id == s.id
        ).order_by(DailyBar.trade_date.desc()).limit(1)
        res = await db.execute(latest_bar_stmt)
        b = res.scalar_one_or_none()

        change_pct = None
        if b and b.prev_close_exchange and float(b.prev_close_exchange) > 0:
            change_pct = round(((float(b.close) / float(b.prev_close_exchange)) - 1.0) * 100.0, 2)

        summaries.append(SecuritySummary(
            symbol=s.symbol,
            name=s.name,
            sector=s.sector,
            sector_group=s.sector_group,
            in_universe=s.in_universe,
            instrument_class=s.instrument_class,
            last_close=float(b.close) if b else None,
            last_trade_date=b.trade_date if b else None,
            change_pct=change_pct,
        ))

    return Page(items=summaries, total=total, limit=limit, offset=offset)

@router.get("/{symbol}", response_model=SecurityDetail)
async def get_security(symbol: str, db: AsyncSession = Depends(get_db)):
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Security with symbol {symbol.upper()} not found")

    latest_bar_stmt = select(DailyBar).where(
        DailyBar.security_id == sec.id
    ).order_by(DailyBar.trade_date.desc()).limit(1)
    res = await db.execute(latest_bar_stmt)
    b = res.scalar_one_or_none()

    brief_stmt = select(func.count(ResearchBriefRow.id)).where(ResearchBriefRow.security_id == sec.id)
    has_brief = bool((await db.execute(brief_stmt)).scalar() or 0)

    change_pct = None
    if b and b.prev_close_exchange and float(b.prev_close_exchange) > 0:
        change_pct = round(((float(b.close) / float(b.prev_close_exchange)) - 1.0) * 100.0, 2)

    return SecurityDetail(
        symbol=sec.symbol,
        name=sec.name,
        sector=sec.sector,
        sector_group=sec.sector_group,
        in_universe=sec.in_universe,
        instrument_class=sec.instrument_class,
        instrument_type=sec.instrument_type,
        listed_on=sec.listed_on,
        first_bar_date=sec.first_bar_date,
        last_bar_date=sec.last_bar_date,
        last_close=float(b.close) if b else None,
        last_trade_date=b.trade_date if b else None,
        change_pct=change_pct,
        has_brief=has_brief,
    )

@router.get("/{symbol}/ohlcv", response_model=OhlcvResponse)
async def get_ohlcv(
    symbol: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    adjusted: bool = True,
    db: AsyncSession = Depends(get_db)
):
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Symbol {symbol.upper()} not found")

    anchor = end
    if not anchor:
        anchor = await prices.get_latest_price_date_for_security(db, sec.id) or date.today()

    df = await prices.get_price_frame(
        db,
        security_id=sec.id,
        end=anchor,
        start=start,
        lookback_bars=365 if not start else None
    )
    if df.empty:
        return OhlcvResponse(symbol=sec.symbol, adjusted=adjusted, candles=[])

    candles = []
    for dt, r in df.iterrows():
        candles.append(Candle(
            date=r["trade_date"],
            open=float(r["open"]) if adjusted and pd.notna(r["open"]) else (float(r["raw_open"]) if pd.notna(r["raw_open"]) else None),
            high=float(r["high"]) if adjusted and pd.notna(r["high"]) else (float(r["raw_high"]) if pd.notna(r["raw_high"]) else None),
            low=float(r["low"]) if adjusted and pd.notna(r["low"]) else (float(r["raw_low"]) if pd.notna(r["raw_low"]) else None),
            close=float(r["close"]) if adjusted else float(r["raw_close"]),
            volume=int(r["volume"]),
            turnover=float(r["turnover"]),
            regime_id=str(r["regime_id"]),
            limit_pct=float(r["limit_pct"]),
            ret_adj_1d=float(r["ret_adj_1d"]) if pd.notna(r["ret_adj_1d"]) else None
        ))
    return OhlcvResponse(symbol=sec.symbol, adjusted=adjusted, candles=candles)

@router.get("/{symbol}/indicators", response_model=IndicatorsResponse)
async def get_indicators(
    symbol: str,
    names: str = "sma20,sma50,sma200,rsi14,macd,bbands20",
    start: Optional[date] = None,
    end: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    sec = await securities.get_by_symbol(db, symbol)
    if not sec:
        raise SymbolNotFound(f"Symbol {symbol.upper()} not found")

    requested = [n.strip().lower() for n in names.split(",") if n.strip()]
    for name in requested:
        if name not in ALLOWED_INDICATORS:
            raise ValidationError(f"Unknown indicator '{name}'. Allowed: {sorted(ALLOWED_INDICATORS)}")

    anchor = end
    if not anchor:
        anchor = await prices.get_latest_price_date_for_security(db, sec.id) or date.today()

    # Warm-up loading: load up to 300 extra bars before start
    df = await prices.get_price_frame(db, security_id=sec.id, end=anchor, lookback_bars=600)
    if df.empty:
        return IndicatorsResponse(symbol=sec.symbol, series={})

    indicators_map = compute_indicators(df, requested)
    series_out: Dict[str, List[Dict[str, Any]]] = {}

    for name, ind_data in indicators_map.items():
        points = []
        if isinstance(ind_data, pd.DataFrame):
            for dt, row in ind_data.iterrows():
                trade_dt = row.name.date() if hasattr(row.name, "date") else dt
                if start and trade_dt < start:
                    continue
                if end and trade_dt > end:
                    continue
                if row.isna().any():
                    continue
                point = {"date": trade_dt.isoformat()}
                point.update({col: float(val) for col, val in row.items()})
                points.append(point)
        else: # pd.Series
            for dt, val in ind_data.items():
                trade_dt = dt.date() if hasattr(dt, "date") else dt
                if start and trade_dt < start:
                    continue
                if end and trade_dt > end:
                    continue
                if pd.isna(val):
                    continue
                points.append({"date": trade_dt.isoformat(), "value": float(val)})
        series_out[name] = points

    return IndicatorsResponse(symbol=sec.symbol, series=series_out)
