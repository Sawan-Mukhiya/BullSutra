"""Research brief assembly."""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import pandas as pd

from bullsutra.core.constants import DISCLAIMER_TEXT
from bullsutra.core.time import cutoff_datetime
from bullsutra.agents.constants import GRAPH_VERSION, LOGIC_VERSION
from bullsutra.schemas.contracts import (
    ResearchBrief,
    BriefMeta,
    AgentSignal,
    Consensus,
    Debate,
    Evidence,
    RiskFlag,
    SourceRef,
)
from bullsutra.marketdata.base import MarketSnapshot

def assemble_brief(
    snap: MarketSnapshot,
    signals: Dict[str, AgentSignal],
    consensus: Consensus,
    debate: Debate,
    weights: Dict[str, float],
    meta_flags: Optional[Dict[str, Any]] = None,
) -> ResearchBrief:
    """Assemble deterministic ResearchBrief before optional LLM narrative synthesis."""
    # 1. Drivers merged: max 5
    # For news, fundamentals, technicals: first 2 drivers
    # For risk: first 2 drivers only if risk.score >= 0.5
    driver_candidates = []
    
    for agent_name in ("news", "fundamentals", "technicals"):
        sig = signals.get(agent_name)
        if sig:
            imp = weights.get(agent_name, 1.0) * sig.confidence * abs(sig.score)
            for idx, driver in enumerate(sig.drivers[:2]):
                # Store (importance, -idx) so sorting by importance descending preserves agent order
                driver_candidates.append((imp, -idx, driver))

    risk_sig = signals.get("risk")
    if risk_sig and risk_sig.score >= 0.5:
        imp = risk_sig.confidence * risk_sig.score
        for idx, driver in enumerate(risk_sig.drivers[:2]):
            driver_candidates.append((imp, -idx, driver))

    driver_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    merged_drivers = [c[2] for c in driver_candidates[:5]]

    # 2. Risks union: max 8, order: risk, technicals, fundamentals, news
    seen_risks = set()
    ordered_risks: List[str] = []
    for agent_name in ("risk", "technicals", "fundamentals", "news"):
        sig = signals.get(agent_name)
        if sig:
            for r in sig.risks:
                if r not in seen_risks:
                    seen_risks.add(r)
                    ordered_risks.append(r)
    final_risks = ordered_risks[:8]

    # 3. Risk flags from signals["risk"].meta["flag_details"]
    risk_flags: List[RiskFlag] = []
    if risk_sig and "flag_details" in risk_sig.meta:
        for fd in risk_sig.meta["flag_details"]:
            risk_flags.append(RiskFlag(
                code=fd["code"],
                severity=fd.get("severity", "medium"),
                message=fd["message"],
            ))

    # 4. Sources
    sources: List[SourceRef] = []
    news_sig = signals.get("news")
    if news_sig and "top_articles" in news_sig.meta:
        for art in news_sig.meta["top_articles"][:5]:
            pub_at = None
            if art.get("published_at"):
                try:
                    pub_at = datetime.fromisoformat(art["published_at"])
                except Exception:
                    pass
            sources.append(SourceRef(
                type="news",
                label=art["title"],
                url=art.get("url"),
                published_at=pub_at,
            ))

    fund_sig = signals.get("fundamentals")
    if fund_sig and "period" in fund_sig.meta and fund_sig.meta["period"].strip():
        sources.append(SourceRef(
            type="fundamental",
            label=fund_sig.meta["period"],
            reported_at=None,
        ))

    price_date = snap.as_of
    if snap.prices is not None and not snap.prices.empty:
        if isinstance(snap.prices.index, (datetime, pd.DatetimeIndex)):
            price_date = snap.prices.index[-1].date() if hasattr(snap.prices.index[-1], "date") else snap.prices.index[-1]
        elif "date" in snap.prices.columns:
            last_d = snap.prices["date"].iloc[-1]
            price_date = last_d.date() if hasattr(last_d, "date") else last_d

    sources.append(SourceRef(
        type="price",
        label=f"NEPSE daily prices through {price_date}",
    ))

    # Meta
    brief_meta = BriefMeta(
        graph_version=GRAPH_VERSION,
        logic_version=LOGIC_VERSION,
        prompt_version=None,
        llm_model=None,
        used_llm=False,
        weights=weights,
        price_date=price_date,
        news_cutoff=cutoff_datetime(snap.as_of),
        generated_at=datetime.now(timezone.utc),
    )

    return ResearchBrief(
        id=str(uuid.uuid4()),
        symbol=snap.symbol,
        company_name=snap.company_name or snap.symbol,
        sector=snap.sector or snap.sector_group,
        as_of=snap.as_of,
        signal=consensus,
        agents=signals,
        debate=debate,
        drivers=merged_drivers,
        risks=final_risks,
        risk_flags=risk_flags,
        sources=sources,
        summary=None,
        meta=brief_meta,
        disclaimer=DISCLAIMER_TEXT,
    )
