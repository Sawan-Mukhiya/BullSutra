"""Global canonical constants for BullSutra."""
from datetime import date
from zoneinfo import ZoneInfo

TZ_NAME = "Asia/Kathmandu"
NPT = ZoneInfo(TZ_NAME)
TRADING_DAYS_PER_YEAR = 240

# Regime boundaries
REGIME_1_END = date(2026, 4, 5)
REGIME_2_END = date(2026, 4, 19)
REGIME_3_START = date(2026, 4, 20)

CIRCUIT_LIMIT_PCT = 0.10

def get_circuit_limit_pct(d: date) -> float:
    """Regime-dependent circuit limit: 0.10 before 2026-04-20, 0.15 on/after 2026-04-20."""
    return 0.15 if d >= REGIME_3_START else 0.10

# Signal and agent parameters
SIGNAL_CUTOFF_HOUR = 16
SIGNAL_CUTOFF_MINUTE = 0
MIN_BARS_SIGNALS = 210
MIN_BARS_RISK = 60
LABEL_THRESHOLD = 0.25
FORWARD_HORIZON_DAYS = 10
MIN_ACTIVE_CONF = 0.2
MIN_TOTAL_CONF = 0.3
DEBATE_TAU = 0.5
DEBATE_MAX_ROUNDS = 2
DEBATE_KAPPA = 0.6
DEBATE_CONF_DECAY = 0.2
RISK_GATE_THRESHOLD = 0.7
ILLIQUID_FLAG_THRESHOLD = 0.8
WEIGHT_ETA = 4.0
WEIGHT_FLOOR = 0.1
WEIGHT_MIN_SAMPLES = 50
WEIGHT_WINDOW = 250
OUTCOME_MIN_ABS_SCORE = 0.1
CALIBRATION_MIN_SAMPLES = 200
NEWS_WINDOW_DAYS = 14
NEWS_DECAY_DAYS = 5
NEWS_PRIOR = 1.0
NEWS_SATURATION = 3.0
DEDUP_SIMILARITY = 0.92
DEDUP_WINDOW_DAYS = 3
UNIVERSE_SIZE = 40

DISCLAIMER_TEXT = (
    "BullSutra is an academic research tool. Its output is not investment advice, "
    "a recommendation, or an offer to buy or sell securities. Past performance and "
    "backtest results do not guarantee future results. Do your own research and "
    "consult a licensed professional before investing."
)
