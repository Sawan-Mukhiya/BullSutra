from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class UploadRowError(BaseModel):
    row: int
    field: str
    message: str

class UploadOut(BaseModel):
    id: str
    upload_type: str
    filename: str
    status: str
    row_count: int
    error_count: int
    errors: List[Dict[str, Any]] = []
    preview: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    committed_at: Optional[datetime] = None

# Backward compat alias
UploadResponse = UploadOut
