"""LLM narrative schemas."""
from typing import Optional
from pydantic import BaseModel

class BriefNarrative(BaseModel):
    news: Optional[str] = None
    fundamentals: Optional[str] = None
    technicals: Optional[str] = None
    risk: Optional[str] = None
    debate_summary: Optional[str] = None     # null when debate was not triggered
    summary: Optional[str] = None            # 3 to 5 sentences
