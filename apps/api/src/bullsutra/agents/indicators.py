import pandas as pd
import numpy as np
from typing import Dict, List, Union

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    res = 100.0 - (100.0 / (1.0 + rs))
    # where avg_loss == 0 set rsi = 100
    res = res.where(avg_loss != 0, 100.0)
    return res

def macd(close: pd.Series) -> pd.DataFrame:
    fast = ema(close, 12)
    slow = ema(close, 26)
    macd_line = fast - slow
    signal = macd_line.ewm(span=9, adjust=False, min_periods=9).mean()
    hist = macd_line - signal
    return pd.DataFrame({"macd": macd_line, "signal": signal, "hist": hist}, index=close.index)

def bbands(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    middle = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    upper = middle + k * sd
    lower = middle - k * sd
    return pd.DataFrame({"upper": upper, "middle": middle, "lower": lower}, index=close.index)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev).abs()
    tr3 = (low - prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()

def volume_sma(volume: pd.Series, n: int = 20) -> pd.Series:
    return sma(volume, n)

ALLOWED_INDICATORS = {
    "sma20", "sma50", "sma200", "ema12", "ema26",
    "rsi14", "macd", "bbands20", "atr14", "volume_sma20"
}

def compute_indicators(prices: pd.DataFrame, names: List[str]) -> Dict[str, Union[pd.DataFrame, pd.Series]]:
    for name in names:
        if name not in ALLOWED_INDICATORS:
            raise ValueError(f"Unknown indicator '{name}'. Allowed: {sorted(ALLOWED_INDICATORS)}")
    
    close = prices["close"]
    high = prices["high"] if "high" in prices.columns else close
    low = prices["low"] if "low" in prices.columns else close
    volume = prices["volume"] if "volume" in prices.columns else pd.Series(0, index=close.index)

    out = {}
    for name in names:
        if name == "sma20":
            out["sma20"] = sma(close, 20)
        elif name == "sma50":
            out["sma50"] = sma(close, 50)
        elif name == "sma200":
            out["sma200"] = sma(close, 200)
        elif name == "ema12":
            out["ema12"] = ema(close, 12)
        elif name == "ema26":
            out["ema26"] = ema(close, 26)
        elif name == "rsi14":
            out["rsi14"] = rsi(close, 14)
        elif name == "macd":
            out["macd"] = macd(close)
        elif name == "bbands20":
            out["bbands20"] = bbands(close, 20, 2.0)
        elif name == "atr14":
            out["atr14"] = atr(high, low, close, 14)
        elif name == "volume_sma20":
            out["volume_sma20"] = volume_sma(volume, 20)

    return out
