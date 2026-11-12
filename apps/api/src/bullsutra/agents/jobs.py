"""Daily background jobs for signals and weights."""
from datetime import date
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select, and_

from bullsutra.agents.constants import LOGIC_VERSION
from bullsutra.worker.context import JobContext
from bullsutra.db.models.agents import AgentSignalRow, SignalOutcome, AgentWeights
from bullsutra.db.repositories.securities import list_universe_asof, get_security
from bullsutra.db.repositories.calendar import get_latest_trading_day
from bullsutra.db.repositories.prices import get_all_prices_for_backtest
from bullsutra.db.repositories.signals import upsert_signals
from bullsutra.db.repositories.weights import insert_weights
from bullsutra.db.repositories.outcomes import upsert_outcomes
from bullsutra.marketdata.db import build_snapshot_db
from bullsutra.agents.specialists import run_numeric_agents
from bullsutra.agents.calibration import (
    compute_outcomes,
    fit_weights,
    build_calibration_dataset,
    fit_calibrator,
    reliability_bins,
)

logger = structlog.get_logger(__name__)

async def run_signals_daily(ctx: JobContext) -> Dict[str, Any]:
    """Compute and store daily numeric signals for all active universe securities."""
    payload = ctx.payload or {}
    date_str = payload.get("date")
    async with ctx.session() as db:
        if date_str:
            as_of = date.fromisoformat(date_str)
        else:
            latest_day = await get_latest_trading_day(db)
            as_of = (latest_day.date if hasattr(latest_day, "date") else latest_day.trade_date) if latest_day else date.today()

        universe = await list_universe_asof(db, as_of)
    if not universe:
        return {"as_of": str(as_of), "securities": 0, "skipped": 0}

    total = len(universe)
    processed = 0
    skipped = 0

    for idx, sec in enumerate(universe):
        try:
            async with ctx.session() as db:
                snapshot = await build_snapshot_db(db, sec.id, as_of)
                # Verify security has a bar exactly on as_of
                has_bar_today = False
                if snapshot.prices is not None and not snapshot.prices.empty:
                    last_dt = snapshot.prices.index[-1]
                    last_d = last_dt.date() if hasattr(last_dt, "date") else last_dt
                    if last_d == as_of:
                        has_bar_today = True

                if not has_bar_today:
                    skipped += 1
                    continue

                signals = run_numeric_agents(snapshot)
                sig_rows = []
                for agent_name in ("news", "fundamentals", "technicals", "risk"):
                    sig = signals[agent_name]
                    sig_rows.append({
                        "security_id": sec.id,
                        "as_of": as_of,
                        "agent": agent_name,
                        "score": sig.score,
                        "confidence": sig.confidence,
                        "drivers": [d.model_dump(mode="json") for d in sig.drivers],
                        "risks": sig.risks,
                        "flags": sig.flags,
                        "meta": sig.meta,
                        "logic_version": LOGIC_VERSION,
                        "origin": "live",
                    })
                await upsert_signals(db, sig_rows)
                await db.commit()
            processed += 1
        except Exception as e:
            logger.warning("daily_signal_skipped_error", symbol=sec.symbol, error=str(e))
            skipped += 1

        prog = 0.05 + 0.90 * ((idx + 1) / total)
        await ctx.set_progress(prog)

    return {"as_of": str(as_of), "securities": processed, "skipped": skipped}

