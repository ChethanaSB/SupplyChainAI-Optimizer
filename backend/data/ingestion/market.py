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

from backend.config import ALPHA_VANTAGE_KEY, REDIS_URL, PRICE_POLL_INTERVAL_SEC, FEATURES

logger = logging.getLogger("chainmind.market")

SYMBOLS = {
    "USO": "crude_oil",
    "X": "steel",
    "SOXX": "semiconductors",
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
            return None
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
    except ConfigError:
        raise
    except Exception as exc:
        logger.warning("Alpha Vantage fetch failed for %s: %s", symbol, exc)
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
