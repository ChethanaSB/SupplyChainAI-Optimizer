"""
playbook_generator.py — LangChain + Anthropic Claude playbook generator.
Generates structured 5-step response playbooks for disruption scenarios.
"""
import json
import logging
from typing import Optional

from backend.config import GEMINI_API_KEY, FEATURES

logger = logging.getLogger("chainmind.playbook")

PLAYBOOK_PROMPT = """You are a logistics operations expert at ZF Group, a global automotive supplier.
Given this disruption scenario and optimization output, generate a structured 5-step response playbook
for the logistics manager. Each step must have: action, owner, timeline, expected_impact.

Return ONLY valid JSON in this exact format:
{{
  "scenario": "{scenario_name}",
  "severity": "HIGH|MEDIUM|LOW",
  "summary": "2-3 sentence executive summary of the disruption and recommended response",
  "steps": [
    {{
      "step": 1,
      "action": "specific action to take",
      "owner": "role/department responsible",
      "timeline": "immediate|24h|48h|1 week|2 weeks",
      "expected_impact": "quantified expected improvement"
    }},
    ... (5 steps total)
  ],
  "kpi_recovery_estimate_days": 14
}}

Scenario: {scenario_name}
Description: {description}
KPI Impact: {delta_kpis}
Recommended Routes: {recommended_routes}
Risk Context: {risk_scores}
Top Affected SKUs: {top_3_skus}
"""


