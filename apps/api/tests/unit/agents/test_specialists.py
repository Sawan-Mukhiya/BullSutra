"""Tests for individual specialist agents (Technicals, Fundamentals, News, Risk)."""
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from bullsutra.core.constants import NPT
from bullsutra.marketdata.base import MarketSnapshot
from bullsutra.agents.specialists.technicals import technicals_signal
from bullsutra.agents.specialists.fundamentals import fundamentals_signal
from bullsutra.agents.specialists.news import news_signal
from bullsutra.agents.specialists.risk import risk_signal
from bullsutra.agents.specialists import run_numeric_agents

def _make_dummy_prices(n: int = 250, trend: float = 0.0) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    base = 100.0 + np.arange(n) * trend
    df = pd.DataFrame({
        "open": base,
        "high": base * 1.01,
        "low": base * 0.99,
        "close": base,
        "raw_open": base,
        "raw_high": base * 1.01,
        "raw_low": base * 0.99,
        "raw_close": base,
        "volume": np.full(n, 10000.0),
        "turnover": base * 10000.0,
        "adj_factor": np.ones(n),
    }, index=dates)
    return df

def test_technicals_uptrend_downtrend_and_insufficient():
    # 1. Uptrend with breakout and volume expansion
    p_up = _make_dummy_prices(250, trend=0.1)
    # Steady base up to t-2
    # Yesterday t-1: close=150, high=155
    p_up.iloc[-2, p_up.columns.get_loc("close")] = 150.0
    p_up.iloc[-2, p_up.columns.get_loc("raw_close")] = 150.0
    p_up.iloc[-2, p_up.columns.get_loc("high")] = 155.0
    p_up.iloc[-2, p_up.columns.get_loc("raw_high")] = 155.0
    # Today t: massive breakout close=190 > prev 55 high (155), surging volume
    p_up.iloc[-1, p_up.columns.get_loc("close")] = 190.0
    p_up.iloc[-1, p_up.columns.get_loc("raw_close")] = 190.0
    p_up.iloc[-1, p_up.columns.get_loc("high")] = 192.0
    p_up.iloc[-1, p_up.columns.get_loc("raw_high")] = 192.0
    p_up.iloc[-1, p_up.columns.get_loc("volume")] = 50000.0
    
    snap_up = MarketSnapshot(
        symbol="UP", security_id=1, as_of=date(2025, 12, 1),
        prices=p_up, fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_up = technicals_signal(snap_up)
    assert sig_up.score > 0.5
    assert sig_up.confidence > 0.4
    assert len(sig_up.drivers) > 0

    # 2. Downtrend with heavy volume breakdown
    p_down = _make_dummy_prices(250, trend=-0.3)
    p_down.iloc[-5:, p_down.columns.get_loc("volume")] = 50000.0  # heavy selling volume
    snap_down = MarketSnapshot(
        symbol="DOWN", security_id=2, as_of=date(2025, 12, 1),
        prices=p_down, fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_down = technicals_signal(snap_down)
    assert sig_down.score < -0.5
    assert "Price below the 200-day average" in sig_down.risks

    # 3. Insufficient history (< 210 bars)
    p_short = _make_dummy_prices(100)
    snap_short = MarketSnapshot(
        symbol="SHORT", security_id=3, as_of=date(2025, 6, 1),
        prices=p_short, fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_short = technicals_signal(snap_short)
    assert sig_short.score == 0.0
    assert sig_short.confidence == 0.0
    assert "insufficient_history" in sig_short.flags

def test_risk_flags_and_insufficient():
    # 1. Insufficient history (< 60 bars)
    p_short = _make_dummy_prices(30)
    snap_short = MarketSnapshot(
        symbol="RISK_SHORT", security_id=1, as_of=date(2025, 2, 1),
        prices=p_short, fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_short = risk_signal(snap_short)
    assert sig_short.score == 0.5
    assert sig_short.confidence == 0.0
    assert "insufficient_history" in sig_short.flags

    # 2. Illiquid scrip (zero volume)
    p_illiquid = _make_dummy_prices(150)
    p_illiquid["volume"] = 0.0
    p_illiquid["turnover"] = 0.0
    snap_illiquid = MarketSnapshot(
        symbol="ILLIQ", security_id=2, as_of=date(2025, 8, 1),
        prices=p_illiquid, fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_illiquid = risk_signal(snap_illiquid)
    assert "illiquid" in sig_illiquid.flags
    assert sig_illiquid.meta["components"]["liq"] >= 0.8

def test_fundamentals_sector_scoring_and_flags():
    p = _make_dummy_prices(100)
    as_of = date(2025, 10, 1)

    # 1. Bank with high NPL
    fund_bank = pd.DataFrame([{
        "fiscal_year": "081-082",
        "quarter": 4,
        "usable_from": date(2025, 8, 1),
        "eps_annualized": 25.0,
        "eps_ytd": 25.0,
        "bvps": 200.0,
        "roe_annualized": 12.5,
        "npl_pct": 6.2,  # > 5.0 -> risk
        "dividend_pct": 10.0,
    }])
    snap_bank = MarketSnapshot(
        symbol="NABIL", security_id=1, as_of=as_of,
        prices=p, fundamentals=fund_bank, news=pd.DataFrame(), sector_group="bank"
    )
    sig_bank = fundamentals_signal(snap_bank)
    assert any("High non-performing loans" in r for r in sig_bank.risks)

    # 2. Loss making scrip
    fund_loss = pd.DataFrame([{
        "fiscal_year": "081-082",
        "quarter": 4,
        "usable_from": date(2025, 8, 1),
        "eps_annualized": -5.0,
        "eps_ytd": -5.0,
        "bvps": 100.0,
        "roe_annualized": -5.0,
        "npl_pct": 1.0,
        "dividend_pct": 0.0,
    }])
    snap_loss = MarketSnapshot(
        symbol="LOSS", security_id=2, as_of=as_of,
        prices=p, fundamentals=fund_loss, news=pd.DataFrame(), sector_group="hydro"
    )
    sig_loss = fundamentals_signal(snap_loss)
    assert "loss_making" in sig_loss.flags
    assert any("loss making" in r.lower() for r in sig_loss.risks)

    # 3. Stale fundamentals (> 180 days)
    fund_stale = pd.DataFrame([{
        "fiscal_year": "080-081",
        "quarter": 2,
        "usable_from": date(2024, 1, 1), # > 270 days ago
        "eps_annualized": 20.0,
        "bvps": 150.0,
        "roe_annualized": 13.3,
        "npl_pct": 1.5,
        "dividend_pct": 5.0,
    }])
    snap_stale = MarketSnapshot(
        symbol="STALE", security_id=3, as_of=as_of,
        prices=p, fundamentals=fund_stale, news=pd.DataFrame(), sector_group="other"
    )
    sig_stale = fundamentals_signal(snap_stale)
    assert any("Fundamentals are stale" in r for r in sig_stale.risks)

def test_news_decay_shrinkage_and_empty():
    as_of = date(2025, 10, 1)

    # 1. Empty news
    snap_empty = MarketSnapshot(
        symbol="NONEWS", security_id=1, as_of=as_of,
        prices=_make_dummy_prices(50), fundamentals=pd.DataFrame(), news=pd.DataFrame()
    )
    sig_empty = news_signal(snap_empty)
    assert sig_empty.score == 0.0
    assert sig_empty.confidence == 0.0
    assert "no_news" in sig_empty.flags

    # 2. Positive news within window
    news_df = pd.DataFrame([
        {
            "article_id": 101,
            "title": "Strong earnings surge announced",
            "url": "https://example.com/101",
            "source": "sharesansar",
            "published_at": datetime(2025, 10, 1, 12, 0, tzinfo=NPT),
            "sentiment_score": 0.8,
            "relevance": 1.0,
        },
        {
            "article_id": 102,
            "title": "Expansion into new hydro projects",
            "url": "https://example.com/102",
            "source": "bizmandu",
            "published_at": datetime(2025, 9, 28, 10, 0, tzinfo=NPT),
            "sentiment_score": 0.6,
            "relevance": 0.9,
        }
    ])
    snap_news = MarketSnapshot(
        symbol="NEWS", security_id=2, as_of=as_of,
        prices=_make_dummy_prices(50), fundamentals=pd.DataFrame(), news=news_df
    )
    sig_news = news_signal(snap_news)
    assert sig_news.score > 0.4
    assert sig_news.confidence > 0.2
    assert len(sig_news.drivers) == 2

def test_point_in_time_as_of_invariance():
    """Future news or price bars must not leak into the current as_of evaluation."""
    as_of = date(2025, 10, 1)
    base_prices = _make_dummy_prices(250, trend=0.5)

    # News: one article on as_of before 16:00, one article on as_of at 16:05 (future relative to cutoff)
    news_df = pd.DataFrame([
        {
            "article_id": 1,
            "title": "Timely Article",
            "url": "http://a",
            "source": "s1",
            "published_at": datetime(2025, 10, 1, 15, 0, tzinfo=NPT),
            "sentiment_score": 0.7,
            "relevance": 1.0,
        },
        {
            "article_id": 2,
            "title": "Future Leaked Article",
            "url": "http://b",
            "source": "s1",
            "published_at": datetime(2025, 10, 1, 16, 5, tzinfo=NPT),
            "sentiment_score": -0.9,
            "relevance": 1.0,
        }
    ])

    snap = MarketSnapshot(
        symbol="TEST", security_id=1, as_of=as_of,
        prices=base_prices, fundamentals=pd.DataFrame(), news=news_df
    )
    sig_news = news_signal(snap)
    # The negative article published at 16:05 must have been excluded!
    assert sig_news.score > 0.0
    assert not any(d.ref == "article:2" for d in sig_news.drivers)
