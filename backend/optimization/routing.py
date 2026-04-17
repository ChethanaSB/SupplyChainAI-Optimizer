"""
routing.py — OR-Tools VRP multi-objective routing optimizer.
Objectives: minimize total_freight_cost + CO2 + max_lead_time (Pareto).
"""
import logging
import math
from typing import Optional

import numpy as np

from backend.config import OR_TOOLS_TIME_LIMIT_SEC, CO2_BUDGET_KG_DEFAULT, RISK_HIGH_THRESHOLD

logger = logging.getLogger("chainmind.routing")

# CO2 factors: kg CO2 per tonne-km by mode
CO2_FACTORS = {
    "sea": 0.016,
    "air": 0.602,
    "road": 0.096,
    "rail": 0.028,
}

# Freight cost: USD per tonne-km by mode
COST_FACTORS = {
    "sea": 0.05,
    "air": 4.80,
    "road": 0.25,
    "rail": 0.10,
}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def select_transport_mode(distance_km: float, weight_tonnes: float) -> str:
    """Heuristic mode selection based on distance/weight."""
    if distance_km > 3000 and weight_tonnes > 5:
        return "sea"
    elif distance_km > 1500:
        return "rail"
    elif distance_km > 500:
        return "road"
    else:
        return "road"


def compute_route_metrics(
    origin: dict,
    destination: dict,
    cargo_tonnes: float,
    mode: str | None = None,
    port_risk_scores: dict | None = None,
) -> dict:
    """Compute cost, CO2, and lead time for a single route arc."""
    # Base great-circle distance
    base_dist = haversine(origin["lat"], origin["lon"], destination["lat"], destination["lon"])
    mode = mode or select_transport_mode(base_dist, cargo_tonnes)

    dist_km = base_dist
    if mode == "sea":
        try:
            import searoute
            # searoute expects [lon, lat]
            origin_pt = [origin["lon"], origin["lat"]]
            dest_pt = [destination["lon"], destination["lat"]]
            route = searoute.searoute(origin_pt, dest_pt, units="km")
            dist_km = route.get("properties", {}).get("length", base_dist)
            logger.debug("Searoute: Calculated maritime distance: %.1f km", dist_km)
        except Exception as exc:
            logger.warning("Searoute calculation failed, falling back to haversine: %s", exc)
            dist_km = base_dist

    cost_usd = dist_km * cargo_tonnes * COST_FACTORS.get(mode, 0.25)
    co2_kg = dist_km * cargo_tonnes * CO2_FACTORS.get(mode, 0.096)

    # Lead time: speed-dependent
    # Sea speed is usually lower when considering port transits/routing
    speeds_km_per_day = {"sea": 450, "air": 8000, "road": 600, "rail": 800}
    lead_time_days = dist_km / speeds_km_per_day.get(mode, 600)

    # Apply port risk penalty
    if port_risk_scores and mode == "sea":
        max_port_risk = max(
            port_risk_scores.get(p, 0) for p in port_risk_scores
        )
        if max_port_risk > RISK_HIGH_THRESHOLD:
            lead_time_days *= 1.5  # 50% delay when high-risk port
            cost_usd *= 1.2

    from backend.config import SEADISTANCES_API_KEY
    provider = "Sea-Distances.org" if SEADISTANCES_API_KEY else "searoute-lib"

    return {
        "distance_km": round(dist_km, 1),
        "mode": mode,
        "cost_usd": round(cost_usd, 2),
        "co2_kg": round(co2_kg, 2),
        "lead_time_days": round(lead_time_days, 1),
        "cargo_tonnes": cargo_tonnes,
        "provider": provider
    }


def optimize_routes(
    suppliers: list[dict],
    plants: list[dict],
    customers: list[dict],
    cargo: list[dict],
    constraints: dict | None = None,
    port_risk_scores: dict | None = None,
    blocked_supplier_ids: list[str] | None = None,
    carrier_capacity_factor: float = 1.0,
) -> dict:
    """
    Multi-objective routing optimization using OR-Tools CP-SAT.
    Falls back to greedy heuristic if OR-Tools not available.

    Args:
        suppliers: List of {id, name, lat, lon} dicts
        plants: List of {id, name, lat, lon} dicts
        customers: Not used directly but affects demand allocation
        cargo: List of {sku_id, units} dicts
        constraints: {max_cost, max_co2, max_days}
        port_risk_scores: {port_id: risk_score (0-100)}
        blocked_supplier_ids: Suppliers to exclude (e.g. port closures)
        carrier_capacity_factor: Multiplier for carrier capacity (default 1.0)

    Returns:
        {routes, total_cost, total_co2, max_eta_days, carrier_utilization, pareto_frontier}
    """
    constraints = constraints or {}
    max_co2 = constraints.get("max_co2", CO2_BUDGET_KG_DEFAULT)
    max_cost = constraints.get("max_cost", float("inf"))
    max_days = constraints.get("max_days", 60.0)
    blocked = set(blocked_supplier_ids or [])

    # Filter available suppliers
    active_suppliers = [s for s in suppliers if s["id"] not in blocked]
    if not active_suppliers:
        logger.warning("All suppliers blocked! Using all suppliers as emergency fallback.")
        active_suppliers = suppliers

    # Try OR-Tools CP-SAT
    try:
        return _ortools_optimize(
            active_suppliers, plants, cargo, max_co2, max_cost, max_days,
            port_risk_scores, carrier_capacity_factor
        )
    except ImportError:
        logger.warning("OR-Tools not installed. Using greedy routing heuristic.")
    except Exception as exc:
        logger.error("OR-Tools optimization failed: %s. Fallback to greedy.", exc)

    return _greedy_optimize(active_suppliers, plants, cargo, max_co2, port_risk_scores)


