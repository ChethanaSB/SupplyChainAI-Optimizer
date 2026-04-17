"""
scenario_runner.py — 5 named disruption scenario executor.
For each scenario: re-runs routing + inventory optimization,
computes delta KPIs vs baseline, and outputs recommended actions.
"""
import logging
from copy import deepcopy
from typing import Any

from backend.config import SUPPLIER_LOCATIONS, PLANT_LOCATIONS, KEY_PORTS

logger = logging.getLogger("chainmind.scenarios")

# ─── Scenario definitions ─────────────────────────────────────────────────────

SCENARIOS: dict[str, dict] = {
    "PORT_CLOSURE": {
        "name": "PORT_CLOSURE",
        "description": "Top-2 most congested ports blocked for 14 days",
        "params": {
            "block_top_n_ports": 2,
            "duration_days": 14,
        },
    },
    "SUPPLIER_DELAY": {
        "name": "SUPPLIER_DELAY",
        "description": "Highest-risk supplier lead time multiplied × 2.5",
        "params": {
            "lead_time_multiplier": 2.5,
            "target": "highest_risk_supplier",
        },
    },
    "CARRIER_CRUNCH": {
        "name": "CARRIER_CRUNCH",
        "description": "Carrier capacity reduced by 40% on all lanes",
        "params": {
            "capacity_factor": 0.60,
        },
    },
    "DEMAND_SPIKE": {
        "name": "DEMAND_SPIKE",
        "description": "Demand multiplied × 1.8 for top 10 SKUs",
        "params": {
            "demand_multiplier": 1.8,
            "top_n_skus": 10,
        },
    },
    "COMBINED": {
        "name": "COMBINED",
        "description": "PORT_CLOSURE + SUPPLIER_DELAY simultaneously",
        "params": {
            "block_top_n_ports": 2,
            "duration_days": 14,
            "lead_time_multiplier": 2.5,
            "target": "highest_risk_supplier",
        },
    },
}