async def generate_playbook(
    scenario_name: str,
    description: str,
    delta_kpis: dict,
    recommended_routes: list,
    risk_scores: dict,
    top_3_skus: list[str],
    model: str = "gemini-1.5-flash",
) -> dict:
    """
    Generate structured playbook using Gemini via Google Generative AI.
    Falls back to rule-based playbook if API key not configured.
    """
    if not FEATURES["ai_playbooks"]:
        logger.warning("AI playbooks disabled — GEMINI_API_KEY not set. Using rule-based fallback.")
        return _rule_based_playbook(scenario_name, description, delta_kpis, top_3_skus)

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from backend.config import GEMINI_API_KEY

        llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=GEMINI_API_KEY,
            temperature=0.7,
        )

        prompt = PLAYBOOK_PROMPT.format(
            scenario_name=scenario_name,
            description=description,
            delta_kpis=json.dumps(delta_kpis, indent=2),
            recommended_routes=json.dumps(recommended_routes[:3], indent=2),
            risk_scores=json.dumps(
                {k: round(v, 1) for k, v in (risk_scores or {}).items()}, indent=2
            ),
            top_3_skus=", ".join(top_3_skus),
        )

        response = await llm.ainvoke(prompt)
        response_text = response.content
        
        # Extract JSON from response
        playbook_json = _extract_json(response_text)
        playbook_json["source"] = "gemini"
        playbook_json["model"] = model
        return playbook_json

    except Exception as exc:
        logger.error("Gemini playbook generation failed: %s. Using rule-based fallback.", exc)
        return _rule_based_playbook(scenario_name, description, delta_kpis, top_3_skus)


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response text."""
    import re
    # Try to find JSON block
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    return json.loads(text)


def _rule_based_playbook(
    scenario_name: str,
    description: str,
    delta_kpis: dict,
    top_3_skus: list[str],
) -> dict:
    """Deterministic rule-based playbook when LLM unavailable."""
    cost_change = delta_kpis.get("total_cost_pct_change", 0)
    severity = "HIGH" if abs(cost_change) > 20 else "MEDIUM" if abs(cost_change) > 10 else "LOW"

    PLAYBOOKS: dict[str, list[dict]] = {
        "PORT_CLOSURE": [
            {"step": 1, "action": "Activate alternative port routing via Hamburg/Rotterdam bypass",
             "owner": "Logistics Manager", "timeline": "immediate",
             "expected_impact": "Reduce delay by 3–5 days"},
            {"step": 2, "action": "Alert tier-1 suppliers to pre-ship affected SKUs",
             "owner": "Procurement", "timeline": "24h",
             "expected_impact": "Build 2-week buffer inventory"},
            {"step": 3, "action": "Switch affected lanes from sea to air freight for critical SKUs",
             "owner": "Freight Operations", "timeline": "48h",
             "expected_impact": "Maintain service level above 85%"},
            {"step": 4, "action": f"Expedite safety stock for top SKUs: {', '.join(top_3_skus)}",
             "owner": "Inventory Control", "timeline": "1 week",
             "expected_impact": "Prevent stockouts for top-volume SKUs"},
            {"step": 5, "action": "Communicate ETA delays to customers and adjust SLA promises",
             "owner": "Customer Service", "timeline": "immediate",
             "expected_impact": "Reduce customer escalations by 60%"},
        ],
        "SUPPLIER_DELAY": [
            {"step": 1, "action": "Qualify backup supplier for delayed materials",
             "owner": "Procurement", "timeline": "48h",
             "expected_impact": "Reduce single-supplier dependency"},
            {"step": 2, "action": "Place emergency orders with secondary suppliers",
             "owner": "Procurement", "timeline": "24h",
             "expected_impact": "Cover 60% of volume gap"},
            {"step": 3, "action": "Re-schedule production to consume available buffer stock first",
             "owner": "Production Planning", "timeline": "immediate",
             "expected_impact": "Avoid line stoppages for 7 days"},
            {"step": 4, "action": f"Increase safety stock targets for {', '.join(top_3_skus)}",
             "owner": "Inventory Control", "timeline": "1 week",
             "expected_impact": "Provide 14-day disruption buffer"},
            {"step": 5, "action": "Negotiate priority allocation with delayed supplier",
             "owner": "Supplier Relations", "timeline": "48h",
             "expected_impact": "Recover 30% of delayed volume"},
        ],
        "CARRIER_CRUNCH": [
            {"step": 1, "action": "Activate backup carrier contracts (DHL, Kuehne+Nagel)",
             "owner": "Freight Operations", "timeline": "immediate",
             "expected_impact": "Restore 40% capacity within 24h"},
            {"step": 2, "action": "Consolidate shipments to maximize container utilization",
             "owner": "Logistics Manager", "timeline": "24h",
             "expected_impact": "Reduce cost impact by 15%"},
            {"step": 3, "action": "Prioritize shipments by customer SLA and margin",
             "owner": "Sales Operations", "timeline": "immediate",
             "expected_impact": "Protect top-tier customer commitments"},
            {"step": 4, "action": "Explore rail alternatives for European lanes",
             "owner": "Freight Operations", "timeline": "48h",
             "expected_impact": "Replace 25% of road capacity at lower cost"},
            {"step": 5, "action": "Develop carrier diversification strategy for resilience",
             "owner": "Supply Chain Strategy", "timeline": "2 weeks",
             "expected_impact": "Reduce future carrier crunch risk by 50%"},
        ],
        "DEMAND_SPIKE": [
            {"step": 1, "action": "Trigger emergency replenishment orders for top 10 SKUs",
             "owner": "Inventory Control", "timeline": "immediate",
             "expected_impact": "Prevent stockouts within 48h"},
            {"step": 2, "action": "Increase production rate at plants with spare capacity",
             "owner": "Production Planning", "timeline": "24h",
             "expected_impact": "Cover 40% of demand spike from internal production"},
            {"step": 3, "action": "Allocate available inventory by customer priority tier",
             "owner": "Sales Operations", "timeline": "immediate",
             "expected_impact": "Protect A-tier customer service levels"},
            {"step": 4, "action": "Negotiate expedited delivery with key suppliers",
             "owner": "Procurement", "timeline": "24h",
             "expected_impact": "Reduce lead time by 30%"},
            {"step": 5, "action": "Update demand forecast models with spike data",
             "owner": "Demand Planning", "timeline": "1 week",
             "expected_impact": "Improve future forecast accuracy by 10%"},
        ],
        "COMBINED": [
            {"step": 1, "action": "Declare supply emergency — activate crisis response team",
             "owner": "VP Supply Chain", "timeline": "immediate",
             "expected_impact": "Coordinate cross-functional response"},
            {"step": 2, "action": "Route all sea freight via alternative ports (Singapore bypass)",
             "owner": "Freight Operations", "timeline": "24h",
             "expected_impact": "Maintain 70% of sea freight volume"},
            {"step": 3, "action": "Emergency air freight for critical automotive components",
             "owner": "Logistics Manager", "timeline": "immediate",
             "expected_impact": "Prevent production line stoppage"},
            {"step": 4, "action": "Activate all backup suppliers simultaneously",
             "owner": "Procurement", "timeline": "48h",
             "expected_impact": "Cover 80% of disrupted supplier volume"},
            {"step": 5, "action": "Customer communication: 14-day delay forecast with recovery plan",
             "owner": "Customer Service + Management", "timeline": "immediate",
             "expected_impact": "Manage expectations and protect key relationships"},
        ],
    }

    steps = PLAYBOOKS.get(scenario_name, PLAYBOOKS["PORT_CLOSURE"])

    return {
        "scenario": scenario_name,
        "severity": severity,
        "summary": (
            f"The {scenario_name.replace('_', ' ').title()} scenario has caused a "
            f"{abs(cost_change):.1f}% {'increase' if cost_change > 0 else 'decrease'} in logistics costs. "
            f"Immediate action is required to maintain service levels above 85% and minimize stockout risk."
        ),
        "steps": steps,
        "kpi_recovery_estimate_days": 14,
        "source": "rule_based",
        "model": "none",
        "affected_skus": top_3_skus,
    }
