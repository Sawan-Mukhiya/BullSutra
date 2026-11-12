"""Fundamentals specialist agent."""
from datetime import date
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from bullsutra.schemas.contracts import AgentSignal, Evidence
from bullsutra.agents.specialists._util import clip, lin
from bullsutra.marketdata.base import MarketSnapshot

# Sector weight configurations: (bad, good, weight)
SECTOR_METRICS: Dict[str, Dict[str, tuple[float, float, float]]] = {
    "bank": {
        "roe": (5.0, 15.0, 0.25),
        "npl": (5.0, 1.5, 0.20),
        "pe": (30.0, 10.0, 0.20),
        "pbv": (3.0, 1.2, 0.15),
        "eps_growth": (-10.0, 20.0, 0.20),
    },
    "hydro": {
        "roe": (2.0, 12.0, 0.20),
        "pe": (60.0, 20.0, 0.25),
        "pbv": (3.5, 1.5, 0.20),
        "eps_growth": (-20.0, 25.0, 0.20),
        "dividend_pct": (0.0, 10.0, 0.15),
    },
    "insurance": {
        "roe": (5.0, 15.0, 0.25),
        "pe": (40.0, 15.0, 0.25),
        "pbv": (4.0, 1.5, 0.20),
        "eps_growth": (-10.0, 20.0, 0.20),
        "dividend_pct": (0.0, 15.0, 0.10),
    },
    "other": {
        "roe": (3.0, 15.0, 0.30),
        "pe": (40.0, 12.0, 0.30),
        "pbv": (4.0, 1.5, 0.20),
        "eps_growth": (-15.0, 20.0, 0.20),
    },
}

