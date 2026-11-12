from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    progress: float
    payload: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

# Backward compat alias
JobResponse = JobOut

class JobEventResponse(BaseModel):
    seq: int
    event_type: str
    node: Optional[str] = None
    data: Dict[str, Any] = {}
    created_at: datetime
