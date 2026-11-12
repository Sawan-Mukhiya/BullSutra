"""Signal store backfill and wide-matrix loader for backtesting."""
from datetime import date
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from bullsutra.core.constants import MIN_BARS_SIGNALS, MIN_BARS_RISK
from bullsutra.worker.context import JobContext
from bullsutra.db.models.agents import AgentSignalRow
from bullsutra.db.repositories import prices, fundamentals, news, floorsheet, securities, calendar
from bullsutra.db.repositories.signals import upsert_signals
from bullsutra.marketdata.base import MarketSnapshot
from bullsutra.agents.specialists.technicals import technicals_series, technicals_signal
from bullsutra.agents.specialists.risk import risk_series, risk_signal
from bullsutra.agents.specialists.fundamentals import fundamentals_signal
from bullsutra.agents.specialists.news import news_signal

logger = structlog.get_logger(__name__)

async def backfill_signals(
    db: AsyncSession,
    security_ids: List[int],
    start: Optional[date] = None,
    end: Optional[date] = None,
    logic_version: str = "1.0.0",
    ctx: Optional[JobContext] = None,
) -> int:
    """Precompute and store deterministic signals for all universe securities."""
    total_secs = len(security_ids)
    total_inserted = 0

    for idx, sec_id in enumerate(security_ids):
        sec = await securities.get_by_id(db, sec_id)
        if not sec:
            continue

        sym = sec.symbol
        sector_group = sec.sector_group or "other"

        # 1. Load full price frame
        bars = await prices.get_price_frame(db, security_id=sec_id, end=end or date.today())
        if bars.empty or len(bars) < MIN_BARS_SIGNALS:
            continue

        # Filter by start if provided
        start_idx = MIN_BARS_SIGNALS - 1

        # 2. Vectorised technicals and risk series across full history
        tech_df = technicals_series(bars)
        risk_df = risk_series(bars)

        # 3. Load full fundamentals, news, floorsheet for fast sub-slicing
        fund_all = await fundamentals.get_fundamentals_asof(db, symbol=sym, as_of=end or date.today())
        news_all = await news.get_news_asof(db, security_id=sec_id, as_of=end or date.today(), window_days=3650)
        fs_all = await floorsheet.get_floorsheet_agg_asof(db, symbol=sym, as_of=end or date.today(), lookback_sessions=3650)

        # 4. Delete existing backfill rows for this security in date range
        del_stmt = delete(AgentSignalRow).where(
            AgentSignalRow.security_id == sec_id,
            AgentSignalRow.origin == "backfill",
            AgentSignalRow.logic_version == logic_version,
        )
        if start:
            del_stmt = del_stmt.where(AgentSignalRow.as_of >= start)
        if end:
            del_stmt = del_stmt.where(AgentSignalRow.as_of <= end)
        await db.execute(del_stmt)

        # 5. Build signal rows
        sig_rows: List[Dict[str, Any]] = []

        dates = bars.index
        for i in range(start_idx, len(bars)):
            cur_date = dates[i].date() if hasattr(dates[i], "date") else dates[i]
            if start and cur_date < start:
                continue
            if end and cur_date > end:
                break

            # Technicals row from vector series
            t_row = tech_df.iloc[i]
            sig_rows.append({
                "security_id": sec_id,
                "as_of": cur_date,
                "agent": "technicals",
                "score": float(t_row["score"]),
                "confidence": float(t_row["confidence"]),
                "drivers": [],
                "risks": [],
                "flags": ["insufficient_history"] if t_row["insufficient"] else [],
                "meta": {},
                "logic_version": logic_version,
                "origin": "backfill",
            })

            # Risk row from vector series
            r_row = risk_df.iloc[i]
            r_components = {
                "vol": float(r_row["c_vol"]),
                "dd": float(r_row["c_dd"]),
                "liq": float(r_row["c_liq"]),
                "circ": float(r_row["c_circ"]),
                "gap": float(r_row["c_gap"]),
            }
            sig_rows.append({
                "security_id": sec_id,
                "as_of": cur_date,
                "agent": "risk",
                "score": float(r_row["score"]),
                "confidence": float(r_row["confidence"]),
                "drivers": [],
                "risks": [],
                "flags": ["insufficient_history"] if r_row["insufficient"] else [],
                "meta": {"components": r_components},
                "logic_version": logic_version,
                "origin": "backfill",
            })

            # Slice fundamentals and news up to cur_date for light snapshot
            sub_fund = pd.DataFrame()
            if not fund_all.empty and "usable_from" in fund_all.columns:
                sub_fund = fund_all[fund_all["usable_from"] <= cur_date]

            sub_news = pd.DataFrame()
            if not news_all.empty and "published_at" in news_all.columns:
                # Up to cur_date 16:00
                from bullsutra.core.time import cutoff_datetime
                c_dt = cutoff_datetime(cur_date)
                sub_news = news_all[news_all["published_at"] <= c_dt]

            snap_light = MarketSnapshot(
                symbol=sym,
                security_id=sec_id,
                as_of=cur_date,
                prices=bars.iloc[: i + 1],
                fundamentals=sub_fund,
                news=sub_news,
                sector_group=sector_group,
            )

            # Fundamentals signal
            f_sig = fundamentals_signal(snap_light)
            sig_rows.append({
                "security_id": sec_id,
                "as_of": cur_date,
                "agent": "fundamentals",
                "score": f_sig.score,
                "confidence": f_sig.confidence,
                "drivers": [],
                "risks": [],
                "flags": f_sig.flags,
                "meta": {},
                "logic_version": logic_version,
                "origin": "backfill",
            })

            # News signal
            n_sig = news_signal(snap_light)
            sig_rows.append({
                "security_id": sec_id,
                "as_of": cur_date,
                "agent": "news",
                "score": n_sig.score,
                "confidence": n_sig.confidence,
                "drivers": [],
                "risks": [],
                "flags": n_sig.flags,
                "meta": {},
                "logic_version": logic_version,
                "origin": "backfill",
            })

        # Upsert in chunks of 5000
        for chunk_idx in range(0, len(sig_rows), 5000):
            chunk = sig_rows[chunk_idx : chunk_idx + 5000]
            await upsert_signals(db, chunk)
            await db.commit()
            total_inserted += len(chunk)

        if ctx is not None:
            prog = (idx + 1) / total_secs
            await ctx.set_progress(prog, phase=f"Backfilled {sym} ({idx+1}/{total_secs})")

    return total_inserted

