"""
reorder_policy.py — Dynamic reorder policies: ROP, EOQ, risk-adjusted.
"""
import logging
from enum import Enum
from typing import Optional

import numpy as np

from backend.models.inventory.safety_stock import (
    compute_safety_stock,
    compute_reorder_point,
    compute_eoq,
)

logger = logging.getLogger("chainmind.reorder_policy")


class Policy(str, Enum):
    STATISTICAL = "statistical"
    RISK_ADJUSTED = "risk_adjusted"
    RL = "rl"
    HYBRID = "hybrid"


def get_recommendation(
    sku_id: str,
    current_stock: float,
    demand_avg: float,
    demand_std: float,
    lead_time_avg: float,
    lead_time_std: float,
    unit_cost: float,
    risk_score: float = 0.0,
    pending_orders: float = 0.0,
    policy: Policy = Policy.STATISTICAL,
    service_level: float = 0.95,
) -> dict:
    """
    Compute inventory recommendation for a single SKU.

    Returns recommended_order, safety_stock, reorder_point,
    days_of_supply, and policy metadata.
    """
    ss = compute_safety_stock(demand_std, lead_time_avg, lead_time_std, demand_avg, service_level)
    rop = compute_reorder_point(demand_avg, lead_time_avg, ss)
    eoq = compute_eoq(
        annual_demand=demand_avg * 365,
        ordering_cost=150.0,
        holding_cost_per_unit=unit_cost * 0.25,
    )

    risk_adjusted = False

    if policy in (Policy.RISK_ADJUSTED, Policy.HYBRID):
        # Increase safety stock buffer by risk factor
        risk_factor = 1.0 + (risk_score / 100.0) * 0.5  # Up to 50% increase
        ss *= risk_factor
        rop = compute_reorder_point(demand_avg, lead_time_avg, ss)
        risk_adjusted = True

    # Effective stock (subtract in-transit orders only if they arrive in time)
    effective_stock = current_stock + pending_orders * 0.5  # 50% in-transit heuristic

    # Order recommendation
    if effective_stock <= rop:
        recommended_order = max(0.0, eoq + (rop - effective_stock))
    else:
        recommended_order = 0.0

    # Days of supply at current stock + pending
    days_of_supply = effective_stock / demand_avg if demand_avg > 0 else 0.0

    return {
        "sku_id": sku_id,
        "current_stock": round(current_stock, 0),
        "effective_stock": round(effective_stock, 0),
        "pending_orders": round(pending_orders, 0),
        "recommended_order": round(max(0, recommended_order), 0),
        "safety_stock": round(ss, 0),
        "reorder_point": round(rop, 0),
        "eoq": round(eoq, 0),
        "days_of_supply": round(days_of_supply, 1),
        "risk_score": risk_score,
        "risk_adjusted": risk_adjusted,
        "policy": policy.value,
        "service_level": service_level,
        "action": "ORDER" if recommended_order > 0 else "HOLD",
    }
