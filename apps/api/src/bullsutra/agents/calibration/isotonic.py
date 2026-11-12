"""Isotonic regression calibration for consensus confidence."""
from datetime import date
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from bullsutra.core.constants import (
    CALIBRATION_MIN_SAMPLES,
    FORWARD_HORIZON_DAYS,
    OUTCOME_MIN_ABS_SCORE,
)
from bullsutra.schemas.contracts import AgentSignal
from bullsutra.agents.consensus import run_consensus
from bullsutra.agents.specialists._util import sign

def build_calibration_dataset(
    signals_wide: pd.DataFrame,
    prices_long: pd.DataFrame,
    weights: Dict[str, float],
    horizon: int = FORWARD_HORIZON_DAYS,
) -> pd.DataFrame:
    """Build consensus signals and join with forward returns for calibration.
    
    Columns: security_id, as_of, label, score, raw_confidence, forward_return, realized_on, hit
    """
    if signals_wide.empty or prices_long.empty:
        return pd.DataFrame(columns=[
            "security_id", "as_of", "label", "score", "raw_confidence",
            "forward_return", "realized_on", "hit"
        ])

    grouped_prices = {sec_id: df.sort_values("date").reset_index(drop=True) 
                      for sec_id, df in prices_long.groupby("security_id")}

    records = []

    for _, row in signals_wide.iterrows():
        sec_id = row["security_id"]
        as_of_date = row["as_of"] if "as_of" in row else row["date"]

        if sec_id not in grouped_prices:
            continue
        p_df = grouped_prices[sec_id]
        pos_list = p_df.index[p_df["date"] == as_of_date].tolist()
        if not pos_list:
            continue
        i = pos_list[0]
        if i + horizon >= len(p_df):
            continue

        p_next = p_df.iloc[i + 1]
        p_target = p_df.iloc[i + horizon]

        adj_open_next = float(p_next["raw_open"] * p_next["adj_factor"]) if "adj_factor" in p_next else float(p_next["open"])
        adj_close_target = float(p_target["raw_close"] * p_target["adj_factor"]) if "adj_factor" in p_target else float(p_target["close"])

        if adj_open_next <= 0:
            continue

        fwd_ret = (adj_close_target / adj_open_next) - 1.0
        realized_date = p_target["date"]

        # Build signals dict for run_consensus
        signals = {
            "news": AgentSignal(
                agent="news",
                score=float(row.get("news_s", 0.0) or 0.0),
                confidence=float(row.get("news_c", 0.0) or 0.0),
            ),
            "fundamentals": AgentSignal(
                agent="fundamentals",
                score=float(row.get("fund_s", 0.0) or 0.0),
                confidence=float(row.get("fund_c", 0.0) or 0.0),
            ),
            "technicals": AgentSignal(
                agent="technicals",
                score=float(row.get("tech_s", 0.0) or 0.0),
                confidence=float(row.get("tech_c", 0.0) or 0.0),
            ),
            "risk": AgentSignal(
                agent="risk",
                score=float(row.get("risk_s", 0.5) or 0.5),
                confidence=float(row.get("risk_c", 0.0) or 0.0),
                meta={"components": {"liq": float(row.get("risk_liq", 0.0) or 0.0)}},
            ),
        }

        consensus, _, _ = run_consensus(signals, weights, calibrator=None, debate=True, risk_gate=True)
        
        # Determine hit for BUY / SELL
        label = consensus.label
        if label in ("BUY", "SELL"):
            hit = (sign(consensus.score) == sign(fwd_ret)) if fwd_ret != 0.0 else False
        else:
            hit = None

        records.append({
            "security_id": sec_id,
            "as_of": as_of_date,
            "label": label,
            "score": consensus.score,
            "raw_confidence": consensus.raw_confidence,
            "forward_return": round(fwd_ret, 6),
            "realized_on": realized_date,
            "hit": hit,
        })

    return pd.DataFrame(records)

def fit_calibrator(dataset: pd.DataFrame, cutoff: date) -> Optional[Dict[str, Any]]:
    """Fit isotonic regression model on realized BUY/SELL outcomes."""
    if dataset.empty:
        return None

    df = dataset[
        (dataset["realized_on"] <= cutoff)
        & (dataset["label"].isin(["BUY", "SELL"]))
        & (dataset["hit"].notna())
    ].copy()

    n = len(df)
    if n < CALIBRATION_MIN_SAMPLES:
        return None

    X = df["raw_confidence"].astype(float).values
    y = df["hit"].astype(float).values

    iso = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip")
    iso.fit(X, y)

    # Convert thresholds to serializable python lists
    x_thresh = [float(val) for val in iso.X_thresholds_]
    y_thresh = [float(val) for val in iso.y_thresholds_]

    return {
        "x": x_thresh,
        "y": y_thresh,
        "n": n,
    }

def apply_calibrator(cal: Optional[Dict[str, Any]], raw_confidence: float) -> float:
    """Apply isotonic calibration thresholds to a raw confidence score."""
    if cal is None or not cal.get("x") or not cal.get("y"):
        return float(round(raw_confidence, 4))
    
    x = cal["x"]
    y = cal["y"]
    calibrated = float(np.interp(raw_confidence, x, y))
    return float(round(calibrated, 4))

def reliability_bins(predicted: List[float], observed: List[float]) -> List[Dict[str, Any]]:
    """Compute 10 equal-width reliability bins for confidence calibration."""
    if not predicted or not observed or len(predicted) != len(observed):
        return []

    p_arr = np.array(predicted)
    o_arr = np.array(observed)
    bins = []

    # 10 equal-width bins over [0, 1]
    edges = np.linspace(0.0, 1.0, 11)
    for i in range(10):
        lo = edges[i]
        hi = edges[i + 1]
        if i == 9:
            mask = (p_arr >= lo) & (p_arr <= hi)
        else:
            mask = (p_arr >= lo) & (p_arr < hi)

        n = int(np.sum(mask))
        if n >= 5:
            bins.append({
                "predicted": round(float(np.mean(p_arr[mask])), 4),
                "observed": round(float(np.mean(o_arr[mask])), 4),
                "count": n,
            })

    return bins
