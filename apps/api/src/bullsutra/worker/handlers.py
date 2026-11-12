from typing import Callable, Awaitable, Dict, Any
from bullsutra.worker.context import JobContext
from bullsutra.services import research_service, backtest_service
from bullsutra.pipelines import jobs as pipeline_jobs
from bullsutra.agents import jobs as agent_jobs
from bullsutra.backtest import jobs as backtest_jobs

HANDLERS: Dict[str, Callable[[JobContext], Awaitable[Dict[str, Any]]]] = {
    "research": research_service.run_research_job,
    "backtest": backtest_service.run_backtest_job,
    "eod_prices": pipeline_jobs.run_eod_prices,
    "news_scrape": pipeline_jobs.run_news_scrape_job,
    "news_score": pipeline_jobs.run_news_score,
    "fundamentals_import": pipeline_jobs.run_fundamentals_import,
    "signals_daily": agent_jobs.run_signals_daily,
    "weights_update": agent_jobs.run_weights_update,
    "signals_backfill": backtest_jobs.run_signals_backfill,
}
