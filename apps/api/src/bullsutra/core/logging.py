import contextvars
import logging
import sys
import structlog
from bullsutra.core.config import settings

request_id_ctx = contextvars.ContextVar("request_id", default=None)
job_id_ctx = contextvars.ContextVar("job_id", default=None)

def add_context_vars(logger, method_name, event_dict):
    req_id = request_id_ctx.get()
    if req_id:
        event_dict["request_id"] = req_id
    j_id = job_id_ctx.get()
    if j_id:
        event_dict["job_id"] = j_id
    return event_dict

def setup_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        add_context_vars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.ENV == "local":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                send_default_pii=False,
                traces_sample_rate=0.1,
            )
        except Exception:
            pass

def get_logger(name: str = "bullsutra"):
    return structlog.get_logger(name)
