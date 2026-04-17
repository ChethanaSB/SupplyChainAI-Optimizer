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
    "port_marine": bool(MARINETRAFFIC_KEY),
    "sea_routing": bool(SEAROUTES_API_KEY),
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
    {"id": "SUP-01", "name": "Suzhou Plant", "lat": 31.299, "lon": 120.585, "country": "CN"},
    {"id": "SUP-02", "name": "Stuttgart Hub", "lat": 48.775, "lon": 9.182, "country": "DE"},
    {"id": "SUP-03", "name": "Pune Factory", "lat": 18.520, "lon": 73.856, "country": "IN"},
    {"id": "SUP-04", "name": "Detroit Tier-1", "lat": 42.332, "lon": -83.046, "country": "US"},
    {"id": "SUP-05", "name": "Monterrey Ops", "lat": 25.686, "lon": -100.316, "country": "MX"},
    {"id": "SUP-06", "name": "Bochum Parts", "lat": 51.482, "lon": 7.216, "country": "DE"},
    {"id": "SUP-07", "name": "Wuhan Components", "lat": 30.593, "lon": 114.305, "country": "CN"},
    {"id": "SUP-08", "name": "Johannesburg Supply", "lat": -26.204, "lon": 28.047, "country": "ZA"},
]

PLANT_LOCATIONS: list[dict] = [
    {"id": "PLT-01", "name": "ZF Saarbrücken", "lat": 49.234, "lon": 6.996},
    {"id": "PLT-02", "name": "ZF Friedrichshafen", "lat": 47.653, "lon": 9.476},
    {"id": "PLT-03", "name": "ZF Lemförde", "lat": 52.471, "lon": 8.370},
    {"id": "PLT-04", "name": "ZF North America", "lat": 43.068, "lon": -85.448},
    {"id": "PLT-05", "name": "ZF Asia Pacific", "lat": 31.224, "lon": 121.469},
]

KEY_PORTS: list[dict] = [
    {"id": "PORT-RTM", "name": "Rotterdam", "lat": 51.905, "lon": 4.480},
    {"id": "PORT-SHA", "name": "Shanghai", "lat": 31.229, "lon": 121.474},
    {"id": "PORT-LAX", "name": "Los Angeles / Long Beach", "lat": 33.754, "lon": -118.216},
    {"id": "PORT-SIN", "name": "Singapore", "lat": 1.264, "lon": 103.820},
    {"id": "PORT-HAM", "name": "Hamburg", "lat": 53.546, "lon": 9.966},
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
