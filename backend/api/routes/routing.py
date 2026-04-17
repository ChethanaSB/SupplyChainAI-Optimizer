"""
routing.py (API route) — POST /api/routing/optimize
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.api.schemas import RoutingRequest, RouteOptResponse, RouteArc
from backend.config import SUPPLIER_LOCATIONS, PLANT_LOCATIONS
from backend.optimization.routing import optimize_routes

logger = logging.getLogger("chainmind.api.routing")
router = APIRouter()


@router.post("/optimize", response_model=RouteOptResponse)
async def optimize_routing(body: RoutingRequest):
    """Optimize multi-supplier routing for given cargo and constraints."""
    try:
        cargo_dicts = [{"sku_id": c.sku_id, "units": c.units} for c in body.cargo]
        if not cargo_dicts:
            # Default: route all SKUs with small quantity
            cargo_dicts = [{"sku_id": f"SKU-{i:04d}", "units": 100} for i in range(1, 11)]

        constraints = {}
        if body.constraints:
            if body.constraints.max_cost:
                constraints["max_cost"] = body.constraints.max_cost
            if body.constraints.max_co2:
                constraints["max_co2"] = body.constraints.max_co2
            if body.constraints.max_days:
                constraints["max_days"] = body.constraints.max_days

        result = optimize_routes(
            suppliers=SUPPLIER_LOCATIONS,
            plants=PLANT_LOCATIONS,
            customers=[],
            cargo=cargo_dicts,
            constraints=constraints,
        )

        routes = [
            RouteArc(
                supplier_id=r["supplier_id"],
                plant_id=r["plant_id"],
                mode=r["mode"],
                distance_km=r["distance_km"],
                cost_usd=r["cost_usd"],
                co2_kg=r["co2_kg"],
                lead_time_days=r["lead_time_days"],
            )
            for r in result["routes"]
        ]

        return RouteOptResponse(
            routes=routes,
            total_cost=result["total_cost"],
            total_co2=result["total_co2"],
            max_eta_days=result["max_eta_days"],
            active_route_count=result["active_route_count"],
            carrier_utilization=result["carrier_utilization"],
            pareto_frontier=result["pareto_frontier"],
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.error("Routing optimize error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
