from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from sqlalchemy import select, update, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from bullsutra.core.time import cutoff_datetime
from bullsutra.db.models.news import NewsArticle, NewsSymbol

async def get_news_asof(
    db: AsyncSession,
    security_id: int,
    as_of: date,
    window_days: int = 14
) -> pd.DataFrame:
    cutoff = cutoff_datetime(as_of)
    start_time = cutoff - timedelta(days=window_days)

    stmt = select(
        NewsArticle.id.label("article_id"),
        NewsArticle.title,
        NewsArticle.url,
        NewsArticle.source,
        NewsArticle.published_at,
        NewsArticle.sentiment_score,
        NewsSymbol.relevance,
    ).join(
        NewsSymbol, NewsArticle.id == NewsSymbol.article_id
    ).where(
        NewsSymbol.security_id == security_id,
        NewsArticle.published_at > start_time,
        NewsArticle.published_at <= cutoff,
        NewsArticle.duplicate_of.is_(None),
        NewsArticle.sentiment_score.is_not(None)
    ).order_by(NewsArticle.published_at.desc())

    res = await db.execute(stmt)
    rows = res.fetchall()
    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([dict(r._mapping) for r in rows])

async def insert_articles(db: AsyncSession, rows: List[Dict[str, Any]]) -> List[int]:
    if not rows:
        return []
    stmt = insert(NewsArticle).values(rows).on_conflict_do_nothing(index_elements=["url"]).returning(NewsArticle.id)
    res = await db.execute(stmt)
    return [r[0] for r in res.fetchall()]

async def get_unscored_articles(db: AsyncSession, limit: int = 100) -> List[NewsArticle]:
    stmt = select(NewsArticle).where(
        NewsArticle.sentiment_score.is_(None)
    ).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())

async def set_sentiment(db: AsyncSession, updates: List[Dict[str, Any]]) -> int:
    count = 0
    for u in updates:
        stmt = update(NewsArticle).where(
            NewsArticle.id == u["id"]
        ).values(
            sentiment_score=u.get("sentiment_score"),
            sentiment_label=u.get("sentiment_label"),
            sentiment_model=u.get("sentiment_model"),
            embedding_id=u.get("embedding_id")
        )
        res = await db.execute(stmt)
        count += res.rowcount
    return count

async def link_symbols(db: AsyncSession, links: List[Dict[str, Any]]) -> int:
    if not links:
        return 0
    stmt = insert(NewsSymbol).values(links).on_conflict_do_nothing(
        index_elements=["article_id", "security_id"]
    )
    res = await db.execute(stmt)
    return res.rowcount

async def mark_duplicate(db: AsyncSession, article_id: int, duplicate_of: int) -> None:
    stmt = update(NewsArticle).where(NewsArticle.id == article_id).values(duplicate_of=duplicate_of)
    await db.execute(stmt)

async def get_all_scored_news(db: AsyncSession, security_ids: List[int]) -> pd.DataFrame:
    stmt = select(
        NewsArticle.id.label("article_id"),
        NewsSymbol.security_id,
        NewsArticle.title,
        NewsArticle.published_at,
        NewsArticle.sentiment_score,
        NewsSymbol.relevance
    ).join(
        NewsSymbol, NewsArticle.id == NewsSymbol.article_id
    ).where(
        NewsSymbol.security_id.in_(security_ids),
        NewsArticle.duplicate_of.is_(None),
        NewsArticle.sentiment_score.is_not(None)
    ).order_by(NewsArticle.published_at.asc())

    res = await db.execute(stmt)
    rows = res.fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r._mapping) for r in rows])
