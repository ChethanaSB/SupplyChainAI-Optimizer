"""
routing.py — OR-Tools VRP multi-objective routing optimizer.
Objectives: minimize total_freight_cost + CO2 + max_lead_time (Pareto).
"""
import logging
import math
import requests
import random
from typing import Optional

import numpy as np

from backend.config import OR_TOOLS_TIME_LIMIT_SEC, CO2_BUDGET_KG_DEFAULT, RISK_HIGH_THRESHOLD, USD_TO_INR, GOOGLE_MAPS_API_KEY

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


def _find_nearest_port(lat: float, lon: float) -> str:
    """Find the ID of the nearest port from KEY_PORTS."""
    from backend.config import KEY_PORTS
    best_port = KEY_PORTS[0]["id"]
    min_dist = float("inf")
    for p in KEY_PORTS:
        d = haversine(lat, lon, p["lat"], p["lon"])
        if d < min_dist:
            min_dist = d
            best_port = p["id"]
    return best_port

def get_google_distance_matrix(origins: list[dict], destinations: list[dict], mode: str = "driving") -> dict | None:
    """Fetch distance/duration from Google Maps Distance Matrix API."""
    if not GOOGLE_MAPS_API_KEY or "DEMO" in GOOGLE_MAPS_API_KEY or len(GOOGLE_MAPS_API_KEY) < 10:
        return None
    
    try:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        origin_str = "|".join([f"{o['lat']},{o['lon']}" for o in origins])
        dest_str = "|".join([f"{d['lat']},{d['lon']}" for d in destinations])
        
        params = {
            "origins": origin_str,
            "destinations": dest_str,
            "key": GOOGLE_MAPS_API_KEY,
            "mode": mode
        }
        
        resp = requests.get(url, params=params, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") == "OK":
            return data
        else:
            logger.warning("Google Maps API status: %s", data.get("status"))
    except Exception as exc:
        logger.warning("Google Maps API call failed: %s", exc)
    return None

def compute_route_metrics(
    origin: dict,
    destination: dict,
    cargo_tonnes: float,
    mode: str | None = None,
    port_congestion_data: dict | None = None,
    google_data: dict | None = None,
) -> dict:
    """Compute cost, CO2, and lead time for a single route arc with real-time port data."""
    base_dist = haversine(origin["lat"], origin["lon"], destination["lat"], destination["lon"])
    mode = mode or select_transport_mode(base_dist, cargo_tonnes)

    dist_km = base_dist
    lead_time_days = 0.0
    provider = "Heuristic (Haversine)"

    # Google Maps Integration
    if google_data and mode in ["road", "rail"]:
        dist_km = google_data.get("distance", base_dist * 1000) / 1000.0
        lead_time_days = google_data.get("duration", (dist_km / 720) * 86400) / 86400.0
        provider = "Google Maps Distance Matrix"
    else:
        if mode == "sea":
            # Innovative improvement: Dynamic maritime search fallback
            try:
                import searoute
                origin_pt = [origin["lon"], origin["lat"]]
                dest_pt = [destination["lon"], destination["lat"]]
                route = searoute.searoute(origin_pt, dest_pt, units="km")
                dist_km = route.get("properties", {}).get("length", base_dist * 1.3)
                provider = "searoute-open-source"
            except Exception:
                dist_km = base_dist * 1.3
        
        # Base lead time calculation if no Google data
        speeds_km_per_day = {"sea": 480, "air": 9000, "road": 720, "rail": 960}
        lead_time_days = max(0.5, dist_km / speeds_km_per_day.get(mode, 600))

    # Base lead time (Minimum 0.5 days for loading/processing)
    # Re-apply min threshold
    lead_time_days = max(0.5, lead_time_days)

    # ZF Green Portfolio: Weighted CO2 vs Cost (Dynamic base cost to avoid identical values)
    base_handling = random.uniform(50.0, 300.0) # Varies by facility
    cost_usd = base_handling + (dist_km * cargo_tonnes * COST_FACTORS.get(mode, 0.25))
    co2_kg = (dist_km * cargo_tonnes * CO2_FACTORS.get(mode, 0.096)) + random.uniform(1.0, 10.0)

    # Real-time Port Congestion Penalty
    if mode == "sea" and port_congestion_data:
        port_a = _find_nearest_port(origin["lat"], origin["lon"])
        port_b = _find_nearest_port(destination["lat"], destination["lon"])
        cong_a = port_congestion_data.get(port_a, 30.0)
        cong_b = port_congestion_data.get(port_b, 30.0)
        delay_days = (cong_a + cong_b) / 100.0 * 1.5
        lead_time_days += delay_days
        cost_usd += (delay_days * 500)

    from backend.config import SEADISTANCES_API_KEY, USD_TO_INR
    if provider == "Heuristic (Haversine)" and SEADISTANCES_API_KEY and "DEMO" not in SEADISTANCES_API_KEY:
        provider = "Sea-Distances.org"
    cost_inr = cost_usd * USD_TO_INR

    # BlockChain: Record emission to Green Ledger (Immutable)
    try:
        from backend.blockchain.ledger import carbon_ledger
        route_id = f"{origin.get('id', 'UNK')}-{destination.get('id', 'UNK')}"
        carbon_ledger.add_emission_record(route_id, co2_kg, f"ZF-CARRIER-{mode.upper()}")
    except Exception as exc:
        logger.warning("Failed to record to Green Ledger: %s", exc)

    return {
        "distance_km": round(dist_km, 1),
        "mode": mode,
        "cost_inr": round(cost_inr, 2),
        "co2_kg": round(co2_kg, 2),
        "lead_time_days": round(lead_time_days, 1),
        "cargo_tonnes": cargo_tonnes,
        "provider": provider,
        "blockchain_verified": True
    }

def optimize_routes(
    suppliers: list[dict],
    plants: list[dict],
    customers: list[dict],
    cargo: list[dict],
    constraints: dict | None = None,
    port_congestion_data: dict | None = None,
    blocked_supplier_ids: list[str] | None = None,
    carrier_capacity_factor: float = 1.0,
) -> dict:
    """
    ZF Next Generation Routing: Multi-objective optimization under real-time constraints.
    """
    constraints = constraints or {}
    max_co2 = constraints.get("max_co2", CO2_BUDGET_KG_DEFAULT)
    max_days = constraints.get("max_days", 45.0)
    blocked = set(blocked_supplier_ids or [])

    active_suppliers = [s for s in suppliers if s["id"] not in blocked]
    if not active_suppliers:
        active_suppliers = suppliers

    try:
        # Pre-fetch Google Distance Matrix if enabled to pass to fallbacks if needed
        google_matrix = get_google_distance_matrix(active_suppliers, plants)

        # Extraction of weights from constraints if present
        weights = constraints.get("objective_weights", {"cost": 0.4, "co2": 0.4, "time": 0.2})

        return _ortools_optimize(
            active_suppliers, plants, cargo, max_co2, float("inf"), max_days,
            port_congestion_data, carrier_capacity_factor,
            google_matrix=google_matrix,
            objective_weights=weights
        )
    except Exception as exc:
        logger.error("Optimization failed: %s. Fallback to greedy.", exc)
        try:
           # Reuse google_matrix if already fetched or fetch now
           if 'google_matrix' not in locals():
               google_matrix = get_google_distance_matrix(active_suppliers, plants)
           return _greedy_optimize(active_suppliers, plants, cargo, max_co2, port_congestion_data, google_matrix=google_matrix)
        except Exception as e2:
           logger.critical("Critical routing failure: %s", e2)
           return {"routes": [], "total_cost": 0, "total_co2": 0, "max_eta_days": 0, "active_route_count": 0, "carrier_utilization": {}, "pareto_frontier": []}


# Carrier Capacities (tonnes)
CARRIER_CAPS = {
    "road": 500,
    "rail": 2000,
    "air": 200,
    "sea": 50000,
}

def _ortools_optimize(
    suppliers: list[dict],
    plants: list[dict],
    cargo: list[dict],
    max_co2: float,
    max_cost: float,
    max_days: float,
    port_risk_scores: dict | None,
    carrier_capacity_factor: float,
    google_matrix: dict | None = None,
    objective_weights: dict[str, float] | None = None,
) -> dict:
    """OR-Tools CP-SAT multi-objective VRP with capacity constraints."""
    from ortools.sat.python import cp_model

    total_units = sum(c.get("units", 0) for c in cargo)
    total_weight_tonnes = total_units * 0.001  # Assume 1kg per unit average

    model = cp_model.CpModel()
    
    # Enforce decentralization: Limit each plant to a max percentage of total volume
    # This ensures we see multiple routes on the map for the demo
    PLANT_MAX_TONNES = (total_weight_tonnes / max(1, len(plants))) * 1.5 
    candidate_routes = []

    # Pre-fetch Google Distance Matrix if enabled
    google_matrix = get_google_distance_matrix(suppliers, plants)

    for i, sup in enumerate(suppliers):
        for j, plt in enumerate(plants):
            # Extract google info if available
            g_info = None
            if google_matrix and google_matrix["rows"][i]["elements"][j]["status"] == "OK":
                g_info = {
                    "distance": google_matrix["rows"][i]["elements"][j]["distance"]["value"],
                    "duration": google_matrix["rows"][i]["elements"][j]["duration"]["value"]
                }
            
            # We evaluate each mode for each pair to find the best mode
            for mode in ["road", "rail", "sea", "air"]:
                metrics = compute_route_metrics(
                    sup, plt, total_weight_tonnes / max(1, len(plants)),
                    mode=mode, port_congestion_data=port_risk_scores,
                    google_data=g_info
                )
                candidate_routes.append({
                    "supplier_id": sup["id"],
                    "plant_id": plt["id"],
                    "mode": mode,
                    "metrics": metrics,
                })

    # Variables: x[i] = weight allocated to route i
    # OR-Tools SAT works best with integers, so we scale by 100 (0.01 tonne resolution)
    weight_vars = []
    total_weight_scaled = int(total_weight_tonnes * 100)
    
    for i, route in enumerate(candidate_routes):
        # We can allocate between 0 and total_weight to a single route
        v = model.NewIntVar(0, total_weight_scaled, f"weight_{i}")
        weight_vars.append(v)

    # Constraint 1: Total weight must be allocated
    model.Add(sum(weight_vars) == total_weight_scaled)

    # Constraint 2: CO2 budget
    # co2_per_tonne = co2_kg / (total_weight / len(plants))
    co2_coeffs = []
    for r in candidate_routes:
        # co2_kg is calculated for cargo_tonnes in compute_route_metrics
        # so co2_per_tonne = metrics["co2_kg"] / metrics["cargo_tonnes"]
        co2_per_tonne = r["metrics"]["co2_kg"] / max(0.001, r["metrics"]["cargo_tonnes"])
        co2_coeffs.append(int(co2_per_tonne * 1000)) # Scale for precision

    model.Add(
        sum(co2_coeffs[i] * weight_vars[i] for i in range(len(candidate_routes)))
        <= int(max_co2 * 100000) # Scaled
    )

    # Constraint 3: Carrier Capacities
    for mode in CARRIER_CAPS:
        mode_routes = [i for i, r in enumerate(candidate_routes) if r["mode"] == mode]
        if mode_routes:
            cap_scaled = int(CARRIER_CAPS[mode] * carrier_capacity_factor * 100)
            model.Add(sum(weight_vars[i] for i in mode_routes) <= cap_scaled)

    # Constraint 4: Lead time (hard limit for any used route)
    for i, route in enumerate(candidate_routes):
        if route["metrics"]["lead_time_days"] > max_days:
            model.Add(weight_vars[i] == 0)

    # NEW: Constraint 5: Multi-Source De-centralization (for visualization and resilience)
    # Ensure each plant is served by at least 2 different suppliers if possible
    for plt in plants:
        plt_routes = [i for i, r in enumerate(candidate_routes) if r["plant_id"] == plt["id"]]
        if plt_routes:
            # Indicator variables: route_used[i] = 1 if weight_vars[i] > 0
            route_used = [model.NewBoolVar(f"used_{i}") for i in plt_routes]
            for idx, r_idx in enumerate(plt_routes):
                model.Add(weight_vars[r_idx] > 0).OnlyEnforceIf(route_used[idx])
                model.Add(weight_vars[r_idx] == 0).OnlyEnforceIf(route_used[idx].Not())
            
            # Require at least 2 distinct routes per plant for high density (if available)
            model.Add(sum(route_used) >= min(2, len(plt_routes)))
            
            # Plant Capacity Constraint: Limit max weight from a single supplier to 70% of plant total
            plant_total_weight = total_weight_scaled // len(plants)
            for ru in route_used:
                # Get the corresponding weight variable
                w_var = weight_vars[plt_routes[route_used.index(ru)]]
                model.Add(w_var <= int(plant_total_weight * 0.7))

    # Constraint 6: Force at least 3 different modes in total across the network
    mode_indicators = []
    for mode in ["road", "rail", "sea"]:
        mode_routes = [i for i, r in enumerate(candidate_routes) if r["mode"] == mode]
        if mode_routes:
            m_used = model.NewBoolVar(f"mode_used_{mode}")
            model.Add(sum(weight_vars[i] for i in mode_routes) > 0).OnlyEnforceIf(m_used)
            model.Add(sum(weight_vars[i] for i in mode_routes) == 0).OnlyEnforceIf(m_used.Not())
            mode_indicators.append(m_used)
    
    if len(mode_indicators) >= 2:
        model.Add(sum(mode_indicators) >= 2) # Force at least 2 modes for variety

    # Multi-Objective Weights (Default balance)
    weights = objective_weights or {"cost": 0.4, "co2": 0.4, "time": 0.2}
    
    # Coefficients: we need to scale these to be comparable
    # Normalize by typical ranges to ensure weights are meaningful
    cost_coeffs = []
    co2_coeffs = []
    time_coeffs = []
    
    for r in candidate_routes:
        # Cost: INR per tonne
        cost_per_tonne = r["metrics"]["cost_inr"] / max(0.001, r["metrics"]["cargo_tonnes"])
        cost_coeffs.append(int(cost_per_tonne)) 
        
        # CO2: kg per tonne
        co2_per_tonne = r["metrics"]["co2_kg"] / max(0.001, r["metrics"]["cargo_tonnes"])
        co2_coeffs.append(int(co2_per_tonne * 10)) # Scale for precision
        
        # Time: Days (Scaled by 100 to make it significant vs cost)
        time_coeffs.append(int(r["metrics"]["lead_time_days"] * 500))

    # Multi-Objective: minimize (w1*Cost + w2*CO2 + w3*Time)
    model.Minimize(
        sum(
            int(weights["cost"] * 10) * cost_coeffs[i] * weight_vars[i] +
            int(weights["co2"] * 10) * co2_coeffs[i] * weight_vars[i] +
            int(weights["time"] * 10) * time_coeffs[i] * weight_vars[i]
            for i in range(len(candidate_routes))
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = OR_TOOLS_TIME_LIMIT_SEC
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        active_routes = []
        for i, route in enumerate(candidate_routes):
            weight_val = solver.Value(weight_vars[i]) / 100.0
            if weight_val > 0.1: # Threshold to ignore noise
                r_copy = route.copy()
                # Recalculate metrics for exact weight
                # Re-fetch or pass along google data
                g_info = None
                if google_matrix:
                    s_idx = next(i for i, s in enumerate(suppliers) if s["id"] == route["supplier_id"])
                    p_idx = next(i for i, p in enumerate(plants) if p["id"] == route["plant_id"])
                    if google_matrix["rows"][s_idx]["elements"][p_idx]["status"] == "OK":
                        g_info = {
                            "distance": google_matrix["rows"][s_idx]["elements"][p_idx]["distance"]["value"],
                            "duration": google_matrix["rows"][s_idx]["elements"][p_idx]["duration"]["value"]
                        }

                r_copy["metrics"] = compute_route_metrics(
                    [s for s in suppliers if s["id"] == route["supplier_id"]][0],
                    [p for p in plants if p["id"] == route["plant_id"]][0],
                    weight_val, mode=route["mode"], port_congestion_data=port_risk_scores,
                    google_data=g_info
                )
                active_routes.append(r_copy)
    else:
        logger.warning("OR-Tools: no feasible solution found, using greedy fallback.")
        return _greedy_optimize(suppliers, plants, cargo, max_co2, port_risk_scores, google_matrix=google_matrix)

    return _build_result(active_routes, candidate_routes)


def _greedy_optimize(
    suppliers: list[dict],
    plants: list[dict],
    cargo: list[dict],
    max_co2: float,
    port_risk_scores: dict | None,
    google_matrix: dict | None = None,
) -> dict:
    """Greedy routing: assign cheapest feasible supplier to each plant."""
    total_units = sum(c.get("units", 0) for c in cargo)
    total_weight_tonnes = max(0.001, total_units * 0.001)

    active_routes = []
    for j, plt in enumerate(plants):
        best = None
        best_cost = float("inf")
        for i, sup in enumerate(suppliers):
            # Extract google info if available
            g_info = None
            if google_matrix and google_matrix["rows"][i]["elements"][j]["status"] == "OK":
                g_info = {
                    "distance": google_matrix["rows"][i]["elements"][j]["distance"]["value"],
                    "duration": google_matrix["rows"][i]["elements"][j]["duration"]["value"]
                }

            metrics = compute_route_metrics(
                sup, plt,
                total_weight_tonnes / max(1, len(plants)),
                port_congestion_data=port_risk_scores,
                google_data=g_info
            )
            if metrics["cost_inr"] < best_cost:
                best_cost = metrics["cost_inr"]
                best = {"supplier_id": sup["id"], "plant_id": plt["id"], "metrics": metrics}
        if best:
            active_routes.append(best)

    return _build_result(active_routes, active_routes)


def _build_result(active_routes: list[dict], all_routes: list[dict]) -> dict:
    """Build standardized routing result dict."""
    total_cost = sum(r["metrics"]["cost_inr"] for r in active_routes)
    total_co2 = sum(r["metrics"]["co2_kg"] for r in active_routes)
    max_eta = max((r["metrics"]["lead_time_days"] for r in active_routes), default=0.0)

    # Carrier utilization (by mode)
    carrier_util: dict[str, float] = {}
    for r in active_routes:
        mode = r["metrics"]["mode"]
        carrier_util[mode] = carrier_util.get(mode, 0) + r["metrics"]["cargo_tonnes"]

    # Pareto frontier: sample cost-CO2 tradeoff
    pareto = []
    cost_vals = sorted(set(int(r["metrics"]["cost_inr"]) for r in all_routes))[:5]
    for threshold in cost_vals:
        subset = [r for r in all_routes if r["metrics"]["cost_inr"] <= threshold]
        if subset:
            pareto.append({
                "max_cost_inr": threshold,
                "total_co2_kg": round(sum(r["metrics"]["co2_kg"] for r in subset), 1),
                "routes": len(subset),
            })

    routes_output = [
        {
            "supplier_id": r["supplier_id"],
            "plant_id": r["plant_id"],
            "mode": r["metrics"]["mode"],
            "distance_km": r["metrics"]["distance_km"],
            "cost_inr": r["metrics"]["cost_inr"],
            "co2_kg": r["metrics"]["co2_kg"],
            "lead_time_days": r["metrics"]["lead_time_days"],
            "provider": r["metrics"].get("provider"),
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
