from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.db.models.prices import DailyBar
from bullsutra.db.models.news import NewsArticle
from bullsutra.db.models.fundamentals import QuarterlyFinancial

async def data_freshness(db: AsyncSession) -> Dict[str, Any]:
    latest_price = (await db.execute(select(func.max(DailyBar.trade_date)))).scalar()
    latest_news = (await db.execute(select(func.max(NewsArticle.published_at)))).scalar()
    latest_fund = (await db.execute(select(func.max(QuarterlyFinancial.usable_from)))).scalar()

    return {
        "status": "ok",
        "prices_latest": latest_price.isoformat() if latest_price else None,
        "news_latest": latest_news.isoformat() if latest_news else None,
        "fundamentals_latest": latest_fund.isoformat() if latest_fund else None,
    }
