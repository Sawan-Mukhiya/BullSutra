"""AppError hierarchy and error definitions."""
from typing import Any, Dict, Optional

class AppError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details

class NotFound(AppError):
    status_code = 404
    code = "not_found"

class BriefNotFound(AppError):
    status_code = 404
    code = "brief_not_found"

class SymbolNotFound(AppError):
    status_code = 404
    code = "symbol_not_found"

class NotInUniverse(AppError):
    status_code = 409
    code = "not_in_universe"

class Conflict(AppError):
    status_code = 409
    code = "conflict"

class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"

class Forbidden(AppError):
    status_code = 403
    code = "forbidden"

class UpstreamUnavailable(AppError):
    status_code = 503
    code = "upstream_unavailable"

class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"

class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
