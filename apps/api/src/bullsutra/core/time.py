"""Time and calendar utilities for NEPSE trading hours and regimes."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from bullsutra.core.constants import (
    NPT,
    REGIME_1_END,
    REGIME_2_END,
    REGIME_3_START,
    SIGNAL_CUTOFF_HOUR,
    SIGNAL_CUTOFF_MINUTE,
)

def to_npt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=NPT)
    return dt.astimezone(NPT)

def npt_now() -> datetime:
    return datetime.now(NPT)

def cutoff_datetime(as_of: date) -> datetime:
    """Returns cutoff datetime (16:00 NPT on as_of) as an aware datetime."""
    return datetime.combine(
        as_of,
        time(SIGNAL_CUTOFF_HOUR, SIGNAL_CUTOFF_MINUTE, tzinfo=NPT)
    )

def get_regime_id(d: date) -> str:
    """Returns regime identifier for the given date."""
    if d <= REGIME_1_END:
        return "regime_1"
    elif d <= REGIME_2_END:
        return "regime_2"
    else:
        return "regime_3"

def is_trading_day_fallback(d: date) -> bool:
    """
    Fallback trading day rule when dim_trading_day has no row:
    - Pre-2026-04-06 (regime_1): Sunday (dow=6) to Thursday (dow=3)
    - On/after 2026-04-06 (regime_2/3): Monday (dow=0) to Friday (dow=4)
    """
    weekday = d.weekday()  # Monday=0, Sunday=6
    if d <= REGIME_1_END:
        return weekday in (6, 0, 1, 2, 3)
    else:
        return weekday in (0, 1, 2, 3, 4)

get_regime_id_for_date = get_regime_id
