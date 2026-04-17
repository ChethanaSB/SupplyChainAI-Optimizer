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
    """Build a live event from Redis stream data."""
    # Read latest from all streams
    weather = await bus.read_latest("stream:weather", count=3)
    ports = await bus.read_latest("stream:ports", count=5)
    news = await bus.read_latest("stream:news", count=3)
    erp = await bus.read_latest("stream:erp", count=5)

    now = datetime.now(timezone.utc).isoformat()

    # Check for high-risk port
    for p in ports:
        if p.get("congestion_index", 0) > 70:
            return {
                "type": "disruption_alert",
                "payload": {
                    "port_id": p.get("port_id"),
                    "port_name": p.get("port_name"),
                    "congestion_index": p.get("congestion_index"),
                    "source": p.get("source"),
                    "message": f"High congestion at {p.get('port_name', 'Unknown Port')}: "
                               f"{p.get('congestion_index', 0):.0f}/100",
                },
                "timestamp": now,
                "severity": "HIGH",
            }

    # Check for severe weather
    for w in weather:
        if w.get("severe_weather_flag"):
            return {
                "type": "disruption_alert",
                "payload": {
                    "location": w.get("_location_name"),
                    "message": f"Severe weather alert at {w.get('_location_name', 'Unknown')}: "
                               f"storm conditions forecasted",
                    "source": "Open-Meteo",
                },
                "timestamp": now,
                "severity": "MEDIUM",
            }

    # Check for high-severity news
    for n in news:
        if n.get("severity", 0) >= 4:
            return {
                "type": "disruption_alert",
                "payload": {
                    "title": n.get("title", ""),
                    "source": n.get("source", ""),
                    "severity": n.get("severity"),
                    "entities": n.get("entities", []),
                    "message": f"High-severity disruption news: {n.get('title', '')[:80]}",
                },
                "timestamp": now,
                "severity": "HIGH" if n.get("severity", 0) >= 5 else "MEDIUM",
            }

    # Check ERP for low stock
    for e in erp:
        stock = e.get("current_stock", 999)
        if stock < 50:
            return {
                "type": "inventory_alert",
                "payload": {
                    "sku_id": e.get("sku_id"),
                    "plant_id": e.get("plant_id"),
                    "current_stock": stock,
                    "message": f"Low inventory alert: {e.get('sku_id')} at "
                               f"{e.get('plant_id')} — only {stock} units remaining",
                },
                "timestamp": now,
                "severity": "MEDIUM",
            }

    # Default: KPI heartbeat update
    return {
        "type": "kpi_update",
        "payload": {
            "network_health": 75.0,
            "active_routes": 12,
            "pending_alerts": len([p for p in ports if p.get("congestion_index", 0) > 50]),
            "message": "Network KPI update",
        },
        "timestamp": now,
        "severity": "LOW",
    }


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
                # Send heartbeat to keep connection alive
                await websocket.send_json({
                    "type": "kpi_update",
                    "payload": {"message": "heartbeat"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "severity": "LOW",
                })

            await asyncio.sleep(5)  # Push events every 5 seconds

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)
