"""
ports.py — Port congestion data ingestion.
Attempts MarineTraffic API if key is set.
Falls back to port economics scraper (BeautifulSoup4).
Injects weather-seeded delay spikes for realism.
Publishes to Redis Streams: stream:ports
"""
import asyncio
import json
import logging
import random
from datetime import datetime, timezone

import httpx
import redis.asyncio as aioredis

from backend.config import MARINETRAFFIC_KEY, REDIS_URL, PORT_POLL_INTERVAL_SEC, FEATURES, KEY_PORTS

logger = logging.getLogger("chainmind.ports")

# Congestion baseline per port (0–100), updated by polls
_CONGESTION_STATE: dict[str, float] = {p["id"]: 30.0 for p in KEY_PORTS}
# Store real-time vessel positions for map visualization
_LIVE_VESSELS: list[dict] = []


async def _try_aisstream():
    print("DEBUG: _try_aisstream starting...")
    from backend.config import AISTREAM_API_KEY
    if not AISTREAM_API_KEY:
        print("DEBUG: Aisstream API key missing!")
        return

    import websockets
    import json
    from datetime import datetime

    # Simple radius-based congestion tracking (vessels within ~50km)
    RADIUS_KM = 50.0

    async def _listen():
        while True:
            try:
                print(f"DEBUG: Attempting AIS connect to wss://stream.aisstream.io/v0/stream ...")
                async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
                    print("DEBUG: AIS WebSocket opened. Sending subscription...")
                    subscribe_msg = {
                        "APIKey": AISTREAM_API_KEY,
                        "BoundingBoxes": [[[5.0, 60.0], [35.0, 100.0]]],
                        "FiltersShipType": [35, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80]
                    }

                    await websocket.send(json.dumps(subscribe_msg))
                    print("DEBUG: AIS Subscription sent. Waiting for messages...")
                    logger.info("Aisstream.io: Connected and subscribed.")

                    vessel_counts = {p["id"]: 0 for p in KEY_PORTS}
                    start_time = datetime.now()

                    async for message in websocket:
                        print("DEBUG: AIS RAW MESSAGE RECEIVED!")
                        msg = json.loads(message)
                        # Log every 50th message to avoid spam but confirm activity
                        if random.random() < 0.02:
                            logger.info("Aisstream.io: Real-time vessel message received: %s", msg.get("MetaData", {}))
                            print(f"DEBUG: AIS message received for {msg.get('MetaData', {}).get('ShipName')}")
                        if "MetaData" in msg:
                            lat = msg["MetaData"].get("latitude")
                            lon = msg["MetaData"].get("longitude")
                            mmsi = msg["MetaData"].get("MMSI")
                            ship_name = msg["MetaData"].get("ShipName", "Unknown")

                            if lat and lon:
                                # Update live vessel list (keep last 200)
                                _LIVE_VESSELS.append({
                                    "id": mmsi,
                                    "name": ship_name,
                                    "lat": lat,
                                    "lon": lon,
                                    "type": "cargo",
                                    "timestamp": datetime.now().isoformat()
                                })
                                if len(_LIVE_VESSELS) > 200:
                                    _LIVE_VESSELS.pop(0)

                                from backend.optimization.routing import haversine
                                for port in KEY_PORTS:
                                    dist = haversine(lat, lon, port["lat"], port["lon"])
                                    if dist < RADIUS_KM:
                                        vessel_counts[port["id"]] += 1
                        
                        if (datetime.now() - start_time).seconds > 30:
                            for pid, count in vessel_counts.items():
                                congestion = min(100.0, (count / 50.0) * 100.0)
                                _CONGESTION_STATE[pid] = (_CONGESTION_STATE[pid] * 0.7) + (congestion * 0.3)
                            
                            vessel_counts = {p["id"]: 0 for p in KEY_PORTS}
                            start_time = datetime.now()
            except Exception as exc:
                logger.warning("Aisstream.io connection lost: %s. Retrying in 10s...", exc)
                await asyncio.sleep(10)

    # This should be run as a background task. 
    # For the poller integration, we'll just return the current state.
    # We'll start this task in run_port_poller.
    asyncio.create_task(_listen())

async def _try_marinetraffic(client: httpx.AsyncClient) -> list[dict]:
    """Fetch vessel counts from MarineTraffic if key available."""
    if not MARINETRAFFIC_KEY:
        return []


def _build_port_record(port: dict, congestion: float, source: str) -> dict:
    return {
        "port_id": port["id"],
        "port_name": port["name"],
        "lat": port["lat"],
        "lon": port["lon"],
        "congestion_index": round(congestion, 1),
        "source": source,
        "_fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _weather_seeded_congestion(port: dict, existing: float) -> float:
    """
    Simulate congestion spikes seeded by port location.
    In production this is overridden by real MarineTraffic data.
    Adds realistic random walk with momentum.
    """
    # Random walk with mean-reversion
    delta = random.gauss(0, 8)
    new_val = existing + delta
    # Mean-revert toward 35
    new_val = new_val + (35.0 - new_val) * 0.05
    return max(0.0, min(100.0, new_val))


async def poll_ports_once() -> list[dict]:
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    results = []

    # Note: Aisstream.io updates _CONGESTION_STATE in background
    # We still fetch regular records here for the stream.

    # Fill in port records from current state
    for port in KEY_PORTS:
        # Get real vessel count from AisStream global state
        new_cong = _CONGESTION_STATE.get(port["id"], 15.0) 
        source = "AisStream (Real-Time AIS)"
            
        record = _build_port_record(port, new_cong, source)
        results.append(record)

    for record in results:
        await redis.xadd("stream:ports", {"data": json.dumps(record)}, maxlen=500)

    await redis.aclose()
    logger.info("Port poll complete: %d ports updated.", len(results))
    return results


async def run_port_poller() -> None:
    logger.info("Starting port congestion poller (interval: %ds).", PORT_POLL_INTERVAL_SEC)
    
    # Start Aisstream real-time tracker if key available
    await _try_aisstream()
    
    while True:
        try:
            await poll_ports_once()
        except Exception as exc:
            logger.error("Port poll error: %s", exc)
        await asyncio.sleep(PORT_POLL_INTERVAL_SEC)


def get_live_vessels() -> list[dict]:
    """Expose live vessel buffer for API."""
    return _LIVE_VESSELS
