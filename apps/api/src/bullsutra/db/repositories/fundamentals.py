from datetime import date
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.fundamentals import QuarterlyFinancial

async def get_fundamentals_asof(
    db: AsyncSession,
    symbol: str,
    as_of: date
) -> pd.DataFrame:
    """
    Returns all rows with usable_from <= as_of, one row per (fiscal_year, quarter)
    using the latest announced_at for that pair, sorted by (fiscal_year, quarter) ascending.
    """
    stmt = select(QuarterlyFinancial).where(
        QuarterlyFinancial.symbol == symbol.upper(),
        QuarterlyFinancial.usable_from.is_not(None),
        QuarterlyFinancial.usable_from <= as_of
    ).order_by(
        QuarterlyFinancial.fiscal_year.asc(),
        QuarterlyFinancial.quarter.asc(),
        QuarterlyFinancial.announced_at.desc().nullslast()
    )
    res = await db.execute(stmt)
    rows = res.scalars().all()
    if not rows:
        return pd.DataFrame()

    seen = set()
    deduped = []
    for r in rows:
        key = (r.fiscal_year, r.quarter)
        if key not in seen:
            seen.add(key)
            deduped.append({
                "symbol": r.symbol,
                "fiscal_year": r.fiscal_year,
                "quarter": r.quarter,
                "period_end": r.period_end,
                "announced_at": r.announced_at,
                "usable_from": r.usable_from,
                "revenue": float(r.revenue) if r.revenue is not None else None,
                "net_profit": float(r.net_profit) if r.net_profit is not None else None,
                "eps_reported": float(r.eps_reported) if r.eps_reported is not None else None,
                "eps_basis": r.eps_basis,
                "eps_ytd": float(r.eps_ytd) if r.eps_ytd is not None else None,
                "eps_annualized": float(r.eps_annualized) if r.eps_annualized is not None else None,
                "eps_ttm": float(r.eps_ttm) if r.eps_ttm is not None else None,
                "bvps": float(r.bvps) if r.bvps is not None else None,
                "paid_up_capital": float(r.paid_up_capital) if r.paid_up_capital is not None else None,
                "shares_outstanding_est": r.shares_outstanding_est,
                "roe_annualized": float(r.roe_annualized) if r.roe_annualized is not None else None,
                "pe_reported": float(r.pe_reported) if r.pe_reported is not None else None,
                "npl_pct": float(r.npl_pct) if r.npl_pct is not None else None,
                "unit_multiplier_applied": float(r.unit_multiplier_applied) if r.unit_multiplier_applied is not None else None,
                "source": r.source,
                "is_restated": r.is_restated,
            })
    return pd.DataFrame(deduped)

async def upsert_quarterly_financials(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(QuarterlyFinancial).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in QuarterlyFinancial.__table__.columns
        if col.name not in ("symbol", "fiscal_year", "quarter", "is_restated")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "fiscal_year", "quarter", "is_restated"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount

async def get_all_fundamentals(db: AsyncSession, symbols: List[str]) -> pd.DataFrame:
    stmt = select(QuarterlyFinancial).where(
        QuarterlyFinancial.symbol.in_(symbols)
    ).order_by(QuarterlyFinancial.symbol.asc(), QuarterlyFinancial.usable_from.asc())
    res = await db.execute(stmt)
    rows = res.scalars().all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        "symbol": r.symbol,
        "fiscal_year": r.fiscal_year,
        "quarter": r.quarter,
        "period_end": r.period_end,
        "announced_at": r.announced_at,
        "usable_from": r.usable_from,
        "revenue": float(r.revenue) if r.revenue is not None else None,
        "net_profit": float(r.net_profit) if r.net_profit is not None else None,
        "eps_reported": float(r.eps_reported) if r.eps_reported is not None else None,
        "eps_basis": r.eps_basis,
        "eps_ytd": float(r.eps_ytd) if r.eps_ytd is not None else None,
        "eps_annualized": float(r.eps_annualized) if r.eps_annualized is not None else None,
        "eps_ttm": float(r.eps_ttm) if r.eps_ttm is not None else None,
        "bvps": float(r.bvps) if r.bvps is not None else None,
        "paid_up_capital": float(r.paid_up_capital) if r.paid_up_capital is not None else None,
        "shares_outstanding_est": r.shares_outstanding_est,
        "roe_annualized": float(r.roe_annualized) if r.roe_annualized is not None else None,
        "npl_pct": float(r.npl_pct) if r.npl_pct is not None else None,
        "source": r.source,
    } for r in rows])
