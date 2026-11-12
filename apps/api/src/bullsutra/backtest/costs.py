"""NEPSE transaction cost and tax model."""
from pathlib import Path
from typing import Optional, List, Tuple
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "costs.yaml"

def _load_cost_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "commission_slabs": [
            [50000, 0.0040],
            [500000, 0.0037],
            [2000000, 0.0034],
            [10000000, 0.0030],
            [None, 0.0027],
        ],
        "commission_min_npr": 10.0,
        "sebon_fee_rate": 0.00015,
        "dp_charge_npr": 25.0,
        "cgt_short_rate": 0.075,
        "cgt_long_rate": 0.05,
        "min_lot": 10,
    }

COST_CFG = _load_cost_config()
COMMISSION_SLABS: List[Tuple[Optional[float], float]] = COST_CFG["commission_slabs"]
COMMISSION_MIN_NPR: float = float(COST_CFG["commission_min_npr"])
SEBON_FEE_RATE: float = float(COST_CFG["sebon_fee_rate"])
DP_CHARGE_NPR: float = float(COST_CFG["dp_charge_npr"])
CGT_SHORT_RATE: float = float(COST_CFG["cgt_short_rate"])
CGT_LONG_RATE: float = float(COST_CFG["cgt_long_rate"])
MIN_LOT: int = int(COST_CFG["min_lot"])

def slab_rate(value: float) -> float:
    """Find brokerage commission rate for transaction value."""
    for bound, rate in COMMISSION_SLABS:
        if bound is None or value <= bound:
            return rate
    return 0.0027

def commission(value: float) -> float:
    """Compute broker commission with minimum threshold."""
    if value <= 0:
        return 0.0
    return max(COMMISSION_MIN_NPR, value * slab_rate(value))

def trade_cost(value: float) -> float:
    """Total one-way trading cost: commission + SEBON regulatory fee + DP charge."""
    if value <= 0:
        return 0.0
    return commission(value) + (value * SEBON_FEE_RATE) + DP_CHARGE_NPR

def capital_gains_tax(gain: float, holding_days: int) -> float:
    """Calculate NEPSE capital gains tax based on holding duration."""
    if gain <= 0:
        return 0.0
    rate = CGT_LONG_RATE if holding_days > 365 else CGT_SHORT_RATE
    return gain * rate
