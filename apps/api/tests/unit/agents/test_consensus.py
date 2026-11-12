"""Golden vector and logic verification for debate, consensus, and risk gate."""
import pytest
from bullsutra.schemas.contracts import AgentSignal
from bullsutra.agents.consensus import run_consensus

def test_consensus_golden_vector_a():
    """Vector A (debate, borderline HOLD).
    weights all 1.0, risk score 0.2, no calibrator.
    Signals: news (0.6, 0.8), fundamentals (-0.5, 0.7), technicals (0.7, 0.6).
    """
    signals = {
        "news": AgentSignal(agent="news", score=0.6, confidence=0.8),
        "fundamentals": AgentSignal(agent="fundamentals", score=-0.5, confidence=0.7),
        "technicals": AgentSignal(agent="technicals", score=0.7, confidence=0.6),
        "risk": AgentSignal(agent="risk", score=0.2, confidence=1.0),
    }

    consensus, debate, voters = run_consensus(signals, weights={"news": 1.0, "fundamentals": 1.0, "technicals": 1.0})

    # R2 applies: news confidence becomes 0.64
    assert len(debate.cross_checks) == 1
    assert debate.cross_checks[0].rule == "R2"
    assert debate.triggered is True
    assert len(debate.rounds) == 1  # stops after round 1 since D1 = 0.4157 <= 0.50

    # Checks within 1e-3
    assert consensus.label == "HOLD"
    assert abs(consensus.score - 0.2432) < 1e-3
    assert abs(consensus.raw_confidence - 0.0160) < 1e-3
    assert consensus.conflicted is False
    assert abs(consensus.position_multiplier - 0.8) < 1e-3

def test_consensus_golden_vector_b():
    """Vector B (agreement, BUY).
    news (0.6, 0.7), fundamentals (0.5, 0.7), technicals (0.7, 0.7), risk 0.3, weights 1.0.
    D = 0.1 (no debate). S = 0.6, label BUY, raw_confidence = 0.57, position_multiplier = 0.7.
    """
    signals = {
        "news": AgentSignal(agent="news", score=0.6, confidence=0.7),
        "fundamentals": AgentSignal(agent="fundamentals", score=0.5, confidence=0.7),
        "technicals": AgentSignal(agent="technicals", score=0.7, confidence=0.7),
        "risk": AgentSignal(agent="risk", score=0.3, confidence=1.0),
    }

    consensus, debate, _ = run_consensus(signals)

    assert debate.triggered is False
    assert len(debate.rounds) == 0
    assert consensus.label == "BUY"
    assert abs(consensus.score - 0.6000) < 1e-3
    assert abs(consensus.raw_confidence - 0.5700) < 1e-3
    assert abs(consensus.position_multiplier - 0.7) < 1e-3

def test_consensus_golden_vector_c():
    """Vector C (risk gate).
    Same as B with risk 0.8: S = 0.6 * (1 - 0.8) = 0.12 -> HOLD, flag risk_damped, position_multiplier = 0.2.
    """
    signals = {
        "news": AgentSignal(agent="news", score=0.6, confidence=0.7),
        "fundamentals": AgentSignal(agent="fundamentals", score=0.5, confidence=0.7),
        "technicals": AgentSignal(agent="technicals", score=0.7, confidence=0.7),
        "risk": AgentSignal(agent="risk", score=0.8, confidence=1.0),
    }

    consensus, debate, _ = run_consensus(signals)

    assert consensus.label == "HOLD"
    assert abs(consensus.score - 0.1200) < 1e-3
    assert "risk_damped" in consensus.flags
    assert abs(consensus.position_multiplier - 0.2) < 1e-3

def test_consensus_debate_false_and_risk_gate_false():
    """Toggling debate=False or risk_gate=False respects flags."""
    signals = {
        "news": AgentSignal(agent="news", score=0.6, confidence=0.8),
        "fundamentals": AgentSignal(agent="fundamentals", score=-0.5, confidence=0.7),
        "technicals": AgentSignal(agent="technicals", score=0.7, confidence=0.6),
        "risk": AgentSignal(agent="risk", score=0.8, confidence=1.0),
    }

    # With risk_gate=False, high risk does not damp score
    c_nogate, _, _ = run_consensus(signals, debate=False, risk_gate=False)
    assert c_nogate.position_multiplier == 1.0
    assert "risk_damped" not in c_nogate.flags
