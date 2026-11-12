"""Numeric specialists package."""
import structlog
from typing import Dict
from bullsutra.schemas.contracts import AgentName, AgentSignal
from bullsutra.marketdata.base import MarketSnapshot
from bullsutra.agents.specialists.technicals import technicals_signal
from bullsutra.agents.specialists.fundamentals import fundamentals_signal
from bullsutra.agents.specialists.news import news_signal
from bullsutra.agents.specialists.risk import risk_signal

logger = structlog.get_logger(__name__)

def run_numeric_agents(snap: MarketSnapshot) -> Dict[AgentName, AgentSignal]:
    """Execute all four specialist agents on a market snapshot synchronously."""
    signals: Dict[AgentName, AgentSignal] = {}

    # Technicals
    try:
        signals["technicals"] = technicals_signal(snap)
    except Exception as e:
        logger.exception("technicals_agent_error", symbol=snap.symbol, error=str(e))
        signals["technicals"] = AgentSignal(
            agent="technicals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["agent_error"],
            meta={"error": str(e)},
        )

    # Fundamentals
    try:
        signals["fundamentals"] = fundamentals_signal(snap)
    except Exception as e:
        logger.exception("fundamentals_agent_error", symbol=snap.symbol, error=str(e))
        signals["fundamentals"] = AgentSignal(
            agent="fundamentals",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["agent_error"],
            meta={"error": str(e)},
        )

    # News
    try:
        signals["news"] = news_signal(snap)
    except Exception as e:
        logger.exception("news_agent_error", symbol=snap.symbol, error=str(e))
        signals["news"] = AgentSignal(
            agent="news",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["agent_error"],
            meta={"error": str(e)},
        )

    # Risk
    try:
        signals["risk"] = risk_signal(snap)
    except Exception as e:
        logger.exception("risk_agent_error", symbol=snap.symbol, error=str(e))
        signals["risk"] = AgentSignal(
            agent="risk",
            score=0.5,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["agent_error"],
            meta={"error": str(e), "components": {}, "raw": {}, "flag_details": []},
        )

    return signals

__all__ = [
    "run_numeric_agents",
    "technicals_signal",
    "fundamentals_signal",
    "news_signal",
    "risk_signal",
]
