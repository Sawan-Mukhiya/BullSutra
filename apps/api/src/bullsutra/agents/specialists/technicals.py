"""Technicals specialist agent."""
from typing import Dict, Any, List
import numpy as np
import pandas as pd

from bullsutra.core.constants import MIN_BARS_SIGNALS
from bullsutra.schemas.contracts import AgentSignal, Evidence
from bullsutra.agents.indicators import sma, rsi as calc_rsi, macd as calc_macd, atr as calc_atr
from bullsutra.agents.specialists._util import clip, sign
from bullsutra.marketdata.base import MarketSnapshot

SUB_WEIGHTS = {
    "trend": 0.30,
    "macd": 0.20,
    "rsi": 0.15,
    "breakout": 0.20,
    "volume": 0.15,
}

def _prep_price_frame(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    if "close" not in df.columns:
        if "raw_close" in df.columns and "adj_factor" in df.columns:
            df["close"] = df["raw_close"] * df["adj_factor"]
            df["open"] = df["raw_open"] * df["adj_factor"]
            df["high"] = df["raw_high"] * df["adj_factor"]
            df["low"] = df["raw_low"] * df["adj_factor"]
        elif "raw_close" in df.columns:
            df["close"] = df["raw_close"]
            df["open"] = df.get("raw_open", df["raw_close"])
            df["high"] = df.get("raw_high", df["raw_close"])
            df["low"] = df.get("raw_low", df["raw_close"])
    if "high" not in df.columns:
        df["high"] = df["close"]
    if "low" not in df.columns:
        df["low"] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df

def technicals_series(prices: pd.DataFrame) -> pd.DataFrame:
    """Compute technicals series vectorised across all rows.
    
    Required output columns: score, confidence, insufficient (bool).
    """
    df = _prep_price_frame(prices)
    n = len(df)
    
    res = pd.DataFrame(index=df.index)
    res["score"] = 0.0
    res["confidence"] = 0.0
    res["insufficient"] = True

    if n < MIN_BARS_SIGNALS:
        return res

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    sma50 = sma(close, 50)
    sma200 = sma(close, 200)
    macd_df = calc_macd(close)
    atr14 = calc_atr(high, low, close, 14)
    rsi14 = calc_rsi(close, 14)

    # 1. Trend: 0.5*sign(close - sma50) + 0.5*sign(sma50 - sma200)
    trend = 0.5 * np.sign(close - sma50) + 0.5 * np.sign(sma50 - sma200)
    trend = trend.fillna(0.0)

    # 2. MACD: tanh(hist / atr14) (0 if atr14 is 0 or NaN)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = macd_df["hist"] / atr14
        ratio = ratio.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        sub_macd = np.tanh(ratio)

    # 3. RSI: if >= 70 -> -0.6; if <= 30 -> +0.6; else (rsi14 - 50)/20 * 0.5
    sub_rsi = pd.Series(0.0, index=close.index)
    mask_high = rsi14 >= 70
    mask_low = rsi14 <= 30
    mask_mid = (~mask_high) & (~mask_low) & rsi14.notna()
    sub_rsi[mask_high] = -0.6
    sub_rsi[mask_low] = 0.6
    sub_rsi[mask_mid] = (rsi14[mask_mid] - 50.0) / 20.0 * 0.5
    sub_rsi = sub_rsi.fillna(0.0)

    # 4. Breakout: over previous 55 bars excluding today
    prev_high_55 = high.shift(1).rolling(55, min_periods=55).max()
    prev_low_55 = low.shift(1).rolling(55, min_periods=55).min()
    breakout = pd.Series(0.0, index=close.index)
    breakout[close > prev_high_55] = 1.0
    breakout[close < prev_low_55] = -1.0

    # 5. Volume: clip(ln(vol_sma5 / vol_sma20), -1, 1) * sign(close/close.shift(5) - 1)
    vol_sma5 = sma(volume, 5)
    vol_sma20 = sma(volume, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        v_ratio = vol_sma5 / vol_sma20
        v_log = np.log(v_ratio)
        v_log = v_log.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-1.0, 1.0)
    price_ret_5 = np.sign(close / close.shift(5) - 1.0).fillna(0.0)
    sub_vol = v_log * price_ret_5

    # Aggregate score
    score = (
        SUB_WEIGHTS["trend"] * trend
        + SUB_WEIGHTS["macd"] * sub_macd
        + SUB_WEIGHTS["rsi"] * sub_rsi
        + SUB_WEIGHTS["breakout"] * breakout
        + SUB_WEIGHTS["volume"] * sub_vol
    )

    # Calculate agreement: fraction of non-zero sub-signals sharing sign with score
    subs = pd.DataFrame({
        "trend": trend,
        "macd": sub_macd,
        "rsi": sub_rsi,
        "breakout": breakout,
        "volume": sub_vol,
    })

    score_sign = np.sign(score)
    # Compare signs
    agree_list = []
    for idx, row in subs.iterrows():
        s = score.loc[idx]
        s_sign = score_sign.loc[idx]
        non_zero = [v for v in row if v != 0.0]
        if s == 0.0 or len(non_zero) == 0:
            agree_list.append(0.0)
        else:
            same_sign_count = sum(1 for v in non_zero if np.sign(v) == s_sign)
            agree_list.append(same_sign_count / len(non_zero))

    agree_series = pd.Series(agree_list, index=df.index)
    
    # confidence = clip(0.2 + 0.8 * min(1, abs(score)/0.6) * agree, 0, 1); if score == 0 then 0.2
    conf = pd.Series(0.2, index=df.index)
    non_zero_score = score != 0.0
    conf[non_zero_score] = (
        0.2 + 0.8 * (score[non_zero_score].abs() / 0.6).clip(upper=1.0) * agree_series[non_zero_score]
    ).clip(0.0, 1.0)

    # For indices before MIN_BARS_SIGNALS
    mask_suff = np.arange(n) >= (MIN_BARS_SIGNALS - 1)
    res["score"] = np.where(mask_suff, score.round(4), 0.0)
    res["confidence"] = np.where(mask_suff, conf.round(4), 0.0)
    res["insufficient"] = ~mask_suff
    return res

def technicals_signal(snap: MarketSnapshot) -> AgentSignal:
    """Generate technicals AgentSignal from a MarketSnapshot."""
    prices = snap.prices
    if prices is None or len(prices) < MIN_BARS_SIGNALS:
        return AgentSignal(
            agent="technicals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["insufficient_history"],
            meta={},
        )

    series_df = technicals_series(prices)
    last_row = series_df.iloc[-1]
    
    if last_row["insufficient"]:
        return AgentSignal(
            agent="technicals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["insufficient_history"],
            meta={},
        )

    df = _prep_price_frame(prices)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    sma50_val = float(sma(close, 50).iloc[-1])
    sma200_val = float(sma(close, 200).iloc[-1])
    macd_df = calc_macd(close)
    atr14_val = float(calc_atr(high, low, close, 14).iloc[-1])
    rsi14_val = float(calc_rsi(close, 14).iloc[-1])
    close_val = float(close.iloc[-1])

    sub_trend = 0.5 * sign(close_val - sma50_val) + 0.5 * sign(sma50_val - sma200_val)
    hist_val = float(macd_df["hist"].iloc[-1])
    sub_macd = np.tanh(hist_val / atr14_val) if atr14_val > 0 else 0.0

    if rsi14_val >= 70:
        sub_rsi = -0.6
    elif rsi14_val <= 30:
        sub_rsi = 0.6
    else:
        sub_rsi = (rsi14_val - 50.0) / 20.0 * 0.5

    prev_high_55 = float(high.shift(1).rolling(55, min_periods=55).max().iloc[-1])
    prev_low_55 = float(low.shift(1).rolling(55, min_periods=55).min().iloc[-1])
    if close_val > prev_high_55:
        sub_breakout = 1.0
    elif close_val < prev_low_55:
        sub_breakout = -1.0
    else:
        sub_breakout = 0.0

    vol_sma5 = float(sma(volume, 5).iloc[-1])
    vol_sma20 = float(sma(volume, 20).iloc[-1])
    close_5 = float(close.shift(5).iloc[-1])
    if vol_sma20 > 0 and vol_sma5 > 0 and close_5 > 0:
        sub_vol = clip(np.log(vol_sma5 / vol_sma20), -1.0, 1.0) * sign(close_val / close_5 - 1.0)
    else:
        sub_vol = 0.0

    sub_dict = {
        "trend": float(round(sub_trend, 4)),
        "macd": float(round(sub_macd, 4)),
        "rsi": float(round(sub_rsi, 4)),
        "breakout": float(round(sub_breakout, 4)),
        "volume": float(round(sub_vol, 4)),
    }

    # Drivers: top 3 sub-signals by abs(weight * sub)
    candidates = []
    # trend
    c_above_sma50 = "above" if close_val > sma50_val else "below"
    sma50_above_200 = "above" if sma50_val > sma200_val else "below"
    candidates.append((
        "trend",
        abs(SUB_WEIGHTS["trend"] * sub_trend),
        Evidence(
            kind="indicator",
            ref="SMA50/SMA200",
            note=f"Close is {c_above_sma50} SMA50 and SMA50 is {sma50_above_200} SMA200",
            value=round(sub_trend, 4),
        )
    ))
    # macd
    macd_pos = "positive" if hist_val > 0 else "negative"
    candidates.append((
        "macd",
        abs(SUB_WEIGHTS["macd"] * sub_macd),
        Evidence(
            kind="indicator",
            ref="MACD",
            note=f"MACD histogram is {macd_pos} relative to volatility",
            value=round(sub_macd, 4),
        )
    ))
    # rsi
    rsi_state = "overbought" if rsi14_val >= 70 else ("oversold" if rsi14_val <= 30 else "neutral")
    candidates.append((
        "rsi",
        abs(SUB_WEIGHTS["rsi"] * sub_rsi),
        Evidence(
            kind="indicator",
            ref="RSI14",
            note=f"RSI is {rsi14_val:.0f} ({rsi_state})",
            value=round(rsi14_val, 4),
        )
    ))
    # breakout
    if sub_breakout != 0.0:
        break_dir = "above the 55-day high" if sub_breakout > 0 else "below the 55-day low"
        candidates.append((
            "breakout",
            abs(SUB_WEIGHTS["breakout"] * sub_breakout),
            Evidence(
                kind="indicator",
                ref="Donchian55",
                note=f"Close broke {break_dir}",
                value=round(sub_breakout, 4),
            )
        ))
    # volume
    v_dir = "rising" if vol_sma5 > vol_sma20 else "falling"
    p_dir = "up" if close_val > close_5 else "down"
    candidates.append((
        "volume",
        abs(SUB_WEIGHTS["volume"] * sub_vol),
        Evidence(
            kind="indicator",
            ref="Volume",
            note=f"Volume is {v_dir} versus its 20-day average with price {p_dir} over 5 days",
            value=round(sub_vol, 4),
        )
    ))

    # Stable sort by abs_val descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    drivers = [c[2] for c in candidates[:3]]

    # Risks
    risks = []
    if rsi14_val >= 70:
        risks.append("Overbought: RSI above 70")
    elif rsi14_val <= 30:
        risks.append("Oversold: RSI below 30")
    if close_val < sma200_val:
        risks.append("Price below the 200-day average")

    meta = {
        "sub": sub_dict,
        "rsi": round(rsi14_val, 2),
        "sma50": round(sma50_val, 2),
        "sma200": round(sma200_val, 2),
    }

    return AgentSignal(
        agent="technicals",
        score=float(last_row["score"]),
        confidence=float(last_row["confidence"]),
        drivers=drivers,
        risks=risks,
        flags=[],
        meta=meta,
    )
