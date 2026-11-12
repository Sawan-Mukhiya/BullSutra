import asyncio
import signal
import sys
import structlog

from bullsutra.core.config import settings
from bullsutra.core.logging import setup_logging
from bullsutra.worker.runner import WorkerRunner
from bullsutra.worker.scheduler import build_scheduler

logger = structlog.get_logger(__name__)

async def main():
    setup_logging()
    logger.info("starting_bullsutra_worker", env=settings.ENV)

    runner = WorkerRunner()
    await runner.start()

    scheduler = None
    if settings.ENABLE_SCHEDULER:
        logger.info("enabling_scheduler")
        scheduler = build_scheduler()
        scheduler.start()

    stop_event = asyncio.Event()

    def handle_signal():
        logger.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for s in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(s, handle_signal)
    else:
        # On Windows, signal handlers can be set via signal.signal
        signal.signal(signal.SIGINT, lambda sig, frame: stop_event.set())
        signal.signal(signal.SIGTERM, lambda sig, frame: stop_event.set())

    await stop_event.wait()

    if scheduler:
        logger.info("shutting_down_scheduler")
        scheduler.shutdown(wait=False)

    await runner.stop()
    logger.info("bullsutra_worker_stopped_cleanly")

if __name__ == "__main__":
    asyncio.run(main())
