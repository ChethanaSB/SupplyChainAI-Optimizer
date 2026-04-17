"""
forecast.py — GET /api/forecast/{sku_id}
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.api.schemas import ForecastResponse
from backend.models.inventory.safety_stock import compute_safety_stock, compute_reorder_point
from backend.models.forecasting.ensemble import ensemble_forecast
from backend.db.database import get_df_cached

logger = logging.getLogger("chainmind.api.forecast")
router = APIRouter()


@router.get("/{sku_id}", response_model=ForecastResponse)
async def get_forecast(
    sku_id: str,
    horizon: int = Query(30, ge=1, le=90),
    region: str = Query("REG-01"),
    percentiles: str = Query("10,50,90"),
):
    """Get demand forecast for a specific SKU and region."""
    try:
        df = await get_df_cached()

        # Validate SKU exists
        if df is not None and len(df) > 0:
            known_skus = df["sku_id"].unique().tolist() if "sku_id" in df.columns else []
            if known_skus and sku_id not in known_skus:
                raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found in dataset.")

        result = ensemble_forecast(
            sku_id=sku_id,
            region_id=region,
            horizon=horizon,
            df_history=df,
            tft_available=False,  # Use ARIMA until TFT trained
        )

        # Compute safety stock from historical data
        demand_std = 50.0
        demand_avg = 200.0
        lead_time_avg = 14.0

        if df is not None and len(df) > 0:
            sku_df = df[df["sku_id"] == sku_id]
            if len(sku_df) > 0:
                demand_avg = float(sku_df["demand_units"].mean())
                demand_std = float(sku_df["demand_units"].std())
                lead_time_avg = float(sku_df["lead_time_days"].mean())

        ss = compute_safety_stock(demand_std, lead_time_avg)
        rop = compute_reorder_point(demand_avg, lead_time_avg, ss)

        return ForecastResponse(
            sku_id=sku_id,
            region_id=region,
            model=result.get("model", "ensemble"),
            horizon=horizon,
            dates=result["dates"],
            p10=result["p10"],
            p50=result["p50"],
            p90=result["p90"],
            safety_stock_units=round(ss, 0),
            reorder_point=round(rop, 0),
            history_points=result.get("history_points", 0),
            warning=result.get("warning"),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Forecast error for %s: %s", sku_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))
