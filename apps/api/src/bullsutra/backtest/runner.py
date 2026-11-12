"""End-to-end backtest workflow runner."""
import asyncio
import uuid
from datetime import date, datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from bullsutra.worker.context import JobContext
from bullsutra.agents.constants import LOGIC_VERSION
from bullsutra.db.models.backtests import BacktestRun
from bullsutra.db.repositories import securities, prices, calendar, backtests
from bullsutra.db.repositories.prices import get_all_prices_for_backtest
from bullsutra.marketdata.db import DbMarketData
from bullsutra.backtest.config import BacktestConfig
from bullsutra.backtest.constants import STRATEGY_KEYS, BENCHMARK_KEYS
from bullsutra.backtest.signal_store import load_signals_wide
from bullsutra.backtest.folds import make_folds, Fold
from bullsutra.backtest.strategies import get_decider, Decision
from bullsutra.backtest.engine import PortfolioEngine, EngineResult
from bullsutra.backtest.benchmarks import simulate_bh_equal_weight, simulate_bh_nepse_index
from bullsutra.backtest.metrics import compute_metrics
from bullsutra.backtest.bootstrap import paired_block_bootstrap
from bullsutra.backtest.calibration_eval import evaluate_calibration
from bullsutra.backtest.persist import persist_backtest_results
from bullsutra.agents.calibration import (
    compute_outcomes,
    fit_weights,
    build_calibration_dataset,
    fit_calibrator,
)

logger = structlog.get_logger(__name__)

