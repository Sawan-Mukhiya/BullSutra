"""LangGraph compilation for research brief workflow."""
from langgraph.graph import StateGraph, START, END
from bullsutra.core.constants import DEBATE_TAU, DEBATE_MAX_ROUNDS
from bullsutra.agents.graph.state import BriefState
from bullsutra.agents.graph.nodes import NODES

TAU = DEBATE_TAU
MAX_ROUNDS = DEBATE_MAX_ROUNDS

def route(state: BriefState) -> str:
    dis = state.get("disagreement", 0.0)
    rounds = state.get("debate_rounds", [])
    if dis > TAU and len(rounds) < MAX_ROUNDS:
        return "debate"
    return "consensus"

def build_graph():
    g = StateGraph(BriefState)
    for name, fn in NODES.items():
        g.add_node(name, fn)
    
    g.add_edge(START, "load_context")
    for a in ("news", "fundamentals", "technicals", "risk"):
        g.add_edge("load_context", a)
        g.add_edge(a, "collect")

    g.add_conditional_edges(
        "collect",
        route,
        {"debate": "debate", "consensus": "consensus"}
    )
    g.add_conditional_edges(
        "debate",
        route,
        {"debate": "debate", "consensus": "consensus"}
    )
    g.add_edge("consensus", "calibrate")
    g.add_edge("calibrate", "write_brief")
    g.add_edge("write_brief", "persist")
    g.add_edge("persist", END)

    return g.compile()

GRAPH = build_graph()
