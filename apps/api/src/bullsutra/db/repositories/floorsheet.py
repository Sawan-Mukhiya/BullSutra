from datetime import date
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.prices import FloorsheetDailyAgg

async def get_floorsheet_agg_asof(
    db: AsyncSession,
    symbol: str,
    as_of: date,
    lookback_sessions: int = 20
) -> pd.DataFrame:
    stmt = select(FloorsheetDailyAgg).where(
        FloorsheetDailyAgg.symbol == symbol.upper(),
        FloorsheetDailyAgg.trade_date <= as_of
    ).order_by(FloorsheetDailyAgg.trade_date.desc()).limit(lookback_sessions)
    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    if not rows:
        return pd.DataFrame()
    rows.reverse()
    return pd.DataFrame([{
        "symbol": r.symbol,
        "trade_date": r.trade_date,
        "n_contracts": r.n_contracts,
        "avg_contract_value": float(r.avg_contract_value),
        "median_contract_value": float(r.median_contract_value),
        "block_share": float(r.block_share),
        "small_lot_share": float(r.small_lot_share),
        "top5_buyer_share": float(r.top5_buyer_share),
        "top5_seller_share": float(r.top5_seller_share),
        "buyer_hhi": float(r.buyer_hhi),
        "seller_hhi": float(r.seller_hhi),
        "n_buyer_brokers": r.n_buyer_brokers,
        "n_seller_brokers": r.n_seller_brokers,
        "bar_completeness": float(r.bar_completeness),
    } for r in rows])

async def upsert_floorsheet_agg(db: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = insert(FloorsheetDailyAgg).values(rows)
    update_cols = {
        col.name: stmt.excluded[col.name]
        for col in FloorsheetDailyAgg.__table__.columns
        if col.name not in ("symbol", "trade_date")
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "trade_date"],
        set_=update_cols
    )
    res = await db.execute(stmt)
    return res.rowcount
