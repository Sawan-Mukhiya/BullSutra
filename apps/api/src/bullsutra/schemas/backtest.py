from datetime import date, datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel

class CreateBacktestRequest(BaseModel):
    name: str
    config: Dict[str, Any]

class CreateBacktestResponse(BaseModel):
    status: Literal["queued"] = "queued"
    job_id: str
    backtest_id: str
    events_url: str

class BacktestListItem(BaseModel):
    id: str
    name: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    summary: Optional[Dict[str, Any]] = None

class StrategyResult(BaseModel):
    strategy_key: str
    label: str
    is_benchmark: bool
    metrics: Dict[str, Any]
    bootstrap: Optional[Dict[str, Any]] = None

class BacktestDetail(BaseModel):
    id: str
    name: str
    status: str
    config: Dict[str, Any]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    strategies: List[StrategyResult] = []

class TradeOut(BaseModel):
    symbol: str
    entry_date: date
    exit_date: Optional[date] = None
    entry_price: float
    exit_price: Optional[float] = None
    shares: int
    gross_pnl: float
    costs: float
    tax: float
    net_pnl: float
    return_pct: float
    holding_days: Optional[int] = None
    exit_reason: Optional[str] = None

class FoldOut(BaseModel):
    fold_idx: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    weights: Dict[str, Any]
    metrics: Dict[str, Any]

class EquityPoint(BaseModel):
    date: date
    equity: float
    drawdown: float
    exposure: float

class EquityResponse(BaseModel):
    series: Dict[str, List[EquityPoint]]

class FoldsResponse(BaseModel):
    items: List[FoldOut]