async def run_weights_update(ctx: JobContext) -> Dict[str, Any]:
    """Fit outcomes, weights, and confidence calibrator across universe history."""
    async with ctx.session() as db:
        latest_day = await get_latest_trading_day(db)
        cutoff = (latest_day.date if hasattr(latest_day, "date") else latest_day.trade_date) if latest_day else date.today()

    await ctx.set_progress(0.1)

    # 1. Load universe securities & agent_signals
    async with ctx.session() as db:
        universe = await list_universe_asof(db, cutoff)
        sec_ids = [s.id for s in universe] if universe else []

        # 2. Load agent_signals for universe
        stmt = select(AgentSignalRow).where(
            AgentSignalRow.security_id.in_(sec_ids),
            AgentSignalRow.logic_version == LOGIC_VERSION,
        ).order_by(AgentSignalRow.as_of.asc())
        res = await db.execute(stmt)
        raw_signals = res.scalars().all()

        if not raw_signals:
            default_w = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}
            await insert_weights(db, {
                "scope": "live",
                "fitted_on": cutoff,
                "weights": default_w,
                "calibrator": None,
                "metrics": {},
            })
            await db.commit()
            return {"weights": default_w, "calibrated": False}

        # 3. Load prices_long
        prices_long = await get_all_prices_for_backtest(db, sec_ids, start=None, end=cutoff)

    sig_df = pd.DataFrame([{
        "security_id": r.security_id,
        "as_of": r.as_of,
        "agent": r.agent,
        "score": r.score,
        "confidence": r.confidence,
        "origin": r.origin,
    } for r in raw_signals])

    # Prefer 'live' over 'backfill'
    sig_df = sig_df.sort_values(by=["security_id", "as_of", "agent", "origin"], ascending=[True, True, True, False])
    sig_df = sig_df.drop_duplicates(subset=["security_id", "as_of", "agent"], keep="first")

    await ctx.set_progress(0.3)

    # 4. Compute outcomes
    outcomes_df = compute_outcomes(prices_long, sig_df)
    if not outcomes_df.empty:
        outcome_rows = outcomes_df.to_dict(orient="records")
        async with ctx.session() as db:
            await upsert_outcomes(db, outcome_rows)
            await db.commit()

    await ctx.set_progress(0.6)

    # 5. Fit weights
    weights, wmetrics = fit_weights(outcomes_df, cutoff=cutoff)

    # 6. Build wide signals for calibration
    wide_rows = []
    for (sec_id, as_of_d), g in sig_df.groupby(["security_id", "as_of"]):
        row_dict = {"security_id": sec_id, "as_of": as_of_d}
        for _, srow in g.iterrows():
            a = srow["agent"]
            if a == "news":
                row_dict["news_s"] = srow["score"]
                row_dict["news_c"] = srow["confidence"]
            elif a == "fundamentals":
                row_dict["fund_s"] = srow["score"]
                row_dict["fund_c"] = srow["confidence"]
            elif a == "technicals":
                row_dict["tech_s"] = srow["score"]
                row_dict["tech_c"] = srow["confidence"]
            elif a == "risk":
                row_dict["risk_s"] = srow["score"]
                row_dict["risk_c"] = srow["confidence"]
        wide_rows.append(row_dict)
    signals_wide = pd.DataFrame(wide_rows)

    calib_dataset = build_calibration_dataset(signals_wide, prices_long, weights)
    
    # Store consensus outcomes for reporting
    if not calib_dataset.empty:
        cons_outcomes = []
        for _, r in calib_dataset.iterrows():
            cons_outcomes.append({
                "security_id": r["security_id"],
                "as_of": r["as_of"],
                "agent": "consensus",
                "horizon_days": 10,
                "score": r["score"],
                "forward_return": r["forward_return"],
                "realized_on": r["realized_on"],
                "hit": r["hit"],
                "logic_version": LOGIC_VERSION,
            })
        async with ctx.session() as db:
            await upsert_outcomes(db, cons_outcomes)
            await db.commit()

    cal = fit_calibrator(calib_dataset, cutoff=cutoff)

    # Calculate brier score and bins
    metrics: Dict[str, Any] = {
        **wmetrics,
        "n_calibration": len(calib_dataset),
    }

    if cal is not None and not calib_dataset.empty:
        val_df = calib_dataset[(calib_dataset["label"].isin(["BUY", "SELL"])) & (calib_dataset["hit"].notna())]
        if not val_df.empty:
            p_raw = val_df["raw_confidence"].astype(float).tolist()
            hits = val_df["hit"].astype(float).tolist()
            bins = reliability_bins(p_raw, hits)
            brier = float(np.mean((np.array(p_raw) - np.array(hits)) ** 2))
            metrics["brier_score"] = round(brier, 4)
            metrics["bins"] = bins

    async with ctx.session() as db:
        await insert_weights(db, {
            "scope": "live",
            "fitted_on": cutoff,
            "weights": weights,
            "calibrator": cal,
            "metrics": metrics,
        })
        await db.commit()

    await ctx.set_progress(1.0)
    return {"weights": weights, "calibrated": bool(cal is not None)}
