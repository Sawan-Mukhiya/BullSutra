"""Outcome computation for agent signals."""
from datetime import date
from typing import Optional
import numpy as np
import pandas as pd

from bullsutra.core.constants import FORWARD_HORIZON_DAYS, OUTCOME_MIN_ABS_SCORE
from bullsutra.agents.constants import LOGIC_VERSION
from bullsutra.agents.specialists._util import sign

def compute_outcomes(
    prices_long: pd.DataFrame,
    signals: pd.DataFrame,
    horizon: int = FORWARD_HORIZON_DAYS,
) -> pd.DataFrame:
    """Compute forward returns and hits for signals using prices_long.
    
    Output columns:
    security_id, as_of, agent, horizon_days, score, forward_return, realized_on, hit, logic_version
    """
    if prices_long.empty or signals.empty:
        return pd.DataFrame(columns=[
            "security_id", "as_of", "agent", "horizon_days",
            "score", "forward_return", "realized_on", "hit", "logic_version"
        ])

    results = []
    
    # Process per security_id
    grouped_prices = {sec_id: df.sort_values("date").reset_index(drop=True) 
                      for sec_id, df in prices_long.groupby("security_id")}

    for (sec_id, as_of_date), sig_rows in signals.groupby(["security_id", "as_of"]):
        if sec_id not in grouped_prices:
            continue
        p_df = grouped_prices[sec_id]
        
        # Match as_of_date index in p_df
        pos_list = p_df.index[p_df["date"] == as_of_date].tolist()
        if not pos_list:
            continue
        i = pos_list[0]
        
        # Requires i+1 and i+horizon to exist
        if i + horizon >= len(p_df):
            continue

        p_next = p_df.iloc[i + 1]
        p_target = p_df.iloc[i + horizon]

        adj_open_next = float(p_next["raw_open"] * p_next["adj_factor"]) if "adj_factor" in p_next else float(p_next["open"])
        adj_close_target = float(p_target["raw_close"] * p_target["adj_factor"]) if "adj_factor" in p_target else float(p_target["close"])

        if adj_open_next <= 0:
            continue

        fwd_ret = (adj_close_target / adj_open_next) - 1.0
        realized_date = p_target["date"]

        for _, sig in sig_rows.iterrows():
            sc = float(sig["score"])
            if abs(sc) < OUTCOME_MIN_ABS_SCORE:
                hit = None
            else:
                if fwd_ret == 0.0:
                    hit = False
                else:
                    hit = (sign(sc) == sign(fwd_ret))

            results.append({
                "security_id": sec_id,
                "as_of": as_of_date,
                "agent": sig["agent"],
                "horizon_days": horizon,
                "score": round(sc, 4),
                "forward_return": round(fwd_ret, 6),
                "realized_on": realized_date,
                "hit": hit,
                "logic_version": LOGIC_VERSION,
            })

    return pd.DataFrame(results)
