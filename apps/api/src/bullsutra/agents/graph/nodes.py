"""LangGraph node definitions for the BullSutra agent workflow."""
import asyncio
import functools
import uuid
from typing import Dict, Any, Callable, Optional
from langchain_core.runnables import RunnableConfig
import structlog

DEFAULT_WEIGHTS = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}
from bullsutra.agents.constants import LOGIC_VERSION, GRAPH_VERSION, PROMPT_VERSION
from bullsutra.schemas.contracts import AgentSignal, Debate
from bullsutra.marketdata.db import build_snapshot_db
from bullsutra.db.repositories.weights import get_latest_weights
from bullsutra.db.repositories.briefs import insert_brief
from bullsutra.db.repositories.signals import upsert_signals
from bullsutra.agents.specialists.technicals import technicals_signal
from bullsutra.agents.specialists.fundamentals import fundamentals_signal
from bullsutra.agents.specialists.news import news_signal
from bullsutra.agents.specialists.risk import risk_signal
from bullsutra.agents.consensus import (
    init_voters,
    active_names,
    disagreement,
    apply_cross_checks,
    debate_step,
    finalize_consensus,
)
from bullsutra.agents.calibration.isotonic import apply_calibrator
from bullsutra.agents.briefing import assemble_brief
from bullsutra.agents.llm.narrate import narrate

logger = structlog.get_logger(__name__)

NODE_PROGRESS = {
    "load_context": 0.10,
    "specialists": 0.40,
    "collect": 0.45,
    "debate": 0.55,
    "consensus": 0.65,
    "calibrate": 0.70,
    "write_brief": 0.90,
    "persist": 1.00,
}

def evented(node_name: str):
    """Decorator to emit JobContext events and handle specialist errors gracefully."""
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
            configurable = config.get("configurable", {})
            ctx = configurable.get("ctx")
            if ctx is not None:
                await ctx.emit("node_started", {"node": node_name})

            try:
                res = await fn(state, config)
                data = res.get("_event_data", {})
                if ctx is not None:
                    await ctx.emit("node_finished", {"node": node_name, **data})
                    if node_name in NODE_PROGRESS:
                        await ctx.set_progress(NODE_PROGRESS[node_name])
                # Remove internal _event_data from state update
                if "_event_data" in res:
                    res = {k: v for k, v in res.items() if k != "_event_data"}
                return res
            except Exception as e:
                logger.exception("node_error", node=node_name, error=str(e))
                if ctx is not None:
                    await ctx.emit("log", {"level": "error", "message": f"Error in node {node_name}: {str(e)}"})
                
                # If specialist, return neutral fallback instead of failing graph
                if node_name in ("news", "fundamentals", "technicals"):
                    neutral = AgentSignal(
                        agent=node_name,  # type: ignore
                        score=0.0,
                        confidence=0.0,
                        drivers=[],
                        risks=[],
                        flags=["agent_error"],
                        meta={"error": str(e)},
                    )
                    return {"signals": {node_name: neutral}}
                elif node_name == "risk":
                    neutral_risk = AgentSignal(
                        agent="risk",
                        score=0.5,
                        confidence=0.0,
                        drivers=[],
                        risks=[],
                        flags=["agent_error"],
                        meta={"error": str(e), "components": {}, "raw": {}, "flag_details": []},
                    )
                    return {"signals": {"risk": neutral_risk}}
                raise e

        return wrapper
    return decorator

