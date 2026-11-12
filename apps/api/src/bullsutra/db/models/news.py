from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, Float, DateTime, ForeignKey,
    CheckConstraint, Index, func, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from bullsutra.db.base import Base

class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        CheckConstraint("source IN ('sharesansar', 'bizmandu')", name="ck_news_articles_source"),
        CheckConstraint("sentiment_score BETWEEN -1.0 AND 1.0", name="ck_news_articles_sentiment_score"),
        CheckConstraint("sentiment_label IN ('positive', 'neutral', 'negative')", name="ck_news_articles_sentiment_label"),
        Index("ix_news_articles_published_at_desc", text("published_at DESC")),
        Index("ix_news_articles_content_hash", "content_hash"),
        Index("ix_news_articles_unscored", "id", postgresql_where=text("sentiment_score IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(600), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    sentiment_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    duplicate_of: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("news_articles.id", ondelete="SET NULL"), nullable=True)

    duplicate_article: Mapped[Optional["NewsArticle"]] = relationship("NewsArticle", remote_side=[id])
    symbols: Mapped[list["NewsSymbol"]] = relationship("NewsSymbol", back_populates="article", cascade="all, delete-orphan")

class NewsSymbol(Base):
    __tablename__ = "news_symbols"
    __table_args__ = (
        CheckConstraint("match_method IN ('ticker', 'name', 'manual')", name="ck_news_symbols_match_method"),
        Index("ix_news_symbols_security_id", "security_id"),
    )

    article_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("news_articles.id", ondelete="CASCADE"), primary_key=True)
    security_id: Mapped[int] = mapped_column(Integer, ForeignKey("securities.id", ondelete="CASCADE"), primary_key=True)
    match_method: Mapped[str] = mapped_column(String(16), nullable=False, default="ticker")
    relevance: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    article: Mapped[NewsArticle] = relationship("NewsArticle", back_populates="symbols")
