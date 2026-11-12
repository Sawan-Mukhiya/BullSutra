import structlog
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bullsutra.core.config import settings
from bullsutra.db.session import async_session_factory
from bullsutra.db.repositories import jobs
from bullsutra.pipelines.freshness import data_freshness

logger = structlog.get_logger(__name__)

async def scheduled_enqueue(kind: str, payload: Dict[str, Any]):
    async with async_session_factory() as session:
        job = await jobs.enqueue_if_absent(session, kind=kind, payload=payload)
        await session.commit()
        if job:
            logger.info("scheduled_job_enqueued", kind=kind, payload=payload, job_id=str(job.id))
        else:
            logger.debug("scheduled_job_already_present", kind=kind, payload=payload)

async def check_freshness_inline():
    async with async_session_factory() as session:
        f = await data_freshness(session)
        logger.info("scheduled_freshness_check", freshness=f)

def build_scheduler() -> AsyncIOScheduler:
    tz = "Asia/Kathmandu"
    scheduler = AsyncIOScheduler(timezone=tz)
    cron_kwargs = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 600,
    }

    # eod_prices at 15:30, 15:50, 16:10
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=30, timezone=tz),
        id="eod_1530",
        args=["eod_prices", {}],
        **cron_kwargs
    )
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=15, minute=50, timezone=tz),
        id="eod_1550",
        args=["eod_prices", {}],
        **cron_kwargs
    )
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=16, minute=10, timezone=tz),
        id="eod_1610",
        args=["eod_prices", {}],
        **cron_kwargs
    )

    # news_live: hour 10-16 minute 0,30 plus 17:00
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour="10-16", minute="0,30", timezone=tz),
        id="news_live",
        args=["news_scrape", {"mode": "live"}],
        **cron_kwargs
    )
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=17, minute=0, timezone=tz),
        id="news_live_1700",
        args=["news_scrape", {"mode": "live"}],
        **cron_kwargs
    )

    # news_evening: 20:00
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=20, minute=0, timezone=tz),
        id="news_evening",
        args=["news_scrape", {"mode": "live"}],
        **cron_kwargs
    )

    # signals_daily: 16:30
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=16, minute=30, timezone=tz),
        id="signals_daily",
        args=["signals_daily", {}],
        **cron_kwargs
    )

    # weights_update: 17:00
    scheduler.add_job(
        scheduled_enqueue,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=17, minute=0, timezone=tz),
        id="weights_update",
        args=["weights_update", {}],
        **cron_kwargs
    )

    # freshness_check: 17:15
    scheduler.add_job(
        check_freshness_inline,
        CronTrigger(day_of_week="sun,mon,tue,wed,thu", hour=17, minute=15, timezone=tz),
        id="freshness_check",
        **cron_kwargs
    )

    return scheduler