@evented("load_context")
async def node_load_context(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    configurable = config.get("configurable", {})
    ctx = configurable.get("ctx")
    db = configurable.get("db") or (getattr(ctx, "db", None))

    sec_id = state["security_id"]
    as_of = state["as_of"]

    # 1. Build snapshot
    snapshot = await build_snapshot_db(db, sec_id, as_of)

    # 2. Latest weights and calibrator
    weights_row = await get_latest_weights(db, scope="live")
    if weights_row:
        weights = weights_row.weights
        calibrator = weights_row.calibrator
    else:
        weights = {"news": 1.0, "fundamentals": 1.0, "technicals": 1.0}
        calibrator = None

    bars_count = len(snapshot.prices) if snapshot.prices is not None else 0
    news_count = len(snapshot.news) if snapshot.news is not None else 0

    return {
        "snapshot": snapshot,
        "weights": weights,
        "calibrator": calibrator,
        "_event_data": {"bars": bars_count, "news": news_count},
    }

@evented("technicals")
async def node_technicals(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    snap = state["snapshot"]
    sig = await asyncio.to_thread(technicals_signal, snap)
    return {
        "signals": {"technicals": sig},
        "_event_data": {"score": sig.score, "confidence": sig.confidence},
    }

@evented("fundamentals")
async def node_fundamentals(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    snap = state["snapshot"]
    sig = await asyncio.to_thread(fundamentals_signal, snap)
    return {
        "signals": {"fundamentals": sig},
        "_event_data": {"score": sig.score, "confidence": sig.confidence},
    }

@evented("news")
async def node_news(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    snap = state["snapshot"]
    sig = await asyncio.to_thread(news_signal, snap)
    return {
        "signals": {"news": sig},
        "_event_data": {"score": sig.score, "confidence": sig.confidence},
    }

@evented("risk")
async def node_risk(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    snap = state["snapshot"]
    sig = await asyncio.to_thread(risk_signal, snap)
    return {
        "signals": {"risk": sig},
        "_event_data": {"score": sig.score, "confidence": sig.confidence},
    }

@evented("collect")
async def node_collect(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    signals = state.get("signals", {})
    voters = init_voters(signals)
    cross_checks = apply_cross_checks(voters)
    names = active_names(voters)
    d0 = disagreement(voters, names)

    return {
        "voters": voters,
        "cross_checks": cross_checks,
        "initial_disagreement": round(d0, 4),
        "disagreement": round(d0, 4),
        "debate_rounds": [],
        "active": names,
        "_event_data": {"disagreement": round(d0, 4), "cross_checks": len(cross_checks)},
    }

@evented("debate")
async def node_debate(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    voters = state["voters"]
    weights = state.get("weights", {})
    names = state.get("active", [])
    rounds = list(state.get("debate_rounds", []))
    round_num = len(rounds) + 1

    deb_round, d_after = debate_step(voters, weights, names, round_num)
    rounds.append(deb_round)

    return {
        "voters": voters,
        "debate_rounds": rounds,
        "disagreement": round(d_after, 4),
        "_event_data": {"round": round_num, "disagreement": round(d_after, 4)},
    }

@evented("consensus")
async def node_consensus(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    voters = state["voters"]
    risk_sig = state["signals"].get("risk")
    if not risk_sig:
        risk_sig = AgentSignal(agent="risk", score=0.5, confidence=0.0)

    weights = state.get("weights", {})
    final_d = state.get("disagreement", 0.0)
    rounds = state.get("debate_rounds", [])
    debate_triggered = len(rounds) > 0

    consensus = finalize_consensus(
        voters,
        risk_sig,
        weights,
        calibrator=None,
        final_disagreement=final_d,
        debate_triggered=debate_triggered,
        risk_gate=True,
    )

    return {
        "consensus": consensus,
        "_event_data": {"label": consensus.label, "score": consensus.score},
    }

@evented("calibrate")
async def node_calibrate(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    consensus = state["consensus"]
    calibrator = state.get("calibrator")

    if consensus.label in ("BUY", "SELL"):
        conf = apply_calibrator(calibrator, consensus.raw_confidence)
        consensus.confidence = conf

    return {
        "consensus": consensus,
        "_event_data": {"confidence": consensus.confidence},
    }

@evented("write_brief")
async def node_write_brief(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    configurable = config.get("configurable", {})
    ctx = configurable.get("ctx")
    db = configurable.get("db") or (getattr(ctx, "db", None))

    snap = state["snapshot"]
    signals = state["signals"]
    consensus = state["consensus"]
    weights = state.get("weights", {})
    cross_checks = state.get("cross_checks", [])
    rounds = state.get("debate_rounds", [])
    d0 = state.get("initial_disagreement", 0.0)
    final_d = state.get("disagreement", 0.0)

    debate_record = Debate(
        triggered=len(rounds) > 0,
        initial_disagreement=round(d0, 4),
        final_disagreement=round(final_d, 4),
        cross_checks=cross_checks,
        rounds=rounds,
        summary=None,
    )

    brief = assemble_brief(snap, signals, consensus, debate_record, weights)

    # If use_llm is requested
    if state.get("use_llm", False):
        brief_input = {
            "symbol": brief.symbol,
            "company_name": brief.company_name,
            "sector": brief.sector,
            "as_of": str(brief.as_of),
            "consensus": {
                "label": consensus.label,
                "score": consensus.score,
                "confidence": consensus.confidence,
                "conflicted": consensus.conflicted,
                "flags": consensus.flags,
            },
            "agents": {
                name: {
                    "score": round(sig.score, 2),
                    "confidence": round(sig.confidence, 2),
                    "drivers": [{"note": d.note, "value": d.value} for d in sig.drivers],
                    "risks": sig.risks,
                    "flags": sig.flags,
                }
                for name, sig in signals.items()
            },
            "debate": {
                "triggered": debate_record.triggered,
                "initial_disagreement": debate_record.initial_disagreement,
                "final_disagreement": debate_record.final_disagreement,
                "cross_checks": [cc.message for cc in cross_checks],
                "rounds": [
                    {
                        "round": r.round,
                        "revisions": [
                            {"agent": rev.agent, "score_before": rev.score_before, "score_after": rev.score_after}
                            for rev in r.revisions
                        ],
                    }
                    for r in rounds
                ],
            },
            "top_news": [
                {"title": art["title"], "published_at": art["published_at"], "sentiment": art["sentiment"]}
                for art in signals.get("news", AgentSignal(agent="news", score=0, confidence=0)).meta.get("top_articles", [])[:5]
            ],
        }

        narrative, model_used = await narrate(brief_input, db=db)
        if narrative:
            fallback_note = "Narrative unavailable for this section."
            if "news" in brief.agents:
                brief.agents["news"].narrative = narrative.news if narrative.news is not None else fallback_note
            if "fundamentals" in brief.agents:
                brief.agents["fundamentals"].narrative = narrative.fundamentals if narrative.fundamentals is not None else fallback_note
            if "technicals" in brief.agents:
                brief.agents["technicals"].narrative = narrative.technicals if narrative.technicals is not None else fallback_note
            if "risk" in brief.agents:
                brief.agents["risk"].narrative = narrative.risk if narrative.risk is not None else fallback_note
            brief.debate.summary = narrative.debate_summary if narrative.debate_summary is not None else (fallback_note if debate_record.triggered else None)
            brief.summary = narrative.summary if narrative.summary is not None else fallback_note
            brief.meta.used_llm = True
            brief.meta.llm_model = model_used
            brief.meta.prompt_version = PROMPT_VERSION

    return {
        "brief": brief,
        "_event_data": {"used_llm": brief.meta.used_llm},
    }

@evented("persist")
async def node_persist(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
    configurable = config.get("configurable", {})
    ctx = configurable.get("ctx")
    db = configurable.get("db") or (getattr(ctx, "db", None))

    brief = state["brief"]
    consensus = brief.signal
    job_id = getattr(ctx, "job_id", None)
    if job_id is not None:
        from bullsutra.db.models.jobs import Job
        job_exists = await db.get(Job, job_id)
        if not job_exists:
            job_id = None

    # Insert research brief row
    brief_row = {
        "id": uuid.UUID(brief.id),
        "security_id": state["security_id"],
        "as_of": brief.as_of,
        "label": consensus.label,
        "consensus_score": consensus.score,
        "raw_confidence": consensus.raw_confidence,
        "confidence": consensus.confidence,
        "position_multiplier": consensus.position_multiplier,
        "conflicted": consensus.conflicted,
        "brief": brief.model_dump(mode="json"),
        "used_llm": brief.meta.used_llm,
        "job_id": job_id,
    }
    await insert_brief(db, brief_row)

    # Upsert the 4 agent signals with origin='live'
    sig_rows = []
    for a_name in ("news", "fundamentals", "technicals", "risk"):
        sig = brief.agents.get(a_name)
        if sig:
            sig_rows.append({
                "security_id": state["security_id"],
                "as_of": brief.as_of,
                "agent": a_name,
                "score": sig.score,
                "confidence": sig.confidence,
                "drivers": [d.model_dump(mode="json") for d in sig.drivers],
                "risks": sig.risks,
                "flags": sig.flags,
                "meta": sig.meta,
                "logic_version": LOGIC_VERSION,
                "origin": "live",
            })
    await upsert_signals(db, sig_rows)
    await db.commit()

    return {
        "brief_id": brief.id,
        "_event_data": {"brief_id": brief.id},
    }

NODES = {
    "load_context": node_load_context,
    "news": node_news,
    "fundamentals": node_fundamentals,
    "technicals": node_technicals,
    "risk": node_risk,
    "collect": node_collect,
    "debate": node_debate,
    "consensus": node_consensus,
    "calibrate": node_calibrate,
    "write_brief": node_write_brief,
    "persist": node_persist,
}
