from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel
from bullsutra.schemas.contracts import Label

class BriefSummary(BaseModel):
    id: str
    symbol: str
    company_name: str
    as_of: date
    label: Label
    score: float
    confidence: float
    conflicted: bool
    used_llm: bool
    generated_at: datetime

class BriefSummaryList(BaseModel):
    items: List[BriefSummary]

class RunResearchRequest(BaseModel):
    symbol: str
    as_of: Optional[date] = None
    use_llm: bool = True