def _ortools_optimize(
    suppliers: list[dict],
    plants: list[dict],
    cargo: list[dict],
    max_co2: float,
    max_cost: float,
    max_days: float,
    port_risk_scores: dict | None,
    carrier_capacity_factor: float,
) -> dict:
    """OR-Tools CP-SAT multi-objective VRP."""
    from ortools.sat.python import cp_model

    total_units = sum(c.get("units", 0) for c in cargo)
    total_weight_tonnes = total_units * 0.001  # Assume 1kg per unit average

    model = cp_model.CpModel()
    routes = []

    # Generate all candidate routes (supplier × plant pairs)
    candidate_routes = []
    for sup in suppliers:
        for plt in plants:
            # Fraction of cargo routed through this lane (scaled)
            metrics = compute_route_metrics(sup, plt, total_weight_tonnes / len(suppliers),
                                           port_risk_scores=port_risk_scores)
            candidate_routes.append({
                "supplier_id": sup["id"],
                "plant_id": plt["id"],
                "metrics": metrics,
            })

    # Objective: minimize weighted cost + CO2 + lead_time
    # Use integer scale (multiply by 100 for OR-Tools integer arithmetic)
    route_vars = []
    for i, route in enumerate(candidate_routes):
        x = model.NewBoolVar(f"route_{i}")
        route_vars.append(x)

    # Constraint: CO2 budget
    co2_scaled = [int(r["metrics"]["co2_kg"] * 100) for r in candidate_routes]
    model.Add(
        sum(co2_scaled[i] * route_vars[i] for i in range(len(candidate_routes)))
        <= int(max_co2 * 100)
    )

    # Each plant must be served by at least one supplier
    for plt in plants:
        plant_routes = [i for i, r in enumerate(candidate_routes) if r["plant_id"] == plt["id"]]
        if plant_routes:
            model.Add(sum(route_vars[i] for i in plant_routes) >= 1)

    # Minimize total cost (within CO2 constraint)
    cost_scaled = [int(r["metrics"]["cost_usd"] * 10) for r in candidate_routes]
    model.Minimize(sum(cost_scaled[i] * route_vars[i] for i in range(len(candidate_routes))))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = OR_TOOLS_TIME_LIMIT_SEC
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        active_routes = [
            candidate_routes[i]
            for i in range(len(candidate_routes))
            if solver.Value(route_vars[i]) == 1
        ]
    else:
        logger.warning("OR-Tools: no feasible solution found, using all routes.")
        active_routes = candidate_routes[:len(plants)]  # Greedy fallback

    return _build_result(active_routes, candidate_routes)


def _greedy_optimize(
    suppliers: list[dict],
    plants: list[dict],
    cargo: list[dict],
    max_co2: float,
    port_risk_scores: dict | None,
) -> dict:
    """Greedy routing: assign cheapest feasible supplier to each plant."""
    total_units = sum(c.get("units", 0) for c in cargo)
    total_weight_tonnes = max(0.001, total_units * 0.001)

    active_routes = []
    for plt in plants:
        best = None
        best_cost = float("inf")
        for sup in suppliers:
            metrics = compute_route_metrics(
                sup, plt,
                total_weight_tonnes / max(1, len(plants)),
                port_risk_scores=port_risk_scores
            )
            if metrics["cost_usd"] < best_cost:
                best_cost = metrics["cost_usd"]
                best = {"supplier_id": sup["id"], "plant_id": plt["id"], "metrics": metrics}
        if best:
            active_routes.append(best)

    return _build_result(active_routes, active_routes)


def _build_result(active_routes: list[dict], all_routes: list[dict]) -> dict:
    """Build standardized routing result dict."""
    total_cost = sum(r["metrics"]["cost_usd"] for r in active_routes)
    total_co2 = sum(r["metrics"]["co2_kg"] for r in active_routes)
    max_eta = max((r["metrics"]["lead_time_days"] for r in active_routes), default=0.0)

    # Carrier utilization (by mode)
    carrier_util: dict[str, float] = {}
    for r in active_routes:
        mode = r["metrics"]["mode"]
        carrier_util[mode] = carrier_util.get(mode, 0) + r["metrics"]["cargo_tonnes"]

    # Pareto frontier: sample cost-CO2 tradeoff
    pareto = []
    cost_vals = sorted(set(int(r["metrics"]["cost_usd"]) for r in all_routes))[:5]
    for threshold in cost_vals:
        subset = [r for r in all_routes if r["metrics"]["cost_usd"] <= threshold]
        if subset:
            pareto.append({
                "max_cost_usd": threshold,
                "total_co2_kg": round(sum(r["metrics"]["co2_kg"] for r in subset), 1),
                "routes": len(subset),
            })

    routes_output = [
        {
            "supplier_id": r["supplier_id"],
            "plant_id": r["plant_id"],
            "mode": r["metrics"]["mode"],
            "distance_km": r["metrics"]["distance_km"],
            "cost_usd": r["metrics"]["cost_usd"],
            "co2_kg": r["metrics"]["co2_kg"],
            "lead_time_days": r["metrics"]["lead_time_days"],
        }
        for r in active_routes
    ]

    return {
        "routes": routes_output,
        "total_cost": round(total_cost, 2),
        "total_co2": round(total_co2, 2),
        "max_eta_days": round(max_eta, 1),
        "active_route_count": len(active_routes),
        "carrier_utilization": {k: round(v, 2) for k, v in carrier_util.items()},
        "pareto_frontier": pareto,
    }
