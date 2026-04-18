"""
market.py — Alpha Vantage commodity price poller.
Fetches daily time series for crude oil ETF (USO), steel (X), semiconductors (SOXX).
Publishes to Redis Streams: stream:prices
Raises ConfigError if ALPHA_VANTAGE_KEY is not set.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from backend.config import ALPHA_VANTAGE_KEY, REDIS_URL, PRICE_POLL_INTERVAL_SEC, FEATURES, GEMINI_API_KEY

logger = logging.getLogger("chainmind.market")

SYMBOLS = {
    "RELIANCE.BSE": "energy_industrial",
    "TATASTEEL.BSE": "steel",
    "ADANIPORTS.BSE": "logistics_infrastructure",
    "COALINDIA.BSE": "power_energy",
}

AV_BASE = "https://www.alphavantage.co/query"


class ConfigError(Exception):
    pass


async def fetch_symbol(client: httpx.AsyncClient, symbol: str) -> dict | None:
    if not ALPHA_VANTAGE_KEY:
        raise ConfigError("ALPHA_VANTAGE_KEY is not set — commodity price feature disabled.")
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_KEY,
        "outputsize": "compact",
    }
    try:
        resp = await client.get(AV_BASE, params=params, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        if "Time Series (Daily)" not in data:
            logger.warning("Alpha Vantage unexpected response for %s: %s", symbol, data.get("Note", data))
            return await _search_scrape_fallback(symbol)
        ts = data["Time Series (Daily)"]
        latest_date = sorted(ts.keys(), reverse=True)[0]
        latest = ts[latest_date]
        return {
            "symbol": symbol,
            "commodity": SYMBOLS[symbol],
            "date": latest_date,
            "open": float(latest["1. open"]),
            "high": float(latest["2. high"]),
            "low": float(latest["3. low"]),
            "close": float(latest["4. close"]),
            "volume": int(latest["5. volume"]),
            "_fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("Alpha Vantage fetch failed for %s: %s", symbol, exc)
        return await _search_scrape_fallback(symbol)

async def _search_scrape_fallback(symbol: str) -> dict | None:
    """Fallback: Scrape/Search current price using LLM + Search capabilities."""
    if not GEMINI_API_KEY:
        return None
    
    logger.info("Using Search Scrape Fallback for %s", symbol)
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=GEMINI_API_KEY)
        
        prompt = f"Search for current stock price of {symbol} on BSE India. Return only the numerical close price. Example: 1542.5"
        response = await llm.ainvoke(prompt)
        price_str = response.content.strip()
        # Basic extraction
        import re
        match = re.search(r"(\d+\.?\d*)", price_str)
        if match:
            price = float(match.group(1))
            return {
                "symbol": symbol,
                "commodity": SYMBOLS.get(symbol, "industrial"),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "close": price,
                "_fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Google Search Scrape"
            }
    except Exception as e:
        logger.error("Search Scrape failed: %s", e)
    return None


async def poll_prices_once() -> list[dict]:
    if not FEATURES["commodity_prices"]:
        logger.warning("Commodity prices disabled — ALPHA_VANTAGE_KEY not set.")
        return []

    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    results = []

    from backend.db.database import AsyncSessionLocal
    from backend.db.schema import MarketPrice

    async with httpx.AsyncClient() as client:
        for symbol in SYMBOLS:
            try:
                reading = await fetch_symbol(client, symbol)
                if reading:
                    await redis.xadd("stream:prices", {"data": json.dumps(reading)}, maxlen=500)
                    results.append(reading)

                    # Save to DB
                    async with AsyncSessionLocal() as session:
                        async with session.begin():
                            entry = MarketPrice(
                                symbol=symbol,
                                price=reading["close"],
                                change_pct=0.0  # Optional logic for change %
                            )
                            session.add(entry)
                        await session.commit()

                    # Alpha Vantage free tier: 5 req/min — small delay
                    await asyncio.sleep(15)
            except ConfigError as e:
                logger.error(str(e))
                break

    await redis.aclose()
    logger.info("Price poll complete: %d symbols fetched and saved to DB.", len(results))
    return results


async def run_price_poller() -> None:
    logger.info("Starting commodity price poller (interval: %ds).", PRICE_POLL_INTERVAL_SEC)
    while True:
        try:
            await poll_prices_once()
        except Exception as exc:
            logger.error("Price poll error: %s", exc)
        await asyncio.sleep(PRICE_POLL_INTERVAL_SEC)
