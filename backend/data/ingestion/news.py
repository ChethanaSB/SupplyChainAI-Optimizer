"""
news.py — NewsAPI disruption signal ingestion + HuggingFace NER/sentiment scoring.
Fetches supply chain news, scores severity 1–5, extracts entities.
Publishes to Redis Streams: stream:news
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import redis.asyncio as aioredis

from backend.config import NEWSAPI_KEY, HF_API_TOKEN, REDIS_URL, NEWS_POLL_INTERVAL_SEC, FEATURES
from backend.data.ingestion.search_engine import search_engine

logger = logging.getLogger("chainmind.news")

NEWSAPI_BASE = "https://newsapi.org/v2/everything"
HF_SENTIMENT_URLS = [
    "https://api-inference.huggingface.co/models/distilbert-base-uncased-finetuned-sst-2-english",
    "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest",
    "https://api-inference.huggingface.co/models/ProsusAI/finbert"
]
HF_NER_URLS = [
    "https://api-inference.huggingface.co/models/dslim/bert-base-NER",
    "https://api-inference.huggingface.co/models/dslim/bert-large-NER",
    "https://api-inference.huggingface.co/models/Babelscape/wikineural-multilingual-ner"
]

SEARCH_QUERY = (
    "ZF India logistics OR ZF Pune plant disruption "
    "OR ZF Chennai production delay OR ZF Coimbatore industrial "
    "OR Indian automotive supply chain OR ZF mobility systems India "
    "OR global port congestion 2026 OR Suez Canal transit update "
    "OR Panama Canal drought impact OR major carrier blank sailings "
    "OR aerospace supply chain disruption"
)


async def _hf_request(client: httpx.AsyncClient, urls: list[str], payload: dict) -> Any:
    """Call HuggingFace Inference API with cascading fallbacks."""
    if not HF_API_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    for url in urls:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=15.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.debug("HuggingFace model %s failed: %s, attempting fallback...", url.split('/')[-1], exc)
            continue
            
    logger.warning("All HuggingFace fallback models exhausted.")
    return None


def _sentiment_to_score(sentiment_result: Any, text: str = "") -> tuple[float, str]:
    """Convert HF sentiment output to numerical score, with keyword fallback."""
    if not sentiment_result or not isinstance(sentiment_result, list):
        # Keyword-based fallback for supply chain sentiment
        lower_text = text.lower()
        negative_keywords = ["strike", "disruption", "delay", "hike", "bottleneck", "shortage", "closed", "accident", "warning", "storm", "flood"]
        positive_keywords = ["growth", "expansion", "profit", "digitalization", "improved", "connected", "opened", "launched"]
        
        if any(kw in lower_text for kw in negative_keywords):
            return 0.82, "NEGATIVE"
        if any(kw in lower_text for kw in positive_keywords):
            return 0.25, "POSITIVE"
            
        return 0.5, "NEUTRAL"
        
    best = max(sentiment_result, key=lambda x: x.get("score", 0))
    label = best.get("label", "NEUTRAL")
    score = best.get("score", 0.5)
    # For supply chain news: NEGATIVE sentiment = higher disruption severity
    if label == "NEGATIVE":
        return score, "NEGATIVE"
    return 1.0 - score, "POSITIVE"


def _severity_from_sentiment(sentiment_score: float) -> int:
    """Map 0–1 disruption sentiment score to severity 1–5."""
    if sentiment_score >= 0.85:
        return 5
    elif sentiment_score >= 0.70:
        return 4
    elif sentiment_score >= 0.55:
        return 3
    elif sentiment_score >= 0.35:
        return 2
    return 1


def _extract_entities_from_ner(ner_result: Any) -> list[str]:
    """Pull ORG/LOC entities from HF NER output."""
    if not ner_result or not isinstance(ner_result, list):
        return []
    entities = []
    for item in ner_result:
        if isinstance(item, dict) and item.get("entity_group") in ("ORG", "LOC", "PER"):
            word = item.get("word", "").strip()
            if word and len(word) > 2:
                entities.append(word)
    # Deduplicate
    return list(dict.fromkeys(entities))


async def fetch_and_score_news(client: httpx.AsyncClient) -> list[dict]:
    """Fetch articles from NewsAPI and score them."""
    if not FEATURES["news_feed"]:
        logger.warning("News feed disabled — NEWSAPI_KEY not set.")
        return []

    params = {
        "q": SEARCH_QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "from": (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat(),
        "apiKey": NEWSAPI_KEY,
    }

    try:
        resp = await client.get(NEWSAPI_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        logger.error("NewsAPI fetch failed: %s", exc)
        articles = []

    # ZF Enhancement: Use the highnd speed Google-like search engine for targeted results
    try:
        search_results = await search_engine.search(SEARCH_QUERY)
        # Add high-intent search results to the pool
        for sr in search_results:
            # Check for duplicates or priority
            if not any(a.get("title") == sr["title"] for a in articles):
                articles.insert(0, {
                    "title": sr["title"],
                    "description": sr["description"],
                    "source": {"name": sr["source"]},
                    "url": sr["url"],
                    "publishedAt": datetime.now(timezone.utc).isoformat()
                })
    except Exception as e:
        logger.warning("ZF Search Engine failed: %s", e)

    scored = []
    for article in articles:  # Process all articles
        text = f"{article.get('title', '')}. {article.get('description', '')}"
        if not text.strip():
            continue

        # Sentiment
        sentiment_raw = await _hf_request(client, HF_SENTIMENT_URLS, {"inputs": text[:512]})
        senti_score, senti_label = _sentiment_to_score(sentiment_raw, text=text)
        severity = _severity_from_sentiment(senti_score)

        # NER
        ner_raw = await _hf_request(client, HF_NER_URLS, {"inputs": text[:512]})
        entities = _extract_entities_from_ner(ner_raw)

        # Expiry: severity-based (high severity = longer impact)
        expiry_days = severity * 3
        expiry_date = (
            datetime.now(timezone.utc) + timedelta(days=expiry_days)
        ).isoformat()

        scored.append(
            {
                "title": article.get("title", ""),
                "summary": article.get("description", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
                "sentiment_label": senti_label,
                "sentiment_score": round(senti_score, 3),
                "severity": severity,
                "entities": entities,
                "expiry_date": expiry_date,
                "_fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return scored


async def poll_news_once() -> list[dict]:
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    async with httpx.AsyncClient() as client:
        articles = await fetch_and_score_news(client)

    from backend.db.database import AsyncSessionLocal
    from backend.db.schema import Disruption

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for article in articles:
                await redis.xadd("stream:news", {"data": json.dumps(article)}, maxlen=200)

                # Persist high-severity signals to DB as potential disruptions
                if article.get("severity", 0) >= 3:
                    dis = Disruption(
                        type="News Signal",
                        location=", ".join(article.get("entities", ["Global"])),
                        severity="High" if article["severity"] >= 4 else "Medium",
                        description=article["title"],
                        impact_score=article["sentiment_score"] * 100,
                        resolved=False
                    )
                    session.add(dis)
        await session.commit()

    await redis.aclose()
    logger.info("News poll complete: %d articles fetched and saved to DB.", len(articles))
    return articles


async def run_news_poller() -> None:
    logger.info("Starting news poller (interval: %ds).", NEWS_POLL_INTERVAL_SEC)
    while True:
        try:
            await poll_news_once()
        except Exception as exc:
            logger.error("News poll error: %s", exc)
        await asyncio.sleep(NEWS_POLL_INTERVAL_SEC)
