"""
kpi.py (API route) — GET /api/kpi/dashboard
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from backend.api.schemas import KPIDashResponse, KPIMetric
from backend.config import MISSING_KEYS
from backend.db.database import get_df_cached
from backend.kpi.tracker import compute_kpis, compute_time_series_kpis
from backend.kpi.baseline import compute_baseline_kpis, compute_delta_vs_baseline

logger = logging.getLogger("chainmind.api.kpi")
router = APIRouter()

PERIOD_MAP = {"7d": 7, "30d": 30, "90d": 90}


@router.get("/dashboard", response_model=KPIDashResponse)
async def get_kpi_dashboard(
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
):
    """Get full KPI dashboard: ChainMind vs baseline with time series."""
    try:
        period_days = PERIOD_MAP.get(period, 30)
        df = await get_df_cached()

        chainmind_kpis = compute_kpis(df, period_days=period_days)
        baseline_kpis = compute_baseline_kpis(df, period_days=period_days)
        delta = compute_delta_vs_baseline(chainmind_kpis, baseline_kpis)

        # Build KPIMetric objects
        delta_pct = {}
        for key, values in delta.items():
            delta_pct[key] = KPIMetric(
                chainmind=values["chainmind"],
                baseline=values["baseline"],
                absolute_delta=values["absolute_delta"],
                pct_improvement=values["pct_improvement"],
                improved=values["improved"],
            )

        # Time series for sparklines
        time_series = compute_time_series_kpis(df, window_days=period_days) if df is not None else {}

        return KPIDashResponse(
            current=chainmind_kpis,
            baseline=baseline_kpis,
            delta_pct=delta_pct,
            time_series=time_series,
            period=period,
            computed_at=datetime.now(timezone.utc).isoformat(),
            missing_features=MISSING_KEYS,
        )

    except Exception as exc:
        logger.error("KPI dashboard error: %s", exc)
        return KPIDashResponse(
            current={},
            baseline={},
            delta_pct={},
            time_series={},
            period=period,
            computed_at=datetime.now(timezone.utc).isoformat(),
            missing_features=MISSING_KEYS,
        )
