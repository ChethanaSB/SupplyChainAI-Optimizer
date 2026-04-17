"""
stream_bus.py — Redis Streams publisher utilities and consumer helpers.
"""
import json
import logging
from typing import Any, AsyncGenerator

import redis.asyncio as aioredis

from backend.config import REDIS_URL

logger = logging.getLogger("chainmind.stream_bus")

STREAM_KEYS = {
    "weather": "stream:weather",
    "prices": "stream:prices",
    "ports": "stream:ports",
    "news": "stream:news",
    "erp": "stream:erp",
}


class StreamBus:
    """Async Redis Streams publisher/consumer."""

    def __init__(self, url: str = REDIS_URL):
        self._url = url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = aioredis.from_url(self._url, decode_responses=True)

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()

    async def publish(self, stream: str, payload: dict, maxlen: int = 1000) -> None:
        if not self._redis:
            await self.connect()
        key = STREAM_KEYS.get(stream, stream)
        await self._redis.xadd(key, {"data": json.dumps(payload)}, maxlen=maxlen)

    async def read_latest(self, stream: str, count: int = 10) -> list[dict]:
        """Read latest N messages from a stream."""
        if not self._redis:
            await self.connect()
        key = STREAM_KEYS.get(stream, stream)
        entries = await self._redis.xrevrange(key, count=count)
        results = []
        for entry_id, fields in entries:
            try:
                data = json.loads(fields.get("data", "{}"))
                data["_stream_id"] = entry_id
                results.append(data)
            except json.JSONDecodeError:
                pass
        return results

    async def consume_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> AsyncGenerator[dict, None]:
        """Consumer group reader — yields individual messages."""
        if not self._redis:
            await self.connect()
        key = STREAM_KEYS.get(stream, stream)

        # Create group if not exists
        try:
            await self._redis.xgroup_create(key, group, id="$", mkstream=True)
        except Exception:
            pass  # Group already exists

        while True:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={key: ">"},
                    count=count,
                    block=block_ms,
                )
                if messages:
                    for _, entries in messages:
                        for entry_id, fields in entries:
                            try:
                                data = json.loads(fields.get("data", "{}"))
                                data["_stream_id"] = entry_id
                                yield data
                                await self._redis.xack(key, group, entry_id)
                            except json.JSONDecodeError:
                                pass
            except Exception as exc:
                logger.error("Stream consume error: %s", exc)
                break


# Singleton for app-wide use
bus = StreamBus()
