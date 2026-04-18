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
            # Default: route variety of SKUs across ALL plants to ensure full map visualization
            cargo_dicts = []
            import random
            for i in range(1, 81): # 80 items for maximum density
                # Spread cargo heavily
                cargo_dicts.append({
                    "sku_id": f"SKU-ZF-{i:02d}", 
                    "units": random.randint(5000, 45000), # Much higher volume
                })

        constraints = {}
        if body.constraints:
            if body.constraints.max_cost:
                constraints["max_cost"] = body.constraints.max_cost
            if body.constraints.max_co2:
                constraints["max_co2"] = body.constraints.max_co2
            if body.constraints.max_days:
                constraints["max_days"] = body.constraints.max_days
        
        if body.objective_weights:
            constraints["objective_weights"] = body.objective_weights

        result = optimize_routes(
            suppliers=SUPPLIER_LOCATIONS,
            plants=PLANT_LOCATIONS,
            customers=[],
            cargo=cargo_dicts,
            constraints=constraints,
        )

        # Create lookups for coordinates
        supplier_coords = {s["id"]: (s["lat"], s["lon"]) for s in SUPPLIER_LOCATIONS}
        plant_coords = {p["id"]: (p["lat"], p["lon"]) for p in PLANT_LOCATIONS}

        import random
        routes = []
        for r in result["routes"]:
            # Add tiny random jitter (0.05 - 0.1 degree) to coordinates to make route bundles visible
            # otherwise lines perfectly overlap and look like one single line
            jitter_o_lat = random.uniform(-0.15, 0.15)
            jitter_o_lon = random.uniform(-0.15, 0.15)
            jitter_d_lat = random.uniform(-0.1, 0.1)
            jitter_d_lon = random.uniform(-0.1, 0.1)

            routes.append(RouteArc(
                supplier_id=r["supplier_id"],
                plant_id=r["plant_id"],
                mode=r["mode"],
                distance_km=r["distance_km"],
                cost_inr=r["cost_inr"],
                co2_kg=r["co2_kg"],
                lead_time_days=r["lead_time_days"],
                origin_lat=supplier_coords.get(r["supplier_id"], (0,0))[0] + jitter_o_lat,
                origin_lon=supplier_coords.get(r["supplier_id"], (0,0))[1] + jitter_o_lon,
                dest_lat=plant_coords.get(r["plant_id"], (0,0))[0] + jitter_d_lat,
                dest_lon=plant_coords.get(r["plant_id"], (0,0))[1] + jitter_d_lon,
                provider=r.get("provider"),
            ))

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


@router.get("/vessels")
async def get_realtime_vessels():
    """Fetch recent vessel positions from Aisstream buffer."""
    from backend.data.ingestion.ports import get_live_vessels
    return get_live_vessels()

@router.post("/execute-plan")
async def execute_routing_plan(plan: dict):
    """
    Immutably record the current logistics plan to the ZF Green Ledger.
    """
    from backend.blockchain.ledger import carbon_ledger
    try:
        results = []
        for route in plan.get("routes", []):
            block = carbon_ledger.add_emission_record(
                route_id=f"{route['supplier_id']}-{route['plant_id']}",
                co2_kg=route['co2_kg'],
                carrier=f"ZF-{route['mode'].upper()}"
            )
            results.append({"route": route['supplier_id'], "hash": block.hash})
        
        return {"status": "SUCCESS", "ledger_blocks": results, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        logger.error("Ledger execution error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
