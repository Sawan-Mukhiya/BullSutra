from starlette.requests import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from bullsutra.core.config import settings

def client_ip_or_principal(request: Request) -> str:
    # Check X-Forwarded-For if available
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request) or "127.0.0.1"

limiter = Limiter(
    key_func=client_ip_or_principal,
    default_limits=[settings.RATE_LIMIT_DEFAULT]
)
