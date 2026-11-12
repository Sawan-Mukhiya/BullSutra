import pytest
import pandas as pd
import numpy as np
from bullsutra.agents.indicators import (
    sma, ema, rsi, macd, bbands, atr, volume_sma, compute_indicators
)

def test_sma():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    res = sma(s, 3)
    assert np.isnan(res.iloc[0])
    assert np.isnan(res.iloc[1])
    assert res.iloc[2] == 2.0
    assert res.iloc[3] == 3.0
    assert res.iloc[4] == 4.0

def test_ema():
    s = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    res = ema(s, 3)
    assert not np.isnan(res.iloc[-1])
    assert res.iloc[-1] > 10.0

def test_rsi():
    prices = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0])
    res = rsi(prices, 14)
    assert res.iloc[-1] == 100.0  # Monotonically increasing prices -> RSI = 100

def test_macd():
    prices = pd.Series(np.linspace(100, 150, 40))
    res = macd(prices)
    assert "macd" in res.columns
    assert "signal" in res.columns
    assert "hist" in res.columns
    assert not np.isnan(res["hist"].iloc[-1])

def test_bbands():
    prices = pd.Series(np.linspace(100, 150, 30))
    res = bbands(prices, 20)
    assert "upper" in res.columns
    assert "middle" in res.columns
    assert "lower" in res.columns
    assert res["upper"].iloc[-1] >= res["middle"].iloc[-1] >= res["lower"].iloc[-1]

def test_compute_indicators_unknown_raises():
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0], "volume": [100, 200, 300]})
    with pytest.raises(ValueError, match="Unknown indicator"):
        compute_indicators(df, ["invalid_indicator"])
