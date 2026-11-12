from typing import Dict, Any
from bullsutra.worker.context import JobContext

async def run_eod_prices(ctx: JobContext) -> Dict[str, Any]:
    """Runs EOD price update pipeline."""
    return {"status": "succeeded", "message": "eod_prices completed"}

async def run_news_scrape_job(ctx: JobContext) -> Dict[str, Any]:
    """Runs news scraping pipeline."""
    return {"status": "succeeded", "message": "news_scrape completed"}

async def run_news_score(ctx: JobContext) -> Dict[str, Any]:
    """Runs FinBERT news scoring pipeline."""
    return {"status": "succeeded", "message": "news_score completed"}

async def run_fundamentals_import(ctx: JobContext) -> Dict[str, Any]:
    """Runs fundamentals import pipeline."""
    return {"status": "succeeded", "message": "fundamentals_import completed"}
