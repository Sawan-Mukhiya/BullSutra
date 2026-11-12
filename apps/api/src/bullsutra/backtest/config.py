from datetime import date
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field

class BacktestConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    universe: str = "pit_universe"
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    train_days: int = Field(default=750, ge=250)
    test_days: int = Field(default=120, gt=0)
    step_days: int = Field(default=120, gt=0)
    embargo_days: int = Field(default=10, ge=0)
    horizon: int = Field(default=10, gt=0)
    initial_capital: float = Field(default=1_000_000.0, gt=0)
    max_positions: int = Field(default=10, gt=0)
    slippage_bps: float = Field(default=20.0, ge=0)
    execution: Literal["next_open", "next_close"] = "next_open"
    min_calibrated_confidence: float = Field(default=0.10, ge=0.0, le=1.0)
    rf_annual: float = Field(default=0.05, ge=0.0)
    apply_taxes: bool = True
    stop_loss_pct: Optional[float] = None
    strategies: List[str] = [
        "tech_only", "fund_only", "news_only", "consensus_basic",
        "consensus_weighted", "consensus_debate", "full"
    ]
    benchmarks: List[str] = ["bh_equal_weight", "bh_nepse_index"]
    bootstrap_samples: int = Field(default=2000, ge=0)
    bootstrap_block: int = Field(default=10, gt=0)
    seed: int = 42
    logic_version: Optional[str] = None
