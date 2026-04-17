"""
weather.py — Open-Meteo API poller.
Fetches hourly/daily weather for each supplier and plant location.
Publishes to Redis Streams: stream:weather
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from backend.config import OPENMETEO_BASE_URL, REDIS_URL, SUPPLIER_LOCATIONS, PLANT_LOCATIONS, WEATHER_POLL_INTERVAL_SEC

logger = logging.getLogger("chainmind.weather")

ALL_LOCATIONS = SUPPLIER_LOCATIONS + PLANT_LOCATIONS


async def fetch_weather_for_location(
    client: httpx.AsyncClient,
    loc: dict,
) -> dict | None:
    """Fetch 16-day forecast for a single location from Open-Meteo."""
    params = {
        "latitude": loc["lat"],
        "longitude": loc["lon"],
        "hourly": "temperature_2m,precipitation,wind_speed_10m,weather_code",
        "daily": "weather_code,precipitation_sum,wind_speed_10m_max,temperature_2m_max",
        "forecast_days": 16,
        "timezone": "UTC",
    }
    try:
        resp = await client.get(f"{OPENMETEO_BASE_URL}/forecast", params=params, timeout=15.0)
        resp.raise_for_status()
        data = resp.json()
        data["_location_id"] = loc["id"]
        data["_location_name"] = loc["name"]
        data["_fetched_at"] = datetime.now(timezone.utc).isoformat()

        # Derive severe_weather_flag: WMO codes 65+ indicate heavy precipitation/storms
        daily_codes = data.get("daily", {}).get("weather_code", [])
        data["severe_weather_flag"] = any(c >= 65 for c in daily_codes)

        return data
    except Exception as exc:
        logger.warning("Weather fetch failed for %s: %s", loc["id"], exc)
        return None


async def publish_to_stream(
    redis: aioredis.Redis, stream_key: str, payload: dict
) -> None:
    await redis.xadd(stream_key, {"data": json.dumps(payload)}, maxlen=1000)


async def poll_weather_once() -> list[dict]:
    """Single poll cycle — returns all location readings and saves to DB."""
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    results = []
    async with httpx.AsyncClient() as client:
        tasks = [fetch_weather_for_location(client, loc) for loc in ALL_LOCATIONS]
        readings = await asyncio.gather(*tasks)

    from backend.db.database import AsyncSessionLocal
    from backend.db.schema import WeatherCache

    async with AsyncSessionLocal() as session:
        async with session.begin():
            for reading in readings:
                if reading:
                    await publish_to_stream(redis, "stream:weather", reading)
                    results.append(reading)
                    # Persist to DB
                    cache_entry = WeatherCache(
                        location_id=reading["_location_id"],
                        data=reading
                    )
                    session.add(cache_entry)
        await session.commit()

    await redis.aclose()
    logger.info("Weather poll complete: %d/%d locations fetched and saved to DB.", len(results), len(ALL_LOCATIONS))
    return results


async def run_weather_poller() -> None:
    """Continuous poller — runs every WEATHER_POLL_INTERVAL_SEC seconds."""
    logger.info("Starting weather poller (interval: %ds).", WEATHER_POLL_INTERVAL_SEC)
    while True:
        try:
            await poll_weather_once()
        except Exception as exc:
            logger.error("Weather poll error: %s", exc)
        await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(poll_weather_once())