async def run_backtest(ctx: JobContext, backtest_id: uuid.UUID) -> Dict[str, Any]:
    """Execute complete walk-forward backtest across strategies and benchmarks."""
    async with ctx.session() as db:
        # 1. Phase: Load (0.05)
        await ctx.set_progress(0.05, phase="Loading backtest run configuration")
        stmt = select(BacktestRun).where(BacktestRun.id == backtest_id)
        res = await db.execute(stmt)
        run = res.scalar_one_or_none()
        if not run:
            raise ValueError(f"Backtest run '{backtest_id}' not found")

        await backtests.update_status(db, backtest_id, status="running")
        await db.commit()

        cfg_dict = dict(run.config or {})
        cfg = BacktestConfig(**cfg_dict)
        logic_v = cfg.logic_version or LOGIC_VERSION

        # Resolve universe
        latest_day = await calendar.get_latest_trading_day(db)
        latest_d = (latest_day.date if hasattr(latest_day, "date") else latest_day.trade_date) if latest_day else date.today()
        as_of_end = cfg.end_date or latest_d
        universe = await securities.list_universe_asof(db, as_of=as_of_end)
        if not universe:
            # Fallback to search if universe_membership not populated for that specific date
            universe_all, _ = await securities.search(db, limit=40)
            universe = universe_all
            
        sec_ids = [s.id for s in universe]
        symbol_map = {s.id: s.symbol for s in universe}
        delisted_dict = {s.id: s.delisted_on for s in universe if s.delisted_on}

        # 2. Phase: Prepare (0.15)
        await ctx.set_progress(0.15, phase="Loading market data, prices, and signals")
        prices_long = await get_all_prices_for_backtest(db, sec_ids, start=cfg.start_date, end=as_of_end)
        signals_wide = await load_signals_wide(db, sec_ids, start=cfg.start_date, end=as_of_end, logic_version=logic_v)

        if signals_wide.empty:
            err_msg = "Signal store is incomplete. Run: python -m bullsutra.cli backtest backfill-signals"
            await backtests.update_status(db, backtest_id, status="failed", error=err_msg)
            await db.commit()
            raise RuntimeError(err_msg)

        # Check coverage on last date
        unique_dates = sorted(signals_wide["date"].unique())
        last_sig_date = unique_dates[-1]
        last_date_sigs = signals_wide[signals_wide["date"] == last_sig_date]
        if len(last_date_sigs) < (0.5 * len(sec_ids)):
            err_msg = "Signal store is incomplete. Run: python -m bullsutra.cli backtest backfill-signals"
            await backtests.update_status(db, backtest_id, status="failed", error=err_msg)
            await db.commit()
            raise RuntimeError(err_msg)

        # Index data
        db_md = DbMarketData(db)
        index_df = await db_md.get_index(as_of=as_of_end, lookback_sessions=3000)

        # Global trading dates
        cal_days = await calendar.list_trading_days(db, start=unique_dates[0], end=as_of_end)
        trading_dates = [(cd.date if hasattr(cd, "date") else cd.trade_date) for cd in cal_days] if cal_days else unique_dates

        # Outcomes across entire signals history
        sig_long_rows = []
        for _, r in signals_wide.iterrows():
            sec_id = r["security_id"]
            d = r["date"]
            for a, s_col in [("news", "news_s"), ("fundamentals", "fund_s"), ("technicals", "tech_s"), ("risk", "risk_s")]:
                sig_long_rows.append({
                    "security_id": sec_id,
                    "as_of": d,
                    "agent": a,
                    "score": r[s_col],
                })
        signals_long = pd.DataFrame(sig_long_rows)
        outcomes_all = compute_outcomes(prices_long, signals_long, horizon=cfg.horizon)

        # 3. Phase: Folds (0.30)
        await ctx.set_progress(0.30, phase="Constructing walk-forward folds and fitting models")
        # First date with >= 50% universe signals
        first_signal_idx = 0
        for idx_d, d_val in enumerate(trading_dates):
            cnt = len(signals_wide[signals_wide["date"] == d_val])
            if cnt >= (0.5 * len(sec_ids)):
                first_signal_idx = idx_d
                break

        folds = make_folds(trading_dates, cfg, first_signal_idx=first_signal_idx)
        if not folds:
            err_msg = "Insufficient history to generate walk-forward folds with specified parameters."
            await backtests.update_status(db, backtest_id, status="failed", error=err_msg)
            await db.commit()
            raise RuntimeError(err_msg)

        fold_data: Dict[int, Dict[str, Any]] = {}
        folds_by_start: Dict[date, Dict[str, Any]] = {}

        for f in folds:
            # Training outcomes realized <= f.train_end
            if not outcomes_all.empty:
                train_outcomes = outcomes_all[
                    (outcomes_all["as_of"] >= f.train_start)
                    & (outcomes_all["as_of"] <= f.train_end)
                    & (outcomes_all["realized_on"] <= f.train_end)
                ]
            else:
                train_outcomes = pd.DataFrame()

            weights, wmetrics = fit_weights(train_outcomes, cutoff=f.train_end)

            # Build calibration dataset on train window
            train_sig_wide = signals_wide[
                (signals_wide["date"] >= f.train_start)
                & (signals_wide["date"] <= f.train_end)
            ]
            cal_dataset = build_calibration_dataset(train_sig_wide, prices_long, weights, horizon=cfg.horizon)
            calibrator = fit_calibrator(cal_dataset, cutoff=f.train_end)

            f_info = {
                "weights": weights,
                "calibrator": calibrator,
                "metrics": {**wmetrics, "n_calibration": len(cal_dataset)},
            }
            fold_data[f.idx] = f_info
            folds_by_start[f.test_start] = f_info

        # Stitched test trading dates across all folds
        test_dates = [d for d in trading_dates if folds[0].test_start <= d <= folds[-1].test_end]

        # 4. Phase: Simulate (0.30 - 0.80)
        await ctx.set_progress(0.40, phase="Simulating strategy execution")
        engine_results: Dict[str, EngineResult] = {}

        # Precompute decisions map for all test dates
        signals_indexed = {(int(r["security_id"]), r["date"]): r.to_dict() for _, r in signals_wide.iterrows()}

        # Active strategies to run
        strategies_to_run = [s for s in cfg.strategies if s not in BENCHMARK_KEYS]

        for s_idx, strat_key in enumerate(strategies_to_run):
            decider = get_decider(strat_key)
            decider.min_calibrated_confidence = cfg.min_calibrated_confidence

            # Precompute decisions per date
            decisions_by_date: Dict[date, Dict[int, Decision]] = {}
            # Update fold weights as we cross fold boundaries
            curr_fold_idx = 0
            for d in test_dates:
                if d in folds_by_start:
                    decider.set_fold(folds_by_start[d])

                day_dec: Dict[int, Decision] = {}
                for sec_id in sec_ids:
                    row_data = signals_indexed.get((sec_id, d))
                    if row_data:
                        day_dec[sec_id] = decider.decide(row_data)
                decisions_by_date[d] = day_dec

            # Run engine
            engine = PortfolioEngine(
                prices_long=prices_long,
                dates=test_dates,
                decider=decider,
                cfg=cfg,
                symbol_map=symbol_map,
                delisted_on=delisted_dict,
                folds_map=folds_by_start,
            )
            res = await asyncio.to_thread(engine.simulate, decisions_by_date)
            engine_results[strat_key] = res

            prog = 0.40 + 0.35 * ((s_idx + 1) / len(strategies_to_run))
            await ctx.set_progress(prog, phase=f"Simulated {strat_key}")

        # Simulate Benchmarks
        await ctx.set_progress(0.78, phase="Simulating benchmark strategies")
        # 1. Equal-weight benchmark
        eq_bench_res = await asyncio.to_thread(
            simulate_bh_equal_weight,
            prices_long=prices_long,
            dates=test_dates,
            cfg=cfg,
            symbol_map=symbol_map,
        )
        engine_results["bh_equal_weight"] = eq_bench_res

        # 2. NEPSE Index benchmark
        idx_bench_res = simulate_bh_nepse_index(
            index_df=index_df,
            dates=test_dates,
            initial_capital=cfg.initial_capital,
        )
        if idx_bench_res is not None:
            engine_results["bh_nepse_index"] = idx_bench_res

        # 5. Phase: Metrics & Evaluation (0.85)
        await ctx.set_progress(0.85, phase="Computing performance metrics and bootstrap statistics")
        metrics_map: Dict[str, Dict[str, Any]] = {}
        bootstrap_map: Dict[str, Dict[str, Any]] = {}

        # Benchmark returns for bootstrap
        bh_eq_curve = engine_results["bh_equal_weight"].equity
        prev_eq_bench = pd.concat([pd.Series([cfg.initial_capital]), bh_eq_curve["equity"].iloc[:-1].reset_index(drop=True)])
        r_bench = (bh_eq_curve["equity"].values / prev_eq_bench.values) - 1.0

        for strat_key, eng_res in engine_results.items():
            is_bm = strat_key in BENCHMARK_KEYS
            eq_curve = eng_res.equity
            prev_eq = pd.concat([pd.Series([cfg.initial_capital]), eq_curve["equity"].iloc[:-1].reset_index(drop=True)])
            r_strat = (eq_curve["equity"].values / prev_eq.values) - 1.0

            strat_metrics = compute_metrics(
                equity_series=eq_curve["equity"],
                exposure_series=eq_curve["exposure"],
                initial_capital=cfg.initial_capital,
                rf_annual=cfg.rf_annual,
                trades=eng_res.trades,
                turnover_value=eng_res.turnover_value,
                is_benchmark=is_bm,
            )

            # Bootstrap for non-benchmarks
            if not is_bm and len(r_strat) == len(r_bench):
                b_res = paired_block_bootstrap(
                    r_strategy=r_strat,
                    r_bench=r_bench,
                    n=cfg.bootstrap_samples,
                    block=cfg.bootstrap_block,
                    rf_annual=cfg.rf_annual,
                    seed=cfg.seed,
                )
                bootstrap_map[strat_key] = b_res

            # Extra metrics for 'full'
            if strat_key == "full":
                # Per-symbol breakdown
                per_sym_list = []
                for sec_id, sym in symbol_map.items():
                    sec_trades = [tr for tr in eng_res.trades if tr.security_id == sec_id]
                    n_tr = len(sec_trades)
                    net_pnl = sum(tr.net_pnl for tr in sec_trades)
                    w_rate = (sum(1 for tr in sec_trades if tr.net_pnl > 0) / n_tr) if n_tr > 0 else 0.0
                    avg_ret = float(np.mean([tr.return_pct for tr in sec_trades])) if n_tr > 0 else 0.0
                    
                    # Buy-and-hold return for symbol over test period
                    p_sub = prices_long[prices_long["security_id"] == sec_id].sort_values("date")
                    if not p_sub.empty:
                        first_row = p_sub.iloc[0]
                        last_row = p_sub.iloc[-1]
                        o_start = float(first_row["raw_open"] * first_row.get("adj_factor", 1.0))
                        c_end = float(last_row["raw_close"] * last_row.get("adj_factor", 1.0))
                        bh_sym_ret = (c_end / o_start - 1.0) if o_start > 0 else 0.0
                    else:
                        bh_sym_ret = 0.0

                    per_sym_list.append({
                        "symbol": sym,
                        "n_trades": n_tr,
                        "net_pnl": round(net_pnl, 2),
                        "win_rate": round(w_rate, 4),
                        "avg_return": round(avg_ret, 4),
                        "buy_hold_return": round(bh_sym_ret, 4),
                    })
                strat_metrics["per_symbol"] = per_sym_list

                # Data coverage: confidence >= MIN_ACTIVE_CONF
                total_cells = len(signals_wide[signals_wide["date"].isin(test_dates)])
                cov_dict = {}
                for a_name, c_col in [("news", "news_c"), ("fundamentals", "fund_c"), ("technicals", "tech_c")]:
                    active_cnt = (signals_wide[c_col] >= 0.2).sum()
                    cov_dict[a_name] = round(float(active_cnt / max(1, total_cells)), 4)
                strat_metrics["data_coverage"] = cov_dict

                # Calibration evaluation
                cal_rows = []
                # Map decisions on test dates
                for d in test_dates:
                    dec_d = decisions_by_date.get(d, {})
                    for sec_id, decision in dec_d.items():
                        if decision.label in ("BUY", "SELL"):
                            # Find resolved outcome
                            out_sub = outcomes_all[
                                (outcomes_all["security_id"] == sec_id)
                                & (outcomes_all["as_of"] == d)
                                & (outcomes_all["agent"] == "technicals")  # use any to get hit/return
                            ]
                            if not out_sub.empty:
                                o_row = out_sub.iloc[0]
                                hit_val = (decision.score * o_row["forward_return"] > 0)
                                cal_rows.append({
                                    "raw_confidence": decision.score,
                                    "calibrated_confidence": decision.calibrated_conf or 0.0,
                                    "hit": hit_val,
                                })
                strat_metrics["calibration"] = evaluate_calibration(cal_rows)

            metrics_map[strat_key] = strat_metrics

        # 6. Phase: Persist (0.95)
        await ctx.set_progress(0.95, phase="Persisting results to database")
        summary: Dict[str, Any] = {}
        for k, m in metrics_map.items():
            summary[k] = {
                "sharpe": m.get("sharpe"),
                "cagr": m.get("cagr"),
                "max_drawdown": m.get("max_drawdown"),
                "total_return": m.get("total_return"),
            }
        if "bh_nepse_index" not in engine_results:
            summary["bh_nepse_index_unavailable"] = True

        await persist_backtest_results(
            db=db,
            backtest_id=backtest_id,
            results=engine_results,
            metrics_map=metrics_map,
            bootstrap_map=bootstrap_map,
            folds=folds,
            fold_data=fold_data,
            summary=summary,
        )

        await ctx.set_progress(1.0, phase="Backtest completed successfully")
        return summary
