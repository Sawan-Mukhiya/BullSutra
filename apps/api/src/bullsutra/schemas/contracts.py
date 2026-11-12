from datetime import date, datetime
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

AgentName = Literal["news", "fundamentals", "technicals", "risk"]
Label = Literal["BUY", "HOLD", "SELL"]

class Evidence(BaseModel):
    kind: Literal["price", "indicator", "fundamental", "news", "risk"]
    ref: str                      # short key, e.g. "RSI14", "ROE", "article:12345", "vol60"
    note: str                     # one human-readable sentence
    value: float | str | None = None
    url: str | None = None

class AgentSignal(BaseModel):
    agent: AgentName
    score: float = Field(ge=-1, le=1)         # for risk: 0..1 risk level (see 04)
    confidence: float = Field(ge=0, le=1)
    drivers: list[Evidence] = []              # at most 5, strongest first
    risks: list[str] = []                     # short strings
    flags: list[str] = []                     # machine codes, e.g. "insufficient_history"
    narrative: str | None = None              # LLM text, live only
    meta: dict[str, Any] = {}                 # sub-scores etc.

class DebateRevision(BaseModel):
    agent: Literal["news", "fundamentals", "technicals"]
    score_before: float
    score_after: float
    confidence_before: float
    confidence_after: float
    others_mean: float | None

class DebateRound(BaseModel):
    round: int
    disagreement_before: float
    revisions: list[DebateRevision]
    disagreement_after: float

class CrossCheck(BaseModel):
    rule: Literal["R1", "R2"]
    message: str
    agent_affected: AgentName

class Debate(BaseModel):
    triggered: bool
    initial_disagreement: float
    final_disagreement: float
    cross_checks: list[CrossCheck] = []
    rounds: list[DebateRound] = []
    summary: str | None = None                # LLM text, live only

class Consensus(BaseModel):
    label: Label
    score: float
    raw_confidence: float
    confidence: float                          # calibrated
    position_multiplier: float                 # 0.2..1.0
    conflicted: bool
    flags: list[str] = []                      # e.g. "insufficient_signal", "illiquid_no_buy", "risk_damped"

class RiskFlag(BaseModel):
    code: str                                  # e.g. "illiquid", "high_volatility"
    severity: Literal["low", "medium", "high"]
    message: str

class SourceRef(BaseModel):
    type: Literal["news", "fundamental", "price"]
    label: str
    url: str | None = None
    published_at: datetime | None = None       # news
    reported_at: date | None = None            # fundamentals

class BriefMeta(BaseModel):
    graph_version: str                         # constant "1.0.0"
    logic_version: str                         # constant "1.0.0"
    prompt_version: str | None                 # "v1" or null when LLM unused
    llm_model: str | None
    used_llm: bool
    weights: dict[str, float]
    price_date: date                           # last bar used
    news_cutoff: datetime
    generated_at: datetime

class ResearchBrief(BaseModel):
    id: str
    symbol: str
    company_name: str
    sector: str
    as_of: date
    signal: Consensus
    agents: dict[AgentName, AgentSignal]
    debate: Debate
    drivers: list[Evidence]                    # up to 5 merged
    risks: list[str]
    risk_flags: list[RiskFlag]
    sources: list[SourceRef]
    summary: str | None
    meta: BriefMeta
    disclaimer: str
