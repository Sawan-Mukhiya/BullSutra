"""Numeric utility functions for specialist agents."""
import math
import numpy as np

def sign(x: float) -> float:
    if math.isnan(x):
        return 0.0
    if x > 0:
        return 1.0
    elif x < 0:
        return -1.0
    return 0.0

def clip(x: float, lo: float, hi: float) -> float:
    if math.isnan(x):
        return lo
    return max(lo, min(hi, x))

def lin(x: float, bad: float, good: float) -> float:
    """Maps bad -> -1 and good -> +1. Works when good < bad as well."""
    if math.isnan(x):
        return 0.0
    denom = good - bad
    if denom == 0:
        return 0.0
    val = 2.0 * (x - bad) / denom - 1.0
    return clip(val, -1.0, 1.0)

def lin01(x: float, lo: float, hi: float) -> float:
    """Maps lo -> 0 and hi -> 1, clipped to [0, 1]."""
    if math.isnan(x):
        return 0.0
    denom = hi - lo
    if denom == 0:
        return 0.0
    val = (x - lo) / denom
    return clip(val, 0.0, 1.0)
