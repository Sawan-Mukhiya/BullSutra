"""Agent weight fitting based on historical hit rate outcomes."""
import math
from datetime import date
from typing import Dict, Tuple, Any
import pandas as pd
import numpy as np

from bullsutra.core.constants import (
    WEIGHT_WINDOW,
    WEIGHT_MIN_SAMPLES,
    WEIGHT_FLOOR,
    WEIGHT_ETA,
)

AGENTS = ["news", "fundamentals", "technicals"]

def fit_weights(outcomes: pd.DataFrame, cutoff: date) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Fit agent weights using historical outcomes up to cutoff date.
    
    Returns (weights, metrics).
    """
    if outcomes.empty:
        return ({a: 1.0 for a in AGENTS}, {"hit_rates": {}, "n_samples": {}, "raw_weights": {}})

    # Use only outcomes with realized_on <= cutoff and agent in AGENTS and hit not null
    df = outcomes[
        (outcomes["realized_on"] <= cutoff)
        & (outcomes["agent"].isin(AGENTS))
        & (outcomes["hit"].notna())
    ].copy()

    raw_weights = {}
    hit_rates = {}
    n_samples = {}

    for a in AGENTS:
        sub = df[df["agent"] == a].sort_values("realized_on", ascending=False)
        sub = sub.iloc[:WEIGHT_WINDOW]
        n = len(sub)
        n_samples[a] = n

        if n < WEIGHT_MIN_SAMPLES:
            raw_w = 1.0
            hr = 0.5
        else:
            hr = float(sub["hit"].astype(float).mean())
            raw_w = max(WEIGHT_FLOOR, math.exp(WEIGHT_ETA * (hr - 0.5)))

        hit_rates[a] = round(hr, 4)
        raw_weights[a] = raw_w

    # Normalise so mean weight is 1.0
    mean_w = sum(raw_weights.values()) / len(raw_weights)
    weights = {a: round(raw_weights[a] / mean_w, 4) for a in AGENTS}

    metrics = {
        "hit_rates": hit_rates,
        "n_samples": n_samples,
        "raw_weights": {a: round(raw_weights[a], 4) for a in AGENTS},
    }

    return weights, metrics
