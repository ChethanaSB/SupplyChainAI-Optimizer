"""
main.py — ChainMind FastAPI application entry point.
Registers all routes, starts background pollers via lifespan.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import FEATURES, MISSING_KEYS
from backend.data.ingestion.stream_bus import bus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chainmind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect Redis, start pollers. Shutdown: clean up."""
    logger.info("ChainMind starting up …")
    logger.info("Enabled features: %s", {k: v for k, v in FEATURES.items() if v})
    if MISSING_KEYS:
        logger.warning("Disabled features (missing keys): %s", MISSING_KEYS)

    # Connect Redis stream bus
    try:
        await bus.connect()
        logger.info("Redis stream bus connected.")
    except Exception as exc:
        logger.warning("Redis not available: %s. Live feed and polling disabled.", exc)

    # Start background pollers
    tasks = []
    try:
        from backend.data.ingestion.weather import run_weather_poller

        tasks.append(asyncio.create_task(run_weather_poller()))
        logger.info("Weather poller started.")
    except Exception as exc:
        logger.warning("Weather poller init failed: %s", exc)

    if FEATURES["commodity_prices"]:
        try:
            from backend.data.ingestion.market import run_price_poller
            tasks.append(asyncio.create_task(run_price_poller()))
            logger.info("Commodity price poller started.")
        except Exception as exc:
            logger.warning("Price poller init failed: %s", exc)

    if FEATURES["news_feed"]:
        try:
            from backend.data.ingestion.news import run_news_poller
            tasks.append(asyncio.create_task(run_news_poller()))
            logger.info("News poller started.")
        except Exception as exc:
            logger.warning("News poller init failed: %s", exc)

    try:
        from backend.data.ingestion.ports import run_port_poller
        tasks.append(asyncio.create_task(run_port_poller()))
        logger.info("Port poller started.")
    except Exception as exc:
        logger.warning("Port poller init failed: %s", exc)

    # Pre-load synthetic data into cache
    try:
        from backend.db.database import get_df_cached
        await get_df_cached()
        logger.info("Data cache pre-loaded.")
    except Exception as exc:
        logger.warning("Data pre-load failed: %s", exc)

    yield  # App is running

    # Shutdown
    for task in tasks:
        task.cancel()
    await bus.close()
    logger.info("ChainMind shut down cleanly.")


app = FastAPI(
    title="ChainMind — Logistics Intelligence Platform",
    description="AI-enhanced supply chain forecasting, optimization, and disruption management.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────
from backend.api.routes import forecast, disruption, routing, inventory, scenario, kpi, websocket

app.include_router(forecast.router, prefix="/api/forecast", tags=["Forecast"])
app.include_router(disruption.router, prefix="/api/disruption", tags=["Disruption"])
app.include_router(routing.router, prefix="/api/routing", tags=["Routing"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(scenario.router, prefix="/api/scenario", tags=["Scenario"])
app.include_router(kpi.router, prefix="/api/kpi", tags=["KPI"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "features": FEATURES,
        "missing_keys": MISSING_KEYS,
    }


@app.get("/")
async def root():
    return {
        "name": "ChainMind API",
        "version": "1.0.0",
        "docs": "/docs",
    }
