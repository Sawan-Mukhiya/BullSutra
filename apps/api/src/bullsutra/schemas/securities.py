from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SecuritySummary(BaseModel):
    symbol: str
    name: str
    sector: str
    sector_group: str
    in_universe: bool
    instrument_class: str
    last_close: Optional[float] = None
    last_trade_date: Optional[date] = None
    change_pct: Optional[float] = None

class SecurityDetail(SecuritySummary):
    instrument_type: str
    listed_on: Optional[date] = None
    first_bar_date: Optional[date] = None
    last_bar_date: Optional[date] = None
    has_brief: bool = False

class Candle(BaseModel):
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: int
    turnover: float
    regime_id: str
    limit_pct: float
    ret_adj_1d: Optional[float] = None

class OhlcvResponse(BaseModel):
    symbol: str
    adjusted: bool
    candles: List[Candle]

class IndicatorsResponse(BaseModel):
    symbol: str
    series: Dict[str, List[Dict[str, Any]]]
