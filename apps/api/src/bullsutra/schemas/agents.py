from datetime import date
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel

class RunRequest(BaseModel):
    symbol: str
    as_of: Optional[date] = None
    use_llm: bool = True
    force: bool = False

# Backward-compat alias if needed
AgentRunRequest = RunRequest

class RunResponse(BaseModel):
    status: Literal["queued", "cached"]
    job_id: Optional[str] = None
    brief_id: Optional[str] = None
    events_url: Optional[str] = None

class WeightsOut(BaseModel):
    fitted_on: Optional[date] = None
    weights: Dict[str, float]
    metrics: Dict[str, Any]
    calibrator_available: bool

# Backward-compat alias if needed
AgentWeightsResponse = WeightsOut

class CalibrationOut(BaseModel):
    fitted_on: Optional[date] = None
    n_samples: int
    brier_score: Optional[float] = None
    bins: List[Dict[str, Any]]
