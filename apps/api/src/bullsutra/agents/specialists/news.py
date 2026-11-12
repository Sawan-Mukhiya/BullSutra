"""News specialist agent."""
from datetime import datetime, timezone
import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from bullsutra.core.constants import (
    NEWS_DECAY_DAYS,
    NEWS_PRIOR,
    NEWS_SATURATION,
    NPT,
)
from bullsutra.core.time import cutoff_datetime, to_npt
from bullsutra.schemas.contracts import AgentSignal, Evidence
from bullsutra.agents.specialists._util import clip
from bullsutra.marketdata.base import MarketSnapshot

def news_signal(snap: MarketSnapshot) -> AgentSignal:
    """Calculate sentiment signal from snapshot news articles."""
    df = snap.news
    if df is None or df.empty:
        return AgentSignal(
            agent="news",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["no_news"],
            meta={"n_articles": 0, "weight_sum": 0.0, "mean_sentiment": 0.0, "std": 0.0, "top_articles": []},
        )

    cutoff = cutoff_datetime(snap.as_of)

    weights = []
    sentiments = []
    articles = []

    for _, row in df.iterrows():
        pub = row["published_at"]
        if isinstance(pub, str):
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        elif isinstance(pub, datetime):
            pub_dt = pub
        else:
            continue
        pub_npt = to_npt(pub_dt)

        if pub_npt > cutoff:
            continue

        age_seconds = (cutoff - pub_npt).total_seconds()
        if age_seconds < 0:
            continue
        age_days = age_seconds / 86400.0

        rel = float(row.get("relevance", 1.0) or 1.0)
        source_w = 1.0
        w = math.exp(-age_days / NEWS_DECAY_DAYS) * rel * source_w
        s = float(row.get("sentiment_score", 0.0) or 0.0)

        weights.append(w)
        sentiments.append(s)
        articles.append({
            "article_id": row.get("article_id", ""),
            "title": str(row.get("title", "")),
            "url": str(row.get("url", "")),
            "source": str(row.get("source", "")),
            "published_at": pub_npt,
            "weight": w,
            "sentiment": s,
            "abs_w_s": w * abs(s),
        })

    if not weights or sum(weights) == 0.0:
        return AgentSignal(
            agent="news",
            score=0.0,
            confidence=0.0,
            drivers=[],
            risks=[],
            flags=["no_news"],
            meta={"n_articles": 0, "weight_sum": 0.0, "mean_sentiment": 0.0, "std": 0.0, "top_articles": []},
        )

    w_arr = np.array(weights)
    s_arr = np.array(sentiments)
    sw = float(np.sum(w_arr))

    # score = Σ(w*s) / (sw + NEWS_PRIOR)
    score = float(np.sum(w_arr * s_arr) / (sw + NEWS_PRIOR))

    # m = Σ(w*s)/sw, std = sqrt(Σ w*(s-m)^2 / sw)
    m = float(np.sum(w_arr * s_arr) / sw)
    var = float(np.sum(w_arr * ((s_arr - m) ** 2)) / sw)
    std = math.sqrt(max(0.0, var))

    # confidence = clip(min(1, sw / NEWS_SATURATION) * (1 - 0.5*std), 0, 1)
    conf_base = min(1.0, sw / NEWS_SATURATION) * (1.0 - 0.5 * std)
    confidence = clip(conf_base, 0.0, 1.0)

    # Sort articles by w*abs(s) descending
    articles.sort(key=lambda a: a["abs_w_s"], reverse=True)

    # Drivers: top 3 articles
    drivers = []
    for art in articles[:3]:
        title = art["title"][:140]
        drivers.append(Evidence(
            kind="news",
            ref=f"article:{art['article_id']}",
            note=title,
            value=round(art["sentiment"], 4),
            url=art["url"] if art["url"] else None,
        ))

    risks = []
    if score < -0.3:
        risks.append("Recent news sentiment is negative")

    meta = {
        "n_articles": len(articles),
        "weight_sum": round(sw, 4),
        "mean_sentiment": round(m, 4),
        "std": round(std, 4),
        "top_articles": [
            {
                "article_id": a["article_id"],
                "title": a["title"],
                "url": a["url"],
                "published_at": a["published_at"].isoformat(),
                "sentiment": round(a["sentiment"], 4),
            }
            for a in articles[:5]
        ],
    }

    return AgentSignal(
        agent="news",
        score=float(round(score, 4)),
        confidence=float(round(confidence, 4)),
        drivers=drivers,
        risks=risks,
        flags=[],
        meta=meta,
    )
