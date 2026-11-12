from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional, List
import pandas as pd

@dataclass
class MarketSnapshot:
    symbol: str
    security_id: int
    as_of: date
    prices: pd.DataFrame
    fundamentals: pd.DataFrame
    news: pd.DataFrame
    company_name: Optional[str] = None
    sector: Optional[str] = None
    sector_group: str = "other"
    floorsheet_agg: Optional[pd.DataFrame] = None
    regime_id: Optional[str] = None

class MarketDataProvider(ABC):
    @abstractmethod
    async def get_bars(self, symbol: str, as_of: date, lookback_sessions: int = 250, adjusted: bool = True) -> pd.DataFrame:
        pass

    @abstractmethod
    async def get_financials(self, symbol: str, as_of: date) -> pd.DataFrame:
        pass

    @abstractmethod
    async def get_actions(self, symbol: str, as_of: date) -> list[dict]:
        pass

    @abstractmethod
    async def get_universe(self, as_of: date) -> list[str]:
        pass

    @abstractmethod
    async def get_regime(self, d: date) -> str:
        pass

    @abstractmethod
    async def get_index(self, as_of: date, lookback_sessions: int = 250) -> pd.DataFrame:
        pass

    @abstractmethod
    async def get_floorsheet_agg(self, symbol: str, as_of: date, lookback_sessions: int = 20) -> pd.DataFrame:
        pass