async def load_signals_wide(
    db: AsyncSession,
    security_ids: List[int],
    start: Optional[date],
    end: Optional[date],
    logic_version: str = "1.0.0",
) -> pd.DataFrame:
    """Load agent signals pivoted to wide format for backtesting."""
    stmt = select(AgentSignalRow).where(
        AgentSignalRow.security_id.in_(security_ids),
        AgentSignalRow.logic_version == logic_version,
    )
    if start:
        stmt = stmt.where(AgentSignalRow.as_of >= start)
    if end:
        stmt = stmt.where(AgentSignalRow.as_of <= end)
    stmt = stmt.order_by(AgentSignalRow.as_of.asc())

    res = await db.execute(stmt)
    rows = res.scalars().all()

    if not rows:
        return pd.DataFrame(columns=[
            "security_id", "date", "news_s", "news_c", "fund_s", "fund_c",
            "tech_s", "tech_c", "risk_s", "risk_c", "risk_liq"
        ])

    df = pd.DataFrame([{
        "security_id": r.security_id,
        "as_of": r.as_of,
        "agent": r.agent,
        "score": r.score,
        "confidence": r.confidence,
        "origin": r.origin,
        "meta": r.meta,
    } for r in rows])

    # Prefer 'live' over 'backfill' for the same key
    df = df.sort_values(by=["security_id", "as_of", "agent", "origin"], ascending=[True, True, True, False])
    df = df.drop_duplicates(subset=["security_id", "as_of", "agent"], keep="first")

    wide_records = []
    for (sec_id, as_of_d), g in df.groupby(["security_id", "as_of"]):
        record = {
            "security_id": sec_id,
            "date": as_of_d,
            "news_s": 0.0,
            "news_c": 0.0,
            "fund_s": 0.0,
            "fund_c": 0.0,
            "tech_s": 0.0,
            "tech_c": 0.0,
            "risk_s": 0.5,
            "risk_c": 0.0,
            "risk_liq": 0.0,
        }
        for _, row in g.iterrows():
            a = row["agent"]
            if a == "news":
                record["news_s"] = float(row["score"])
                record["news_c"] = float(row["confidence"])
            elif a == "fundamentals":
                record["fund_s"] = float(row["score"])
                record["fund_c"] = float(row["confidence"])
            elif a == "technicals":
                record["tech_s"] = float(row["score"])
                record["tech_c"] = float(row["confidence"])
            elif a == "risk":
                record["risk_s"] = float(row["score"])
                record["risk_c"] = float(row["confidence"])
                meta = row.get("meta") or {}
                comps = meta.get("components") or {}
                record["risk_liq"] = float(comps.get("liq", 0.0) or 0.0)
        wide_records.append(record)

    wide_df = pd.DataFrame(wide_records)
    wide_df = wide_df.sort_values(by=["date", "security_id"]).reset_index(drop=True)
    return wide_df
