"""
config.py — ChainMind environment configuration and constants.
Validates required API keys on startup; logs which features are disabled.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("chainmind.config")

# ─── Base Paths ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://chainmind:chainmind@localhost:5432/chainmind"
)
DATABASE_URL_SYNC: str = DATABASE_URL.replace("+asyncpg", "")

# ─── Redis ───────────────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# ─── MLflow ──────────────────────────────────────────────────────────────────
MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

# ─── External API keys ───────────────────────────────────────────────────────
ALPHA_VANTAGE_KEY: str | None = os.getenv("ALPHA_VANTAGE_KEY")
NEWSAPI_KEY: str | None = os.getenv("NEWSAPI_KEY")
MARINETRAFFIC_KEY: str | None = os.getenv("MARINETRAFFIC_KEY")
AISTREAM_API_KEY: str | None = os.getenv("AISTREAM_API_KEY")
SEADISTANCES_API_KEY: str | None = os.getenv("SEADISTANCES_API_KEY")
SEAROUTES_API_KEY: str | None = os.getenv("SEAROUTES_API_KEY")
HF_API_TOKEN: str | None = os.getenv("HF_API_TOKEN")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ─── Open-Meteo (no key required) ────────────────────────────────────────────
OPENMETEO_BASE_URL: str = os.getenv(
    "OPENMETEO_BASE_URL", "https://api.open-meteo.com/v1"
)

# ─── Polling intervals ────────────────────────────────────────────────────────
WEATHER_POLL_INTERVAL_SEC: int = 15 * 60   # 15 minutes
PRICE_POLL_INTERVAL_SEC: int = 24 * 3600   # 24 hours (rate-limit aware)
PORT_POLL_INTERVAL_SEC: int = 15 * 60
NEWS_POLL_INTERVAL_SEC: int = 15 * 60
ERP_POLL_INTERVAL_SEC: int = 60            # 1 minute

# ─── Feature flags derived from key availability ─────────────────────────────
FEATURES: dict[str, bool] = {
    "commodity_prices": bool(ALPHA_VANTAGE_KEY),
    "news_feed": bool(NEWSAPI_KEY),
    "port_marine": bool(MARINETRAFFIC_KEY or AISTREAM_API_KEY),
    "sea_routing": bool(SEAROUTES_API_KEY or SEADISTANCES_API_KEY),
    "nlp_ner": bool(HF_API_TOKEN),
    "ai_playbooks": bool(GEMINI_API_KEY),
    "weather": True,   # Open-Meteo: always available
}

MISSING_KEYS: list[str] = [
    name for name, available in FEATURES.items() if not available
]

if MISSING_KEYS:
    logger.warning(
        "ChainMind startup: the following features are DISABLED due to missing "
        "API keys: %s.  Add keys to .env to enable them.",
        ", ".join(MISSING_KEYS),
    )

# ─── Supply chain topology constants ─────────────────────────────────────────
NUM_SKUS: int = 50
NUM_SUPPLIERS: int = 8
NUM_PLANTS: int = 5
NUM_REGIONS: int = 12

SUPPLIER_LOCATIONS: list[dict] = [
    {"id": "ZF-SUP-PUNE", "name": "ZF Pune Chakan Plant", "lat": 18.750, "lon": 73.850, "country": "IN"},
    {"id": "ZF-SUP-CBE", "name": "ZF Coimbatore Hub", "lat": 11.016, "lon": 76.955, "country": "IN"},
    {"id": "ZF-SUP-CHN", "name": "ZF Chennai Oragadam", "lat": 12.833, "lon": 80.016, "country": "IN"},
    {"id": "ZF-SUP-BLR", "name": "ZF Bengaluru Tech", "lat": 12.971, "lon": 77.594, "country": "IN"},
    {"id": "ZF-SUP-HYD", "name": "ZF Hyderabad Tech", "lat": 17.385, "lon": 78.486, "country": "IN"},
    {"id": "ZF-SUP-MUM", "name": "ZF Mumbai Logistics", "lat": 19.076, "lon": 72.877, "country": "IN"},
    {"id": "ZF-SUP-DEL", "name": "ZF Delhi NCR Hub", "lat": 28.613, "lon": 77.209, "country": "IN"},
    {"id": "ZF-SUP-JKD", "name": "ZF Jamshedpur Foundry", "lat": 22.804, "lon": 86.202, "country": "IN"},
]

PLANT_LOCATIONS: list[dict] = [
    {"id": "ZF-PLT-PUNE", "name": "ZF Pune Multi-Divisional", "lat": 18.750, "lon": 73.850},
    {"id": "ZF-PLT-CHN", "name": "ZF Chennai CVCS Plant", "lat": 12.833, "lon": 80.016},
    {"id": "ZF-PLT-BLR", "name": "ZF Bengaluru Global Tech Center", "lat": 12.971, "lon": 77.594},
    {"id": "ZF-PLT-HYD", "name": "ZF Hyderabad IT Center", "lat": 17.385, "lon": 78.486},
    {"id": "ZF-PLT-CBE", "name": "ZF Coimbatore Industrial", "lat": 11.016, "lon": 76.955},
]

KEY_PORTS: list[dict] = [
    {"id": "PORT-NSA", "name": "Nhava Sheva (JNPT)", "lat": 18.950, "lon": 72.950},
    {"id": "PORT-MUN", "name": "Mundra", "lat": 22.733, "lon": 69.700},
    {"id": "PORT-MAA", "name": "Chennai Port", "lat": 13.100, "lon": 80.300},
    {"id": "PORT-VTZ", "name": "Visakhapatnam", "lat": 17.683, "lon": 83.217},
    {"id": "PORT-KND", "name": "Kandla (Deendayal)", "lat": 23.016, "lon": 70.216},
]

SKU_IDS: list[str] = [
    "GEARBOX-X1", "SENSOR-A2", "MOTOR-Z", "CHASSIS-H", "BATTERY-V2", 
    "TIRE-R18", "BRAKE-KIT", "ECU-M1", "INFOTAINMENT-S", "TRANSMISSION-AUTO"
]

# ─── Risk thresholds ─────────────────────────────────────────────────────────
RISK_HIGH_THRESHOLD: int = 70
RISK_MEDIUM_THRESHOLD: int = 40

# ─── Optimization defaults ────────────────────────────────────────────────────
OR_TOOLS_TIME_LIMIT_SEC: int = 30
CO2_BUDGET_KG_DEFAULT: float = 50_000.0

# ─── Service level target ────────────────────────────────────────────────────
TARGET_SERVICE_LEVEL: float = 0.95  # 95%
Z_SCORE_95: float = 1.645
