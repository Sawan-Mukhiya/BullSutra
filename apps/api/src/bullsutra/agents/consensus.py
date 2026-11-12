"""Debate, consensus, and risk gate protocol."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Literal, Any
import math

from bullsutra.core.constants import (
    MIN_ACTIVE_CONF,
    MIN_TOTAL_CONF,
    DEBATE_TAU,
    DEBATE_MAX_ROUNDS,
    DEBATE_KAPPA,
    DEBATE_CONF_DECAY,
    RISK_GATE_THRESHOLD,
    LABEL_THRESHOLD,
    ILLIQUID_FLAG_THRESHOLD,
)
from bullsutra.schemas.contracts import (
    AgentSignal,
    Consensus,
    Debate,
    DebateRound,
    DebateRevision,
    CrossCheck,
    Label,
)
from bullsutra.agents.specialists._util import clip

@dataclass
class Voter:
    agent: str
    score: float
    confidence: float

def init_voters(signals: Dict[str, AgentSignal]) -> Dict[str, Voter]:
    """Initialize voters from news, fundamentals, and technicals."""
    voters = {}
    for name in ("news", "fundamentals", "technicals"):
        sig = signals.get(name)
        if sig is not None:
            voters[name] = Voter(agent=name, score=float(sig.score), confidence=float(sig.confidence))
        else:
            voters[name] = Voter(agent=name, score=0.0, confidence=0.0)
    return voters

def active_names(voters: Dict[str, Voter]) -> List[str]:
    """Names of voters with confidence >= MIN_ACTIVE_CONF."""
    return [name for name, v in voters.items() if v.confidence >= MIN_ACTIVE_CONF]

def disagreement(voters: Dict[str, Voter], names: List[str]) -> float:
    """Disagreement: (max score - min score) / 2 over names. 0 if fewer than 2."""
    if len(names) < 2:
        return 0.0
    scores = [voters[name].score for name in names]
    return (max(scores) - min(scores)) / 2.0

def apply_cross_checks(voters: Dict[str, Voter]) -> List[CrossCheck]:
    """Apply R1 and R2 cross checks using original scores before mutation."""
    checks = []
    news_v = voters.get("news")
    fund_v = voters.get("fundamentals")
    tech_v = voters.get("technicals")

    if not news_v or not fund_v or not tech_v:
        return checks

    # Snapshot original scores and confidences
    orig_tech_s = tech_v.score
    orig_news_s = news_v.score
    orig_news_c = news_v.confidence
    orig_fund_s = fund_v.score
    orig_fund_c = fund_v.confidence

    # R1: technicals.score > 0.3 and news.score < -0.3 and news.confidence > 0.4
    if orig_tech_s > 0.3 and orig_news_s < -0.3 and orig_news_c > 0.4:
        tech_v.confidence *= 0.8
        checks.append(CrossCheck(
            rule="R1",
            agent_affected="technicals",
            message="Technical strength conflicts with negative recent news; technicals confidence reduced by 20%.",
        ))

    # R2: news.score > 0.3 and fundamentals.score < -0.3 and fundamentals.confidence > 0.4
    if orig_news_s > 0.3 and orig_fund_s < -0.3 and orig_fund_c > 0.4:
        news_v.confidence *= 0.8
        checks.append(CrossCheck(
            rule="R2",
            agent_affected="news",
            message="Positive news sentiment is not supported by fundamentals; news confidence reduced by 20%.",
        ))

    return checks

def debate_step(
    voters: Dict[str, Voter],
    weights: Dict[str, float],
    names: List[str],
    round_num: int,
) -> Tuple[DebateRound, float]:
    """Execute one debate round with simultaneous update."""
    d_before = disagreement(voters, names)
    revisions: List[DebateRevision] = []
    new_states: Dict[str, Tuple[float, float]] = {}

    for i in names:
        v_i = voters[i]
        s_i = v_i.score
        c_i = v_i.confidence

        others = [j for j in names if j != i]
        denom = sum(weights.get(j, 1.0) * voters[j].confidence for j in others)
        if denom == 0.0:
            m_i = s_i
        else:
            num = sum(weights.get(j, 1.0) * voters[j].confidence * voters[j].score for j in others)
            m_i = num / denom

        s_prime = s_i + DEBATE_KAPPA * (1.0 - c_i) * (m_i - s_i)
        c_prime = c_i * (1.0 - DEBATE_CONF_DECAY * abs(s_i - m_i))

        new_states[i] = (s_prime, c_prime)
        revisions.append(DebateRevision(
            agent=i,  # type: ignore
            score_before=round(s_i, 4),
            score_after=round(s_prime, 4),
            confidence_before=round(c_i, 4),
            confidence_after=round(c_prime, 4),
            others_mean=round(m_i, 4) if m_i is not None else None,
        ))

    # Simultaneous update
    for i in names:
        voters[i].score, voters[i].confidence = new_states[i]

    d_after = disagreement(voters, names)
    return (
        DebateRound(
            round=round_num,
            disagreement_before=round(d_before, 4),
            revisions=revisions,
            disagreement_after=round(d_after, 4),
        ),
        d_after,
    )

def finalize_consensus(
    voters: Dict[str, Voter],
    risk: AgentSignal,
    weights: Dict[str, float],
    calibrator: Optional[Dict[str, Any]] = None,
    *,
    final_disagreement: float,
    debate_triggered: bool,
    risk_gate: bool = True,
) -> Consensus:
    """Aggregate voter signals into final consensus."""
    flags: List[str] = []

    # 1. Total confidence over all three voters
    total_conf = sum(v.confidence for v in voters.values())
    r = float(risk.score)
    pos_mult = max(0.2, 1.0 - r) if risk_gate else 1.0

    if total_conf < MIN_TOTAL_CONF:
        flags.append("insufficient_signal")
        return Consensus(
            label="HOLD",
            score=0.0,
            raw_confidence=0.0,
            confidence=0.0,
            position_multiplier=round(pos_mult, 4),
            conflicted=False,
            flags=flags,
        )

    # 2. Score S over active voters
    act = active_names(voters)
    denom = sum(weights.get(i, 1.0) * voters[i].confidence for i in act)
    if denom == 0.0 or len(act) == 0:
        S = 0.0
    else:
        num = sum(weights.get(i, 1.0) * voters[i].confidence * voters[i].score for i in act)
        S = num / denom

    # 3. Risk gate
    if risk_gate and S > 0.0 and r >= RISK_GATE_THRESHOLD:
        S = S * (1.0 - r)
        flags.append("risk_damped")

    # 4. Label
    if S > LABEL_THRESHOLD:
        label: Label = "BUY"
    elif S < -LABEL_THRESHOLD:
        label = "SELL"
    else:
        label = "HOLD"

    # 5. Illiquid rule
    if risk_gate and label == "BUY":
        liq_val = float(risk.meta.get("components", {}).get("liq", 0.0) or 0.0)
        if liq_val >= ILLIQUID_FLAG_THRESHOLD:
            label = "HOLD"
            flags.append("illiquid_no_buy")

    # 6. Conflict rule
    conflicted = debate_triggered and (final_disagreement > DEBATE_TAU)
    if conflicted and label in ("BUY", "SELL"):
        label = "HOLD"
        flags.append("conflict_hold")

    # 7. Raw confidence
    if label in ("BUY", "SELL"):
        raw_conf = clip(abs(S) * (1.0 - 0.5 * final_disagreement), 0.0, 1.0)
    else:
        raw_conf = clip((1.0 - abs(S) / LABEL_THRESHOLD) * (1.0 - final_disagreement), 0.0, 1.0)

    # 8. Calibration
    conf = raw_conf
    if calibrator is not None and label in ("BUY", "SELL"):
        from bullsutra.agents.calibration.isotonic import apply_calibrator
        conf = apply_calibrator(calibrator, raw_conf)

    return Consensus(
        label=label,
        score=round(S, 4),
        raw_confidence=round(raw_conf, 4),
        confidence=round(conf, 4),
        position_multiplier=round(pos_mult, 4),
        conflicted=conflicted,
        flags=flags,
    )

def run_consensus(
    signals: Dict[str, AgentSignal],
    weights: Optional[Dict[str, float]] = None,
    calibrator: Optional[Dict[str, Any]] = None,
    *,
    debate: bool = True,
    risk_gate: bool = True,
) -> Tuple[Consensus, Debate, Dict[str, Voter]]:
    """Execute debate and consensus resolution."""
    if weights is None:
        weights = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}

    risk_sig = signals.get("risk")
    if risk_sig is None:
        risk_sig = AgentSignal(
            agent="risk", score=0.5, confidence=0.0, drivers=[], risks=[], flags=[], meta={}
        )

    voters = init_voters(signals)
    cross_checks: List[CrossCheck] = []
    rounds: List[DebateRound] = []

    if debate:
        cross_checks = apply_cross_checks(voters)

    names = active_names(voters)
    d0 = disagreement(voters, names)
    d_curr = d0
    debate_triggered = False

    if debate and d0 > DEBATE_TAU:
        debate_triggered = True
        round_idx = 1
        while d_curr > DEBATE_TAU and round_idx <= DEBATE_MAX_ROUNDS:
            deb_round, d_curr = debate_step(voters, weights, names, round_idx)
            rounds.append(deb_round)
            round_idx += 1

    final_d = d_curr if debate else d0

    debate_record = Debate(
        triggered=debate_triggered,
        initial_disagreement=round(d0, 4),
        final_disagreement=round(final_d, 4),
        cross_checks=cross_checks,
        rounds=rounds,
        summary=None,
    )

    consensus = finalize_consensus(
        voters,
        risk_sig,
        weights,
        calibrator,
        final_disagreement=final_d,
        debate_triggered=debate_triggered,
        risk_gate=risk_gate,
    )

    return consensus, debate_record, voters
