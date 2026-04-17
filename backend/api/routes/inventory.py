"""
inventory.py (API route) — GET /api/inventory/recommendations
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from backend.api.schemas import InventoryResponse, InventoryItem
from backend.config import SKU_IDS
from backend.db.database import get_df_cached
from backend.models.inventory.reorder_policy import get_recommendation, Policy

logger = logging.getLogger("chainmind.api.inventory")
router = APIRouter()


@router.get("/recommendations", response_model=InventoryResponse)
async def get_inventory_recommendations(
    sku_ids: str = Query("all"),
    policy: str = Query("statistical"),
):
    """Get inventory recommendations for all or specified SKUs."""
    try:
        df = await get_df_cached()

        target_skus = SKU_IDS if sku_ids == "all" else [s.strip() for s in sku_ids.split(",")]
        policy_enum = Policy(policy) if policy in Policy.__members__.values() else Policy.STATISTICAL

        items = []
        for sku_id in target_skus[:50]:  # Cap at 50 for performance
            demand_avg = 200.0
            demand_std = 50.0
            lead_time_avg = 14.0
            lead_time_std = 3.0
            unit_cost = 100.0
            current_stock = 500.0
            pending_orders = 100.0

            if df is not None and len(df) > 0 and "sku_id" in df.columns:
                sku_df = df[df["sku_id"] == sku_id]
                if len(sku_df) > 0:
                    demand_avg = float(sku_df["demand_units"].mean())
                    demand_std = float(sku_df["demand_units"].std()) if len(sku_df) > 1 else 50.0
                    lead_time_avg = float(sku_df["lead_time_days"].mean())
                    lead_time_std = float(sku_df["lead_time_days"].std()) if len(sku_df) > 1 else 3.0
                    unit_cost = float(sku_df["unit_cost"].iloc[-1]) if "unit_cost" in sku_df.columns else 100.0
                    current_stock = float(sku_df["stock_level"].iloc[-1]) if "stock_level" in sku_df.columns else 500.0

            rec = get_recommendation(
                sku_id=sku_id,
                current_stock=current_stock,
                demand_avg=demand_avg,
                demand_std=demand_std,
                lead_time_avg=lead_time_avg,
                lead_time_std=lead_time_std,
                unit_cost=unit_cost,
                risk_score=35.0,  # Default risk
                pending_orders=pending_orders,
                policy=policy_enum,
            )

            items.append(InventoryItem(**rec))

        return InventoryResponse(
            items=items,
            policy=policy,
            service_level=0.95,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.error("Inventory recommendations error: %s", exc)
        return InventoryResponse(
            items=[],
            policy=policy,
            service_level=0.95,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
