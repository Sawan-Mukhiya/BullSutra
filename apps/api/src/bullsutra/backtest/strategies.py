"""Decider strategies for backtesting."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any, Tuple
import pandas as pd

from bullsutra.core.constants import LABEL_THRESHOLD, MIN_ACTIVE_CONF
from bullsutra.schemas.contracts import AgentSignal
from bullsutra.agents.consensus import run_consensus
from bullsutra.agents.calibration.isotonic import apply_calibrator

@dataclass
class Decision:
    label: str
    score: float
    multiplier: float = 1.0
    calibrated_conf: Optional[float] = None

class Decider(ABC):
    def __init__(self, key: str):
        self.key = key
        self.fold_weights: Dict[str, float] = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}
        self.calibrator: Optional[Dict[str, Any]] = None
        self.min_calibrated_confidence: float = 0.10

    def set_fold(self, fold_params: Dict[str, Any]) -> None:
        if "weights" in fold_params and fold_params["weights"]:
            self.fold_weights = fold_params["weights"]
        self.calibrator = fold_params.get("calibrator")

    @abstractmethod
    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        pass

class SingleAgentDecider(Decider):
    def __init__(self, key: str, agent_prefix: str):
        super().__init__(key)
        self.agent_prefix = agent_prefix

    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        s = float(sig_row.get(f"{self.agent_prefix}_s", 0.0) or 0.0)
        c = float(sig_row.get(f"{self.agent_prefix}_c", 0.0) or 0.0)

        if s > LABEL_THRESHOLD and c >= MIN_ACTIVE_CONF:
            label = "BUY"
        elif s < -LABEL_THRESHOLD and c >= MIN_ACTIVE_CONF:
            label = "SELL"
        else:
            label = "HOLD"

        return Decision(label=label, score=s, multiplier=1.0, calibrated_conf=c)

class ConsensusBasicDecider(Decider):
    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        signals = _build_signals_from_row(sig_row)
        equal_w = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}
        consensus, _, _ = run_consensus(signals, weights=equal_w, calibrator=None, debate=False, risk_gate=False)
        return Decision(
            label=consensus.label,
            score=consensus.score,
            multiplier=1.0,
            calibrated_conf=consensus.confidence,
        )

class ConsensusWeightedDecider(Decider):
    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        signals = _build_signals_from_row(sig_row)
        consensus, _, _ = run_consensus(signals, weights=self.fold_weights, calibrator=None, debate=False, risk_gate=False)
        return Decision(
            label=consensus.label,
            score=consensus.score,
            multiplier=1.0,
            calibrated_conf=consensus.confidence,
        )

class ConsensusDebateDecider(Decider):
    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        signals = _build_signals_from_row(sig_row)
        consensus, _, _ = run_consensus(signals, weights=self.fold_weights, calibrator=None, debate=True, risk_gate=False)
        return Decision(
            label=consensus.label,
            score=consensus.score,
            multiplier=1.0,
            calibrated_conf=consensus.confidence,
        )

class FullSystemDecider(Decider):
    def decide(self, sig_row: Dict[str, Any]) -> Decision:
        signals = _build_signals_from_row(sig_row)
        consensus, _, _ = run_consensus(
            signals,
            weights=self.fold_weights,
            calibrator=self.calibrator,
            debate=True,
            risk_gate=True,
        )
        # Calibrate confidence for BUY / SELL
        cal_conf = consensus.raw_confidence
        if consensus.label in ("BUY", "SELL"):
            cal_conf = apply_calibrator(self.calibrator, consensus.raw_confidence)
            consensus.confidence = cal_conf

        return Decision(
            label=consensus.label,
            score=consensus.score,
            multiplier=consensus.position_multiplier,
            calibrated_conf=cal_conf,
        )

def _build_signals_from_row(sig_row: Dict[str, Any]) -> Dict[str, AgentSignal]:
    return {
        "news": AgentSignal(
            agent="news",
            score=float(sig_row.get("news_s", 0.0) or 0.0),
            confidence=float(sig_row.get("news_c", 0.0) or 0.0),
        ),
        "fundamentals": AgentSignal(
            agent="fundamentals",
            score=float(sig_row.get("fund_s", 0.0) or 0.0),
            confidence=float(sig_row.get("fund_c", 0.0) or 0.0),
        ),
        "technicals": AgentSignal(
            agent="technicals",
            score=float(sig_row.get("tech_s", 0.0) or 0.0),
            confidence=float(sig_row.get("tech_c", 0.0) or 0.0),
        ),
        "risk": AgentSignal(
            agent="risk",
            score=float(sig_row.get("risk_s", 0.5) or 0.5),
            confidence=float(sig_row.get("risk_c", 0.0) or 0.0),
            meta={"components": {"liq": float(sig_row.get("risk_liq", 0.0) or 0.0)}},
        ),
    }

def get_decider(key: str) -> Decider:
    if key == "tech_only":
        return SingleAgentDecider(key, "tech")
    elif key == "fund_only":
        return SingleAgentDecider(key, "fund")
    elif key == "news_only":
        return SingleAgentDecider(key, "news")
    elif key == "consensus_basic":
        return ConsensusBasicDecider(key)
    elif key == "consensus_weighted":
        return ConsensusWeightedDecider(key)
    elif key == "consensus_debate":
        return ConsensusDebateDecider(key)
    elif key == "full":
        return FullSystemDecider(key)
    raise ValueError(f"Unknown strategy key '{key}'")
