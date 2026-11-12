"""LangGraph agent brief state schema."""
from datetime import date
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from bullsutra.schemas.contracts import (
    AgentSignal,
    Consensus,
    DebateRound,
    CrossCheck,
    ResearchBrief,
)
from bullsutra.agents.consensus import Voter
from bullsutra.marketdata.base import MarketSnapshot

def merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    return {**(a or {}), **(b or {})}

class BriefState(TypedDict, total=False):
    security_id: int
    symbol: str
    as_of: date
    use_llm: bool
    snapshot: MarketSnapshot
    weights: Dict[str, float]
    calibrator: Optional[Dict[str, Any]]
    signals: Annotated[Dict[str, AgentSignal], merge_dict]
    voters: Dict[str, Voter]
    cross_checks: List[CrossCheck]
    debate_rounds: List[DebateRound]
    initial_disagreement: float
    disagreement: float
    consensus: Consensus
    brief: ResearchBrief
    brief_id: str
    active: List[str]