def fundamentals_signal(snap: MarketSnapshot) -> AgentSignal:
    """Evaluate fundamental strength from snapshot quarterly reports."""
    fund_df = snap.fundamentals
    if fund_df is None or fund_df.empty:
        return AgentSignal(
            agent="fundamentals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["no_fundamentals"],
            meta={},
        )

    # Sort ascending and get latest
    df = fund_df.sort_values(by=["fiscal_year", "quarter"]).copy()
    latest = df.iloc[-1]
    
    as_of = snap.as_of
    if snap.prices is not None and not snap.prices.empty:
        if "raw_close" in snap.prices.columns:
            price = float(snap.prices["raw_close"].iloc[-1])
        else:
            price = float(snap.prices["close"].iloc[-1])
    else:
        price = 0.0

    # Sector group
    group = snap.sector_group if snap.sector_group in SECTOR_METRICS else "other"
    table = SECTOR_METRICS[group]

    flags = []
    risks = []

    # 1. ROE
    roe_val = getattr(latest, "roe_annualized", None)
    if roe_val is None or pd.isna(roe_val):
        eps_ann = getattr(latest, "eps_annualized", None)
        bvps = getattr(latest, "bvps", None)
        if eps_ann is not None and bvps is not None and bvps > 0:
            roe_val = float(eps_ann / bvps * 100.0)
        else:
            roe_val = None

    # 2. Annualised EPS & PE
    eps_ann = getattr(latest, "eps_annualized", None)
    loss_making = False
    pe_sub = None
    pe_val = None
    if eps_ann is not None and not pd.isna(eps_ann):
        if eps_ann <= 0:
            loss_making = True
            flags.append("loss_making")
            risks.append("Company is loss making on a year to date basis")
            pe_sub = -1.0
            pe_val = 0.0
        elif price > 0:
            pe_val = price / eps_ann

    # 3. PBV
    bvps = getattr(latest, "bvps", None)
    pbv_val = None
    if bvps is not None and not pd.isna(bvps) and bvps > 0 and price > 0:
        pbv_val = price / bvps

    # 4. EPS Growth
    eps_growth_val = None
    latest_q = getattr(latest, "quarter", None)
    latest_fy = getattr(latest, "fiscal_year", None)
    latest_eps_ytd = getattr(latest, "eps_ytd", None)
    if latest_eps_ytd is not None and not pd.isna(latest_eps_ytd):
        # find matching quarter in previous fiscal year
        prev_rows = df[(df["quarter"] == latest_q) & (df["fiscal_year"] != latest_fy)]
        if not prev_rows.empty:
            prev = prev_rows.iloc[-1]
            prev_eps_ytd = getattr(prev, "eps_ytd", None)
            if prev_eps_ytd is not None and not pd.isna(prev_eps_ytd) and prev_eps_ytd > 0:
                eps_growth_val = float((latest_eps_ytd - prev_eps_ytd) / prev_eps_ytd * 100.0)

    # 5. NPL
    npl_val = getattr(latest, "npl_pct", None)
    if pd.isna(npl_val):
        npl_val = None
    npl_unavailable = False
    if group == "bank":
        if npl_val is None:
            npl_unavailable = True
            flags.append("npl_unavailable")
            risks.append("Bank NPL data not available")
        elif npl_val > 5.0:
            risks.append(f"High non-performing loans ({npl_val:.1f}%)")

    # 6. Dividend pct
    div_val = None
    for _, r in df.iloc[::-1].iterrows():
        d = getattr(r, "dividend_pct", None)
        if d is not None and not pd.isna(d):
            div_val = float(d)
            break

    # Calculate sub-scores
    raw_metrics: Dict[str, Optional[float]] = {
        "roe": float(roe_val) if roe_val is not None else None,
        "npl": float(npl_val) if npl_val is not None else None,
        "pe": float(pe_val) if pe_val is not None else None,
        "pbv": float(pbv_val) if pbv_val is not None else None,
        "eps_growth": float(eps_growth_val) if eps_growth_val is not None else None,
        "dividend_pct": float(div_val) if div_val is not None else None,
    }

    sub_scores: Dict[str, float] = {}
    total_table_weight = sum(cfg[2] for cfg in table.values())
    avail_weight = 0.0
    weighted_score_sum = 0.0

    driver_candidates = []

    for metric_name, (bad, good, w) in table.items():
        if metric_name == "pe" and pe_sub is not None:
            sub = pe_sub
            sub_scores["pe"] = sub
            avail_weight += w
            weighted_score_sum += w * sub
            imp = abs(w * sub)
            driver_candidates.append((
                imp,
                Evidence(
                    kind="fundamental",
                    ref="PE",
                    note=f"P/E is negative (loss making)",
                    value=0.0,
                )
            ))
            continue

        val = raw_metrics.get(metric_name)
        if val is not None:
            sub = lin(val, bad, good)
            sub_scores[metric_name] = sub
            avail_weight += w
            weighted_score_sum += w * sub
            
            imp = abs(w * sub)
            strength = "strong" if sub >= 0.5 else ("weak" if sub <= -0.5 else "moderate")
            ref_name = metric_name.upper()
            if metric_name == "dividend_pct":
                ref_name = "DIVIDEND"
            driver_candidates.append((
                imp,
                Evidence(
                    kind="fundamental",
                    ref=ref_name,
                    note=f"{ref_name} is {val:.1f}%, {strength}",
                    value=round(val, 2),
                )
            ))

    if avail_weight == 0.0:
        return AgentSignal(
            agent="fundamentals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["no_available_metrics"],
            meta={},
        )

    score = weighted_score_sum / avail_weight
    coverage = avail_weight / total_table_weight

    # Freshness
    usable_from = getattr(latest, "usable_from", None)
    if isinstance(usable_from, str):
        usable_from = date.fromisoformat(usable_from)
    elif hasattr(usable_from, "date"):
        usable_from = usable_from.date()
    
    if usable_from is not None:
        days = (as_of - usable_from).days
    else:
        days = 100

    if days <= 120:
        freshness = 1.0
    elif 120 < days <= 270:
        freshness = 1.0 - 0.5 * (days - 120) / 150.0
    else:
        freshness = 0.3

    if days > 180:
        risks.append(f"Fundamentals are stale (last report {days} days old)")

    bank_npl_factor = 0.8 if npl_unavailable else 1.0
    confidence = clip(coverage * freshness * bank_npl_factor, 0.0, 1.0)

    # Sort drivers
    driver_candidates.sort(key=lambda x: x[0], reverse=True)
    drivers = [c[1] for c in driver_candidates[:3]]

    meta = {
        "period": f"{getattr(latest, 'fiscal_year', '')} Q{getattr(latest, 'quarter', '')}",
        "announced_at": str(getattr(latest, "announced_at", "")),
        "usable_from": str(getattr(latest, "usable_from", "")),
        "eps_basis": getattr(latest, "eps_basis", "annualized"),
        "metrics": {k: round(v, 4) if v is not None else None for k, v in raw_metrics.items()},
        "sub": {k: round(v, 4) for k, v in sub_scores.items()},
        "coverage": round(coverage, 4),
        "freshness": round(freshness, 4),
    }

    return AgentSignal(
        agent="fundamentals",
        score=float(round(score, 4)),
        confidence=float(round(confidence, 4)),
        drivers=drivers,
        risks=risks,
        flags=flags,
        meta=meta,
    )
