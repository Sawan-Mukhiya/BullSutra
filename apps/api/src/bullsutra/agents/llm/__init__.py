"""LLM integration package."""
from bullsutra.agents.llm.schemas import BriefNarrative
from bullsutra.agents.llm.factory import get_llm, FakeNarrator
from bullsutra.agents.llm.narrate import narrate

__all__ = ["BriefNarrative", "get_llm", "FakeNarrator", "narrate"]
