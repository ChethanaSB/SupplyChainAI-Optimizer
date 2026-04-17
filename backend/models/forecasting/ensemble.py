"""
ensemble.py — Weighted ensemble of TFT + ARIMA forecasts.
Weights are learned from validation performance.
"""
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger("chainmind.ensemble")

# Default weights (TFT preferred when available and performing well)
DEFAULT_WEIGHTS = {"tft": 0.65, "arima": 0.35}


def ensemble_forecast(
    sku_id: str,
    region_id: str,
    horizon: int = 30,
    df_history=None,
    tft_available: bool = False,
    weights: dict | None = None,
) -> dict:
    """
    Blend TFT and ARIMA forecasts using weighted average.
    Falls back to ARIMA-only if TFT not available.
    """
    from backend.models.forecasting.arima_hierarchical import predict_arima

    weights = weights or DEFAULT_WEIGHTS

    arima_result = predict_arima(
        sku_id=sku_id,
        region_id=region_id,
        horizon=horizon,
        df=df_history,
    )

    if not tft_available:
        arima_result["model"] = "arima_only"
        return arima_result

    try:
        from backend.models.forecasting.tft_model import predict_demand
        tft_result = predict_demand(
            sku_id=sku_id,
            region_id=region_id,
            horizon=horizon,
            df_history=df_history,
        )
    except Exception as exc:
        logger.warning("TFT unavailable: %s. Using ARIMA only.", exc)
        arima_result["model"] = "arima_only"
        return arima_result

    w_tft = weights["tft"]
    w_arima = weights["arima"]

    def blend(tft_vals, arima_vals):
        n = min(len(tft_vals), len(arima_vals), horizon)
        return [round(w_tft * t + w_arima * a, 1) for t, a in zip(tft_vals[:n], arima_vals[:n])]

    return {
        "sku_id": sku_id,
        "region_id": region_id,
        "model": f"ensemble(tft×{w_tft}, arima×{w_arima})",
        "horizon": horizon,
        "dates": arima_result["dates"][:horizon],
        "p10": blend(tft_result.get("p10", arima_result["p10"]), arima_result["p10"]),
        "p50": blend(tft_result.get("p50", arima_result["p50"]), arima_result["p50"]),
        "p90": blend(tft_result.get("p90", arima_result["p90"]), arima_result["p90"]),
        "history_points": arima_result.get("history_points", 0),
    }
