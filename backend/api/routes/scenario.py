"""
scenario.py (API route) — POST /api/scenario/run
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    ScenarioRequest, ScenarioResponse, Playbook, PlaybookStep, RouteArc
)
from backend.config import SUPPLIER_LOCATIONS, PLANT_LOCATIONS
from backend.optimization.scenario_runner import run_scenario, SCENARIOS
from backend.optimization.playbook_generator import generate_playbook
from backend.db.database import get_df_cached
from backend.kpi.baseline import compute_baseline_kpis

logger = logging.getLogger("chainmind.api.scenario")
router = APIRouter()


@router.post("/run", response_model=ScenarioResponse)
async def run_disruption_scenario(body: ScenarioRequest):
    """Run a named disruption scenario and generate response playbook."""
    try:
        if body.scenario_name not in SCENARIOS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scenario '{body.scenario_name}'. Valid: {list(SCENARIOS.keys())}"
            )

        df = await get_df_cached()
        baseline_kpis = compute_baseline_kpis(df) if df is not None else {}

        # Default cargo for scenario simulation
        cargo = [{"sku_id": f"SKU-{i:04d}", "units": 200} for i in range(1, 21)]

        # Default risk scores
        risk_scores = {sup["id"]: 35.0 for sup in SUPPLIER_LOCATIONS}

        # Default port congestion
        port_congestion = {
            "PORT-RTM": 42.0,
            "PORT-SHA": 68.0,
            "PORT-LAX": 55.0,
            "PORT-SIN": 35.0,
            "PORT-HAM": 28.0,
        }

        result = run_scenario(
            scenario_name=body.scenario_name,
            baseline_kpis=baseline_kpis,
            suppliers=SUPPLIER_LOCATIONS,
            plants=PLANT_LOCATIONS,
            port_congestion=port_congestion,
            cargo=cargo,
            risk_scores=risk_scores,
            override_params=body.override_params,
        )

        # Generate playbook
        playbook_data = await generate_playbook(
            scenario_name=body.scenario_name,
            description=result["description"],
            delta_kpis=result["delta_kpis"],
            recommended_routes=result["affected_routes"],
            risk_scores=risk_scores,
            top_3_skus=result["top_3_affected_skus"],
        )

        steps = [
            PlaybookStep(
                step=s.get("step", i + 1),
                action=s.get("action", ""),
                owner=s.get("owner", ""),
                timeline=s.get("timeline", ""),
                expected_impact=s.get("expected_impact", ""),
            )
            for i, s in enumerate(playbook_data.get("steps", []))
        ]

        playbook = Playbook(
            scenario=body.scenario_name,
            severity=playbook_data.get("severity", "MEDIUM"),
            summary=playbook_data.get("summary", ""),
            steps=steps,
            kpi_recovery_estimate_days=playbook_data.get("kpi_recovery_estimate_days", 14),
            source=playbook_data.get("source", "rule_based"),
            model=playbook_data.get("model"),
        )

        affected_routes = []
        for r in result["affected_routes"]:
            sup = next((s for s in SUPPLIER_LOCATIONS if s["id"] == r["supplier_id"]), None)
            plt = next((p for p in PLANT_LOCATIONS if p["id"] == r["plant_id"]), None)
            
            affected_routes.append(
                RouteArc(
                    supplier_id=r.get("supplier_id", ""),
                    plant_id=r.get("plant_id", ""),
                    mode=r.get("mode", "sea"),
                    distance_km=r.get("distance_km", 0),
                    cost_inr=r.get("cost_inr", 0),
                    co2_kg=r.get("co2_kg", 0),
                    lead_time_days=r.get("lead_time_days", 0),
                    origin_lat=sup["lat"] if sup else 0.0,
                    origin_lon=sup["lon"] if sup else 0.0,
                    dest_lat=plt["lat"] if plt else 0.0,
                    dest_lon=plt["lon"] if plt else 0.0,
                )
            )

        delta = result["delta_kpis"]
        cost_pct = delta.get("total_cost_pct_change", 0)
        summary = (
            f"{body.scenario_name} simulation complete. "
            f"Estimated cost impact: {'+' if cost_pct > 0 else ''}{cost_pct:.1f}%. "
            f"Recovery estimated in {playbook.kpi_recovery_estimate_days} days. "
            f"Follow the {playbook.severity}-priority playbook."
        )

        return ScenarioResponse(
            scenario_name=body.scenario_name,
            description=result["description"],
            delta_kpis=result["delta_kpis"],
            playbook=playbook,
            affected_routes=affected_routes,
            blocked_ports=result.get("blocked_ports", []),
            top_3_affected_skus=result["top_3_affected_skus"],
            recommendation_summary=summary,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Scenario run error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