def run_scenario(
    scenario_name: str,
    baseline_kpis: dict,
    suppliers: list[dict],
    plants: list[dict],
    port_congestion: dict,
    cargo: list[dict],
    risk_scores: dict,
    override_params: dict | None = None,
) -> dict:
    """
    Execute a named disruption scenario.

    Args:
        scenario_name: One of PORT_CLOSURE, SUPPLIER_DELAY, CARRIER_CRUNCH,
                       DEMAND_SPIKE, COMBINED
        baseline_kpis: Current KPI dict from kpi/tracker.py
        suppliers: List of supplier metadata dicts
        plants: List of plant metadata dicts
        port_congestion: {port_id: congestion_index} dict
        cargo: List of {sku_id, units} cargo dicts
        risk_scores: {supplier_id: risk_score} dict
        override_params: Optional parameter overrides

    Returns:
        {scenario_name, delta_kpis, affected_routes, playbook_context}
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_name}. Valid: {list(SCENARIOS.keys())}")

    config = deepcopy(SCENARIOS[scenario_name])
    if override_params:
        config["params"].update(override_params)

    params = config["params"]
    modified_suppliers = deepcopy(suppliers)
    modified_cargo = deepcopy(cargo)
    blocked_ports: list[str] = []
    capacity_factor = 1.0

    # ─── Apply scenario modifications ─────────────────────────────────────────

    if scenario_name in ("PORT_CLOSURE", "COMBINED"):
        # Block top-N most congested ports
        sorted_ports = sorted(port_congestion.items(), key=lambda x: -x[1])
        n_block = int(params.get("block_top_n_ports", 2))
        blocked_ports = [p[0] for p in sorted_ports[:n_block]]
        logger.info("Scenario %s: blocking ports %s", scenario_name, blocked_ports)

    if scenario_name in ("SUPPLIER_DELAY", "COMBINED"):
        # Multiply lead time of highest-risk supplier
        if risk_scores:
            worst_supplier = max(risk_scores, key=risk_scores.get)
            lt_mult = float(params.get("lead_time_multiplier", 2.5))
            for sup in modified_suppliers:
                if sup["id"] == worst_supplier:
                    sup["_lead_time_multiplier"] = lt_mult
                    logger.info("Scenario %s: supplier %s lead time ×%.1f",
                                scenario_name, worst_supplier, lt_mult)

    if scenario_name == "CARRIER_CRUNCH":
        capacity_factor = float(params.get("capacity_factor", 0.60))
        logger.info("Scenario CARRIER_CRUNCH: capacity factor=%.2f", capacity_factor)

    if scenario_name == "DEMAND_SPIKE":
        top_n = int(params.get("top_n_skus", 10))
        mult = float(params.get("demand_multiplier", 1.8))
        for i in range(min(top_n, len(modified_cargo))):
            modified_cargo[i]["units"] = int(modified_cargo[i].get("units", 100) * mult)
        logger.info("Scenario DEMAND_SPIKE: multiplied demand ×%.1f for %d SKUs", mult, top_n)

    # ─── Re-run routing with scenario modifications ────────────────────────────
    from backend.optimization.routing import optimize_routes

    scenario_route_result = optimize_routes(
        suppliers=modified_suppliers,
        plants=plants,
        customers=[],  # Simplified: plant-level aggregation
        cargo=modified_cargo,
        constraints={},
        port_risk_scores={p: 95.0 for p in blocked_ports},  # Mark blocked as very high risk
        blocked_supplier_ids=[],  # Use risk scores to constrain
        carrier_capacity_factor=capacity_factor,
    )

    # ─── Compute delta KPIs ────────────────────────────────────────────────────
    delta_kpis = _compute_delta_kpis(baseline_kpis, scenario_route_result, scenario_name, params)

    # ─── Identify affected routes ─────────────────────────────────────────────
    affected_routes = scenario_route_result.get("routes", [])

    # Top-3 affected SKUs (by demand impact)
    top_3_skus = [c["sku_id"] for c in sorted(modified_cargo, key=lambda x: -x.get("units", 0))[:3]]

    logger.info(
        "Scenario %s complete: cost_delta=%.1f%%, co2_delta=%.1f%%",
        scenario_name,
        delta_kpis.get("total_cost_pct_change", 0),
        delta_kpis.get("co2_pct_change", 0),
    )

    return {
        "scenario_name": scenario_name,
        "description": config["description"],
        "delta_kpis": delta_kpis,
        "route_result": scenario_route_result,
        "affected_routes": affected_routes[:5],  # Top 5 for display
        "blocked_ports": blocked_ports,
        "top_3_affected_skus": top_3_skus,
        "capacity_factor": capacity_factor,
        "params_applied": params,
        "playbook_context": {
            "scenario_name": scenario_name,
            "delta_kpis": delta_kpis,
            "recommended_routes": affected_routes[:3],
            "risk_scores": risk_scores,
        },
    }


def _compute_delta_kpis(
    baseline: dict,
    scenario_result: dict,
    scenario_name: str,
    params: dict,
) -> dict:
    """Compute percentage KPI changes vs baseline."""
    base_cost = baseline.get("total_logistics_cost", 100_000)
    base_co2 = baseline.get("co2_emissions_kg", 50_000)
    base_lead = baseline.get("avg_lead_time_days", 14.0)
    base_service = baseline.get("service_level_pct", 92.0)

    scenario_cost = scenario_result.get("total_cost", base_cost)
    scenario_co2 = scenario_result.get("total_co2", base_co2)
    scenario_lead = scenario_result.get("max_eta_days", base_lead)

    # Estimate service level impact by scenario type
    service_impact = {
        "PORT_CLOSURE": -12.0,
        "SUPPLIER_DELAY": -8.0,
        "CARRIER_CRUNCH": -6.0,
        "DEMAND_SPIKE": -5.0,
        "COMBINED": -18.0,
    }.get(scenario_name, -5.0)

    scenario_service = max(50.0, base_service + service_impact)

    def pct_change(new, old):
        if old == 0:
            return 0.0
        return round((new - old) / old * 100, 1)

    return {
        "total_cost_absolute": round(scenario_cost, 2),
        "total_cost_pct_change": pct_change(scenario_cost, base_cost),
        "co2_absolute": round(scenario_co2, 2),
        "co2_pct_change": pct_change(scenario_co2, base_co2),
        "lead_time_absolute": round(scenario_lead, 1),
        "lead_time_pct_change": pct_change(scenario_lead, base_lead),
        "service_level_absolute": round(scenario_service, 1),
        "service_level_pct_change": round(service_impact, 1),
        "stockout_risk_increase_pct": round(abs(service_impact) * 2, 1),
    }


def run_all_scenarios(
    baseline_kpis: dict,
    suppliers: list[dict],
    plants: list[dict],
    port_congestion: dict,
    cargo: list[dict],
    risk_scores: dict,
) -> list[dict]:
    """Run all 5 scenarios and return results."""
    results = []
    for scenario_name in SCENARIOS:
        try:
            result = run_scenario(
                scenario_name=scenario_name,
                baseline_kpis=baseline_kpis,
                suppliers=suppliers,
                plants=plants,
                port_congestion=port_congestion,
                cargo=cargo,
                risk_scores=risk_scores,
            )
            results.append(result)
        except Exception as exc:
            logger.error("Scenario %s failed: %s", scenario_name, exc)
    return results
