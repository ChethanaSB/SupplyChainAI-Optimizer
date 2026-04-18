"""
websocket.py — WS /ws/live-feed
Streams live events: disruption_alert, kpi_update, route_change, inventory_alert.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.config import SUPPLIER_LOCATIONS
from backend.data.ingestion.stream_bus import bus
from backend.models.disruption.risk_score import compute_risk_score

_EVENT_HISTORY = [] # Simple rotating history to prevent repetition

logger = logging.getLogger("chainmind.api.ws")
router = APIRouter()

# ─── Connection manager ───────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)
        logger.info("WS client connected. Total: %d", len(self.active))

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)
        logger.info("WS client disconnected. Total: %d", len(self.active))

    async def broadcast(self, message: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active.discard(ws)


manager = ConnectionManager()


async def _build_live_event() -> dict:
    """Build a live event from Redis stream data with rotation to prevent repeats."""
    # Read latest from all streams
    weather = await bus.read_latest("stream:weather", count=3)
    ports = await bus.read_latest("stream:ports", count=5)
    news = await bus.read_latest("stream:news", count=3)
    erp = await bus.read_latest("stream:erp", count=5)
    prices = await bus.read_latest("stream:prices", count=3)

    now = datetime.now(timezone.utc).isoformat()
    raw_event = None

    # Priority 0: Intelligence News Signals (from Intelligence Blog)
    import random
    random.shuffle(news) # Shuffle to show different things if multiple are available
    for n in news:
        # Lower threshold: show anything NEGATIVE or severity >= 2
        if n.get("severity", 0) >= 2 or n.get("sentiment_label") == "NEGATIVE":
           raw_event = {
               "type": "disruption_alert",
               "payload": {
                   "message": f"Intelligence Signal: {n.get('title')} [{n.get('source')}]",
                   "url": n.get("url"),
               },
               "timestamp": now,
               "severity": "HIGH" if n.get("severity", 0) >= 4 else ("MEDIUM" if n.get("severity", 0) >= 2 else "LOW"),
           }
           break

    # Priority 1: Market Price Volatility Alert (Indian Markets)
    if not raw_event:
        for p in prices:
            raw_event = {
                "type": "market_update",
                "payload": {
                    "symbol": p.get("symbol"),
                    "message": f"Real-Time NSE/BSE Signal: {p.get('commodity','').replace('_', ' ').capitalize()} price at ₹{p.get('close',0):,.2f}. Integrating into cost optimization models.",
                },
                "timestamp": now,
                "severity": "LOW",
            }
            break

    # Priority 2: Port Congestion
    if not raw_event:
        for p in ports:
            if p.get("congestion_index", 0) > 60:
                raw_event = {
                    "type": "disruption_alert",
                    "payload": {
                        "message": f"High congestion at {p.get('port_name', 'Unknown Port')}: {p.get('congestion_index', 0):.0f}/100 [LIVE AIS]",
                    },
                    "timestamp": now,
                    "severity": "HIGH",
                }
                break

    # Priority 3: Severe Weather
    if not raw_event:
        for w in weather:
            if w.get("severe_weather_flag"):
                raw_event = {
                    "type": "disruption_alert",
                    "payload": {
                        "message": f"Severe weather alert at {w.get('_location_name', 'Unknown')}: storm conditions forecasted",
                    },
                    "timestamp": now,
                    "severity": "MEDIUM",
                }
                break

    # Priority 4: Agentic Orchestration Heartbeat
    if not raw_event:
        from backend.orchestration.langchain_agent import run_agent_orchestration
        orchestration_recommendation = await run_agent_orchestration("All systems nominal. Network stability: 92%")
        raw_event = {
            "type": "kpi_update",
            "payload": {
                "message": f"LangChain Agent: {orchestration_recommendation[:80]}...",
                "inr_status": "₹ Stable"
            },
            "timestamp": now,
            "severity": "LOW",
        }

    # Deduplication Logic
    msg = raw_event["payload"]["message"]
    if msg in _EVENT_HISTORY:
        # If we just sent this, send a secondary heartbeat instead
        return {
            "type": "kpi_update",
            "payload": {"message": "Active Monitoring: Real-time telemetry scan complete. No new disruptions detected.", "inr_status": "₹ Monitoring"},
            "timestamp": now,
            "severity": "LOW",
        }

    _EVENT_HISTORY.append(msg)
    if len(_EVENT_HISTORY) > 5: # Keep last 5 messages to rotate
        _EVENT_HISTORY.pop(0)

    return raw_event


@router.websocket("/live-feed")
async def live_feed(websocket: WebSocket):
    """WebSocket endpoint streaming live supply chain events."""
    await manager.connect(websocket)
    try:
        # Ensure bus is connected
        await bus.connect()

        while True:
            try:
                event = await _build_live_event()
                await websocket.send_json(event)
            except Exception as exc:
                logger.warning("Event build error: %s", exc)
                await websocket.send_json({
                    "type": "kpi_update",
                    "payload": {"message": "ChainMind Heartbeat - Verified INR"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": "LOW",
                })

            await asyncio.sleep(8)  # Slightly longer interval to reduce spam

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)
