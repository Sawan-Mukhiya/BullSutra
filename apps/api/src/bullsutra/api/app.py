import traceback
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import structlog

from bullsutra.core.config import settings
from bullsutra.core.errors import AppError
from bullsutra.core.logging import request_id_ctx, setup_logging
from bullsutra.api.ratelimit import limiter
from bullsutra.api.middleware import (
    RequestIdMiddleware,
    AccessLogMiddleware,
    SecurityHeadersMiddleware,
)
from bullsutra.api.routers import (
    auth,
    securities,
    research,
    agents,
    backtest,
    uploads,
    exports,
    admin,
    jobs,
    health,
)

logger = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    # Setup structured logging
    setup_logging()

    # Optional Sentry initialization
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                send_default_pii=False,
                traces_sample_rate=0.1
            )
        except Exception as e:
            logger.warning("sentry_init_failed", error=str(e))

    app = FastAPI(
        title="BullSutra API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        generate_unique_id_function=lambda route: route.name,
    )

    # Attach rate limiter state
    app.state.limiter = limiter

    # Exception Handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        req_id = request_id_ctx.get()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": req_id,
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        req_id = request_id_ctx.get()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Validation error",
                    "details": {"errors": exc.errors()},
                    "request_id": req_id,
                }
            }
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        req_id = request_id_ctx.get()
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": "Rate limit exceeded",
                    "details": None,
                    "request_id": req_id,
                }
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = request_id_ctx.get()
        logger.error("internal_server_error", exc_info=True, request_id=req_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "details": None,
                    "request_id": req_id,
                }
            }
        )

    # Middlewares (executed in reverse registration order: RequestId -> AccessLog -> SecurityHeaders -> CORS -> App)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
        allow_credentials=False,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(SlowAPIMiddleware)

    # API Routers under /api/v1
    api_v1 = FastAPI(title="BullSutra API v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(securities.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(backtest.router, prefix="/api/v1")
    app.include_router(uploads.router, prefix="/api/v1")
    app.include_router(exports.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(jobs.router, prefix="/api/v1")
    app.include_router(health.router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {"name": "BullSutra API", "version": "1.0.0"}

    return app
