"""Risk specialist agent."""
from typing import Dict, Any, List, Optional
import math
import numpy as np
import pandas as pd

from bullsutra.core.constants import MIN_BARS_RISK, get_circuit_limit_pct
from bullsutra.schemas.contracts import AgentSignal, Evidence, RiskFlag
from bullsutra.agents.specialists._util import clip, lin01
from bullsutra.marketdata.base import MarketSnapshot

RISK_WEIGHTS = {
    "vol": 0.30,
    "dd": 0.20,
    "liq": 0.25,
    "circ": 0.10,
    "gap": 0.15,
}

def _prep_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    if "close" not in df.columns:
        if "raw_close" in df.columns and "adj_factor" in df.columns:
            df["close"] = df["raw_close"] * df["adj_factor"]
            df["open"] = df.get("raw_open", df["raw_close"]) * df["adj_factor"]
        elif "raw_close" in df.columns:
            df["close"] = df["raw_close"]
            df["open"] = df.get("raw_open", df["raw_close"])
    if "raw_close" not in df.columns:
        df["raw_close"] = df["close"]
    if "raw_open" not in df.columns:
        df["raw_open"] = df.get("open", df["close"])
    if "volume" not in df.columns:
        df["volume"] = 0.0
    if "turnover" not in df.columns:
        df["turnover"] = df["raw_close"] * df["volume"]
    return df

