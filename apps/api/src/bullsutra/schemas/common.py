from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
