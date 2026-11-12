"""Database persistence helpers for backtest runs."""
import uuid
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from bullsutra.db.repositories.backtests import (
    update_status,
    insert_strategy_results,
    insert_equity,
    insert_trades,
    insert_folds,
)
from bullsutra.backtest.engine import EngineResult
from bullsutra.backtest.folds import Fold

from bullsutra.backtest.constants import BENCHMARK_KEYS

async def persist_backtest_results(
    db: AsyncSession,
    backtest_id: uuid.UUID,
    results: Dict[str, EngineResult],
    metrics_map: Dict[str, Dict[str, Any]],
    bootstrap_map: Dict[str, Dict[str, Any]],
    folds: List[Fold],
    fold_data: Dict[int, Dict[str, Any]],
    summary: Dict[str, Any],
) -> None:
    """Persist all backtest artifacts in a single database transaction."""
    # 1. Strategy Results
    res_rows = []
    for strat_key, metrics in metrics_map.items():
        res_rows.append({
            "run_id": backtest_id,
            "strategy_key": strat_key,
            "is_benchmark": (strat_key in BENCHMARK_KEYS),
            "metrics": metrics,
            "bootstrap": bootstrap_map.get(strat_key),
        })
    await insert_strategy_results(db, res_rows)

    # 2. Equity Curves
    eq_rows = []
    for strat_key, eng_res in results.items():
        for _, r in eng_res.equity.iterrows():
            eq_rows.append({
                "run_id": backtest_id,
                "strategy_key": strat_key,
                "trade_date": r["date"],
                "equity": r["equity"],
                "exposure": r.get("exposure", 0.0),
                "drawdown": r.get("drawdown", 0.0),
            })
    # Batch insert in chunks of 5000
    for i in range(0, len(eq_rows), 5000):
        await insert_equity(db, eq_rows[i : i + 5000])

    # 3. Trades
    trade_rows = []
    for strat_key, eng_res in results.items():
        for tr in eng_res.trades:
            trade_rows.append({
                "run_id": backtest_id,
                "strategy_key": strat_key,
                "security_id": tr.security_id,
                "entry_date": tr.entry_date,
                "exit_date": tr.exit_date,
                "entry_price": tr.entry_price,
                "exit_price": tr.exit_price,
                "shares": tr.shares,
                "entry_cost": tr.entry_cost,
                "exit_cost": tr.exit_cost,
                "tax": tr.tax,
                "net_pnl": tr.net_pnl,
                "return_pct": tr.return_pct,
                "holding_days": tr.holding_days,
                "exit_reason": tr.exit_reason,
            })
    for i in range(0, len(trade_rows), 5000):
        await insert_trades(db, trade_rows[i : i + 5000])

    # 4. Folds
    fold_rows = []
    for f in folds:
        f_info = fold_data.get(f.idx, {})
        fold_rows.append({
            "run_id": backtest_id,
            "fold_idx": f.idx,
            "train_start": f.train_start,
            "train_end": f.train_end,
            "test_start": f.test_start,
            "test_end": f.test_end,
            "weights": f_info.get("weights", {}),
            "calibrator": f_info.get("calibrator"),
            "metrics": f_info.get("metrics", {}),
        })
    await insert_folds(db, fold_rows)

    # 5. Update Run Status
    await update_status(db, backtest_id, status="succeeded", summary=summary)
    await db.commit()