def risk_series(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute risk metrics across all rows vectorised.
    
    Required columns: score, confidence, insufficient, c_vol, c_dd, c_liq, c_circ, c_gap.
    """
    df = _prep_price_frame(prices)
    n = len(df)
    
    cols = ["score", "confidence", "insufficient", "c_vol", "c_dd", "c_liq", "c_circ", "c_gap"]
    res = pd.DataFrame(index=df.index, columns=cols)
    res["score"] = 0.5
    res["confidence"] = 0.0
    res["insufficient"] = True
    for c in ["c_vol", "c_dd", "c_liq", "c_circ", "c_gap"]:
        res[c] = 0.0

    if n < MIN_BARS_RISK:
        return res

    close = df["close"]
    raw_close = df["raw_close"]
    raw_open = df["raw_open"]
    volume = df["volume"]
    turnover = df["turnover"]

    # 1. vol: 60-day std of adjusted returns * sqrt(240)
    ret_1d = close.pct_change()
    vol60 = ret_1d.rolling(60, min_periods=60).std(ddof=1) * math.sqrt(240)
    c_vol = (vol60 - 0.15) / (0.60 - 0.15)
    c_vol = c_vol.clip(0.0, 1.0).fillna(0.0)

    # 2. dd: 1 - close / max(close over last 120 bars, min 60)
    roll_max = close.rolling(120, min_periods=60).max()
    depth = 1.0 - (close / roll_max)
    c_dd = (depth - 0.05) / (0.35 - 0.05)
    c_dd = c_dd.clip(0.0, 1.0).fillna(0.0)

    # 3. liq: median turnover over 60 bars, zero trades fraction
    med_turnover = turnover.rolling(60, min_periods=60).median().clip(lower=1.0)
    log_med = np.log10(med_turnover)
    liq_turnover_score = 1.0 - ((log_med - math.log10(1e6)) / (math.log10(2e7) - math.log10(1e6))).clip(0.0, 1.0)
    zero_vol = (volume == 0).astype(float)
    zero_frac = zero_vol.rolling(60, min_periods=60).mean()
    liq_zero_score = ((zero_frac - 0.0) / (0.3 - 0.0)).clip(0.0, 1.0)
    c_liq = np.maximum(liq_turnover_score, liq_zero_score).fillna(0.0)

    # 4. circ: number of last 20 bars hitting regime limit
    # Determine limit_pct per date
    if isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
    elif "date" in df.columns:
        dates = pd.to_datetime(df["date"]).dt.date
    else:
        dates = [None] * n

    limits = np.array([get_circuit_limit_pct(d) if d is not None else 0.10 for d in dates])
    hits_series = pd.Series(0.0, index=df.index)
    if "hit_upper" in df.columns and "hit_lower" in df.columns:
        circuit_hit = (df["hit_upper"] == True) | (df["hit_lower"] == True)
        hits_series = circuit_hit.astype(float)
    else:
        abs_ret = ret_1d.abs()
        circuit_hit = abs_ret >= (pd.Series(limits, index=df.index) * 0.95)
        hits_series = circuit_hit.astype(float)
    
    hits_20 = hits_series.rolling(20, min_periods=20).sum()
    c_circ = (hits_20 / 4.0).clip(0.0, 1.0).fillna(0.0)

    # 5. gap: fraction of last 60 bars with abs(raw_open / prev_close - 1) >= 0.03
    prev_close = df["prev_close_exchange"] if "prev_close_exchange" in df.columns else raw_close.shift(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        gap_ratio = (raw_open / prev_close - 1.0).abs()
        is_gap = (gap_ratio >= 0.03).astype(float)
    gap_freq = is_gap.rolling(60, min_periods=60).mean()
    c_gap = ((gap_freq - 0.05) / (0.30 - 0.05)).clip(0.0, 1.0).fillna(0.0)

    # Combined score
    score = (
        RISK_WEIGHTS["vol"] * c_vol
        + RISK_WEIGHTS["dd"] * c_dd
        + RISK_WEIGHTS["liq"] * c_liq
        + RISK_WEIGHTS["circ"] * c_circ
        + RISK_WEIGHTS["gap"] * c_gap
    )

    # confidence: min(1, bars / 120)
    bars_count = np.arange(1, n + 1)
    confidence = np.minimum(1.0, bars_count / 120.0)

    mask_suff = np.arange(n) >= (MIN_BARS_RISK - 1)
    res["score"] = np.where(mask_suff, score.round(4), 0.5)
    res["confidence"] = np.where(mask_suff, np.round(confidence, 4), 0.0)
    res["insufficient"] = ~mask_suff
    res["c_vol"] = np.where(mask_suff, c_vol.round(4), 0.0)
    res["c_dd"] = np.where(mask_suff, c_dd.round(4), 0.0)
    res["c_liq"] = np.where(mask_suff, c_liq.round(4), 0.0)
    res["c_circ"] = np.where(mask_suff, c_circ.round(4), 0.0)
    res["c_gap"] = np.where(mask_suff, c_gap.round(4), 0.0)
    return res

def risk_signal(snap: MarketSnapshot) -> AgentSignal:
    """Generate risk AgentSignal from a MarketSnapshot."""
    prices = snap.prices
    if prices is None or len(prices) < MIN_BARS_RISK:
        return AgentSignal(
            agent="risk",
            score=0.5,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["insufficient_history"],
            meta={"components": {}, "raw": {}, "flag_details": []},
        )

    series_df = risk_series(prices)
    last_row = series_df.iloc[-1]
    
    if last_row["insufficient"]:
        return AgentSignal(
            agent="risk",
            score=0.5,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["insufficient_history"],
            meta={"components": {}, "raw": {}, "flag_details": []},
        )

    df = _prep_price_frame(prices)
    close = df["close"]
    raw_close = df["raw_close"]
    raw_open = df["raw_open"]
    volume = df["volume"]
    turnover = df["turnover"]

    # Compute raw values for drivers and messages
    ret_1d = close.pct_change()
    vol60_val = float(ret_1d.iloc[-60:].std(ddof=1) * math.sqrt(240)) if len(ret_1d) >= 60 else 0.0
    
    roll_max_120 = float(close.iloc[-min(120, len(close)):].max())
    close_curr = float(close.iloc[-1])
    depth_val = 1.0 - (close_curr / roll_max_120) if roll_max_120 > 0 else 0.0

    med_turnover_val = float(turnover.iloc[-60:].median()) if len(turnover) >= 60 else 0.0
    zero_val = float((volume.iloc[-60:] == 0).mean()) if len(volume) >= 60 else 0.0

    # circuit hits
    prev_close = df["prev_close_exchange"] if "prev_close_exchange" in df.columns else raw_close.shift(1)
    if "hit_upper" in df.columns and "hit_lower" in df.columns:
        circuit_hit = (df["hit_upper"] == True) | (df["hit_lower"] == True)
    else:
        circuit_hit = ret_1d.abs() >= (0.10 * 0.95)
    hits_val = int(circuit_hit.iloc[-20:].sum())

    gap_ratio = (raw_open / prev_close - 1.0).abs()
    gap_freq_val = float((gap_ratio.iloc[-60:] >= 0.03).mean()) if len(gap_ratio) >= 60 else 0.0

    components = {
        "vol": float(last_row["c_vol"]),
        "dd": float(last_row["c_dd"]),
        "liq": float(last_row["c_liq"]),
        "circ": float(last_row["c_circ"]),
        "gap": float(last_row["c_gap"]),
    }

    raw = {
        "vol60": round(vol60_val, 4),
        "drawdown120": round(depth_val, 4),
        "median_turnover60": round(med_turnover_val, 2),
        "zero_vol_pct": round(zero_val, 4),
        "circuit20": hits_val,
        "gap60": round(gap_freq_val, 4),
    }

    # Flag templates
    msg_templates = {
        "vol": f"Annualised volatility is {vol60_val:.0%}",
        "dd": f"Price is {depth_val:.0%} below its 120-day high",
        "liq": f"Median daily turnover is NPR {med_turnover_val:,.0f}; {zero_val:.0%} of days had no trades",
        "circ": f"{hits_val} of the last 20 days hit the circuit limit (regime-aware)",
        "gap": f"{gap_freq_val:.0%} of recent days opened with a gap of 3% or more",
    }
    flag_code_map = {
        "vol": "high_volatility",
        "dd": "deep_drawdown",
        "liq": "illiquid",
        "circ": "frequent_circuit_hits",
        "gap": "frequent_gaps",
    }

    flags = []
    flag_details = []
    for k, val in components.items():
        if val >= 0.6:
            code = flag_code_map[k]
            flags.append(code)
            severity = "high" if val >= 0.85 else ("medium" if val >= 0.7 else "low")
            flag_details.append({
                "code": code,
                "severity": severity,
                "message": msg_templates[k],
            })

    # Microstructure & floorsheet context
    floorsheet_meta = {}
    if snap.floorsheet_agg is not None and not snap.floorsheet_agg.empty:
        fs = snap.floorsheet_agg.iloc[-1]
        top5_b = float(fs.get("top5_buyer_share", 0.0) or 0.0)
        top5_s = float(fs.get("top5_seller_share", 0.0) or 0.0)
        b_hhi = float(fs.get("buyer_hhi", 0.0) or 0.0)
        s_hhi = float(fs.get("seller_hhi", 0.0) or 0.0)
        block_share = float(fs.get("block_share", 0.0) or 0.0)
        floorsheet_meta["block_share"] = block_share

        max_share = max(top5_b, top5_s)
        if max_share >= 0.40 or b_hhi > 2000 or s_hhi > 2000:
            flags.append("broker_concentration")
            flag_details.append({
                "code": "broker_concentration",
                "severity": "high" if max_share >= 0.60 else "medium",
                "message": f"Top 5 brokers control {max_share:.0%} of trading volume",
            })

    # Drivers: top 3 components by abs(weight * component)
    raw_ref_map = {
        "vol": ("vol60", vol60_val),
        "dd": ("drawdown120", depth_val),
        "liq": ("median_turnover60", med_turnover_val),
        "circ": ("circuit20", hits_val),
        "gap": ("gap60", gap_freq_val),
    }

    driver_candidates = []
    for k, comp_val in components.items():
        imp = RISK_WEIGHTS[k] * comp_val
        ref_name, raw_m = raw_ref_map[k]
        driver_candidates.append((
            imp,
            Evidence(
                kind="risk",
                ref=ref_name,
                note=msg_templates[k],
                value=round(raw_m, 4) if isinstance(raw_m, float) else raw_m,
            )
        ))

    driver_candidates.sort(key=lambda x: x[0], reverse=True)
    drivers = [c[1] for c in driver_candidates[:3]]
    risks = [fd["message"] for fd in flag_details]

    meta = {
        "components": components,
        "raw": raw,
        "flag_details": flag_details,
    }
    if floorsheet_meta:
        meta["floorsheet"] = floorsheet_meta

    return AgentSignal(
        agent="risk",
        score=float(last_row["score"]),
        confidence=float(last_row["confidence"]),
        drivers=drivers,
        risks=risks,
        flags=flags,
        meta=meta,
    )
