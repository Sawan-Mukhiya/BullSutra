"""Report generation and export for backtest results."""
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bullsutra.db.models.backtests import (
    BacktestRun,
    BacktestStrategyResult,
    BacktestEquity,
    BacktestTrade,
    BacktestFold,
)
from bullsutra.backtest.constants import STRATEGY_LABELS, STRATEGY_KEYS

async def export_report(db: AsyncSession, backtest_id: uuid.UUID, out_dir: Path) -> Path:
    """Export complete tabular and chart report package to directory."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch Run Info
    stmt_run = select(BacktestRun).where(BacktestRun.id == backtest_id)
    run = (await db.execute(stmt_run)).scalar_one_or_none()
    if not run:
        raise ValueError(f"Backtest run '{backtest_id}' not found")

    # 2. Fetch Strategy Results
    stmt_strat = select(BacktestStrategyResult).where(BacktestStrategyResult.run_id == backtest_id)
    strat_results = (await db.execute(stmt_strat)).scalars().all()

    # Build Ablation Table
    ablation_rows = []
    per_symbol_data = []
    reliability_data = {}

    for sr in strat_results:
        key = sr.strategy_key
        label = STRATEGY_LABELS.get(key, key)
        m = sr.metrics or {}
        b = sr.bootstrap or {}

        sh_diff = b.get("sharpe_diff", {})
        ci_str = f"[{sh_diff.get('ci_low', 'N/A')}, {sh_diff.get('ci_high', 'N/A')}]" if sh_diff else "N/A"
        p_val = sh_diff.get("p_value", "N/A") if sh_diff else "N/A"

        ablation_rows.append({
            "Strategy": label,
            "Key": key,
            "Total Return": f"{m.get('total_return', 0.0):.2%}" if m.get("total_return") is not None else "N/A",
            "CAGR": f"{m.get('cagr', 0.0):.2%}" if m.get("cagr") is not None else "N/A",
            "Sharpe": f"{m.get('sharpe', 0.0):.2f}" if m.get("sharpe") is not None else "N/A",
            "Max Drawdown": f"{m.get('max_drawdown', 0.0):.2%}" if m.get("max_drawdown") is not None else "N/A",
            "Calmar": f"{m.get('calmar', 0.0):.2f}" if m.get("calmar") is not None else "N/A",
            "Trades": m.get("n_trades", "N/A"),
            "Win Rate": f"{m.get('trade_win_rate', 0.0):.2%}" if m.get("trade_win_rate") is not None else "N/A",
            "Signal Hit Rate": f"{m.get('signal_hit_rate', 0.0):.2%}" if m.get("signal_hit_rate") is not None else "N/A",
            "Sharpe Diff 95% CI vs BH": ci_str,
            "p-value": f"{p_val:.4f}" if isinstance(p_val, float) else p_val,
        })

        if key == "full":
            if "per_symbol" in m:
                per_symbol_data = m["per_symbol"]
            if "calibration" in m:
                reliability_data = m["calibration"]

    # Sort ablation by canonical order
    order_map = {k: idx for idx, k in enumerate(STRATEGY_KEYS)}
    ablation_rows.sort(key=lambda r: order_map.get(r["Key"], 999))
    ablation_df = pd.DataFrame(ablation_rows)
    ablation_df.to_csv(out_dir / "ablation.csv", index=False)

    # Markdown table
    md_content = "# BullSutra Strategy Ablation Report\n\n"
    md_content += ablation_df.drop(columns=["Key"]).to_markdown(index=False)
    md_content += "\n\n*Note: All returns account for transaction costs, SEBON fees, DP charges, and holding taxes.*\n"
    with open(out_dir / "ablation.md", "w", encoding="utf-8") as f:
        f.write(md_content)

    # Per symbol CSV
    if per_symbol_data:
        pd.DataFrame(per_symbol_data).to_csv(out_dir / "per_symbol.csv", index=False)

    # 3. Folds CSV
    stmt_folds = select(BacktestFold).where(BacktestFold.run_id == backtest_id).order_by(BacktestFold.fold_idx.asc())
    folds_rows = (await db.execute(stmt_folds)).scalars().all()
    if folds_rows:
        folds_df = pd.DataFrame([{
            "fold_idx": f.fold_idx,
            "train_start": f.train_start,
            "train_end": f.train_end,
            "test_start": f.test_start,
            "test_end": f.test_end,
            "weights": json.dumps(f.weights),
            "metrics": json.dumps(f.metrics),
        } for f in folds_rows])
        folds_df.to_csv(out_dir / "folds.csv", index=False)

    # 4. Equity Curves & Charts
    stmt_eq = select(BacktestEquity).where(BacktestEquity.run_id == backtest_id).order_by(BacktestEquity.trade_date.asc())
    eq_rows = (await db.execute(stmt_eq)).scalars().all()
    if eq_rows:
        eq_df = pd.DataFrame([{
            "date": pd.to_datetime(r.trade_date),
            "strategy": r.strategy_key,
            "equity": float(r.equity),
            "drawdown": float(r.drawdown),
        } for r in eq_rows])

        # Equity chart
        plt.figure(figsize=(12, 6))
        for strat, group in eq_df.groupby("strategy"):
            lbl = STRATEGY_LABELS.get(strat, strat)
            plt.plot(group["date"], group["equity"], label=lbl, alpha=0.85)
        plt.title("Backtest Equity Curves (Linear Scale, NPR)")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value (NPR)")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize="small")
        plt.tight_layout()
        plt.savefig(out_dir / "equity.png", dpi=200)
        plt.close()

        # Drawdown chart: full vs bh_equal_weight
        plt.figure(figsize=(12, 5))
        for strat in ("full", "bh_equal_weight"):
            sub = eq_df[eq_df["strategy"] == strat]
            if not sub.empty:
                lbl = STRATEGY_LABELS.get(strat, strat)
                plt.plot(sub["date"], sub["drawdown"] * 100.0, label=lbl)
        plt.title("Drawdown Comparison: BullSutra Full vs Equal-Weight Benchmark")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "drawdown.png", dpi=200)
        plt.close()

    # 5. Reliability Calibration Chart
    if reliability_data:
        bins_raw = reliability_data.get("bins_raw", [])
        bins_cal = reliability_data.get("bins_calibrated", [])

        plt.figure(figsize=(7, 7))
        plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
        if bins_raw:
            px = [b["predicted"] for b in bins_raw]
            py = [b["observed"] for b in bins_raw]
            plt.plot(px, py, "s-", color="red", label="Raw Confidence")
        if bins_cal:
            cx = [b["predicted"] for b in bins_cal]
            cy = [b["observed"] for b in bins_cal]
            plt.plot(cx, cy, "o-", color="blue", label="Calibrated Confidence")

        plt.title("Confidence Calibration Reliability Diagram (Brier Score)")
        plt.xlabel("Predicted Confidence")
        plt.ylabel("Observed Frequency (Forward Hit Rate)")
        plt.xlim(0, 1)
        plt.ylim(0, 1)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "reliability.png", dpi=200)
        plt.close()

    # 6. README.txt
    readme_text = f"""BullSutra Walk-Forward Backtest Report
======================================
Run ID: {run.id}
Run Name: {run.name}
Created At: {run.created_at}
Started At: {run.started_at}
Finished At: {run.finished_at}

Configuration Used:
{json.dumps(run.config, indent=2)}

Summary:
{json.dumps(run.summary, indent=2)}
"""
    with open(out_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_text)

    return out_dir
