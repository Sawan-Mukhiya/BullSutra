"""Unit tests for NEPSE transaction costs, commission slabs, and CGT."""
import pytest
from bullsutra.backtest.costs import (
    commission,
    trade_cost,
    capital_gains_tax,
    slab_rate,
)

def test_commission_slabs_and_minimum():
    # Min commission Rs 10
    assert commission(1000.0) == 10.0  # 1000 * 0.0040 = 4.0 -> min 10.0

    # Slab 1: <= 50,000 (0.40%)
    assert slab_rate(40000.0) == 0.0040
    assert commission(40000.0) == 160.0

    # Slab 2: <= 500,000 (0.37%)
    assert slab_rate(200000.0) == 0.0037
    assert commission(200000.0) == 740.0

    # Slab 3: <= 2,000,000 (0.34%)
    assert slab_rate(1500000.0) == 0.0034
    assert commission(1500000.0) == 5100.0

    # Slab 4: <= 10,000,000 (0.30%)
    assert slab_rate(5000000.0) == 0.0030
    assert commission(5000000.0) == 15000.0

    # Slab 5: > 10,000,000 (0.27%)
    assert slab_rate(12000000.0) == 0.0027
    assert commission(12000000.0) == 32400.0

def test_trade_cost():
    # Value 100,000
    # Comm = 100,000 * 0.0037 = 370
    # SEBON = 100,000 * 0.00015 = 15
    # DP = 25
    # Total = 410
    val = 100000.0
    expected = 370.0 + 15.0 + 25.0
    assert trade_cost(val) == expected

def test_capital_gains_tax():
    # Short term: <= 365 days (7.5%)
    assert capital_gains_tax(10000.0, holding_days=100) == 750.0
    assert capital_gains_tax(10000.0, holding_days=365) == 750.0

    # Long term: > 365 days (5.0%)
    assert capital_gains_tax(10000.0, holding_days=366) == 500.0
    assert capital_gains_tax(10000.0, holding_days=700) == 500.0

    # Loss: 0 tax
    assert capital_gains_tax(-5000.0, holding_days=50) == 0.0
    assert capital_gains_tax(0.0, holding_days=50) == 0.0
