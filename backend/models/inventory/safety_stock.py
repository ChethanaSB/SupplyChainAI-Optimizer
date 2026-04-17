"""
safety_stock.py — Statistical safety stock calculation.
Z × σ_demand × √lead_time at configurable service levels.
"""
import logging
import math
from typing import Optional
import numpy as np

logger = logging.getLogger("chainmind.safety_stock")


def compute_safety_stock(
    demand_std: float,
    lead_time_avg: float,
    lead_time_std: float = 0.0,
    demand_avg: float = 0.0,
    service_level: float = 0.95,
) -> float:
    """
    Compute safety stock for given service level.

    SS = Z × √(LT × σ_demand² + demand_avg² × σ_LT²)

    Args:
        demand_std: Standard deviation of daily demand
        lead_time_avg: Average lead time in days
        lead_time_std: Standard deviation of lead time
        demand_avg: Average daily demand
        service_level: Target service level (0.95 = 95%)

    Returns:
        Safety stock in units (always positive)
    """
    from scipy.stats import norm
    z = float(norm.ppf(service_level))

    # Combined variability formula
    variance = (lead_time_avg * demand_std**2) + (demand_avg**2 * lead_time_std**2)
    ss = z * math.sqrt(max(0, variance))

    return round(max(0.0, ss), 1)


def compute_reorder_point(
    demand_avg: float,
    lead_time_avg: float,
    safety_stock: float,
) -> float:
    """
    ROP = (avg_daily_demand × avg_lead_time) + safety_stock
    """
    return round(demand_avg * lead_time_avg + safety_stock, 1)


def compute_eoq(
    annual_demand: float,
    ordering_cost: float,
    holding_cost_per_unit: float,
) -> float:
    """
    Economic Order Quantity: EOQ = √(2DS/H)

    Args:
        annual_demand: Annual demand in units
        ordering_cost: Fixed cost per order ($)
        holding_cost_per_unit: Annual holding cost per unit ($)
    """
    if holding_cost_per_unit <= 0:
        return float(annual_demand / 12)  # Monthly order as fallback
    eoq = math.sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)
    return round(eoq, 1)


def batch_safety_stock(
    sku_df,  # DataFrame with sku_id, demand_units, lead_time_days, unit_cost
    service_level: float = 0.95,
) -> list[dict]:
    """Compute safety stock for all SKUs from historical data."""
    import pandas as pd
    results = []

    for sku_id, group in sku_df.groupby("sku_id"):
        demand = group["demand_units"].values
        lead_times = group["lead_time_days"].values

        demand_avg = float(np.mean(demand))
        demand_std = float(np.std(demand))
        lt_avg = float(np.mean(lead_times))
        lt_std = float(np.std(lead_times))
        unit_cost = float(group["unit_cost"].iloc[-1]) if "unit_cost" in group.columns else 100.0

        ss = compute_safety_stock(demand_std, lt_avg, lt_std, demand_avg, service_level)
        rop = compute_reorder_point(demand_avg, lt_avg, ss)

        # Annual holding cost = 25% of unit cost
        holding_cost = unit_cost * 0.25
        annual_demand = demand_avg * 365
        eoq = compute_eoq(annual_demand, ordering_cost=150.0, holding_cost_per_unit=holding_cost)

        results.append({
            "sku_id": sku_id,
            "demand_avg_daily": round(demand_avg, 1),
            "demand_std_daily": round(demand_std, 1),
            "lead_time_avg_days": round(lt_avg, 1),
            "lead_time_std_days": round(lt_std, 1),
            "safety_stock_units": ss,
            "reorder_point": rop,
            "eoq": eoq,
            "days_of_supply": round(ss / demand_avg, 1) if demand_avg > 0 else 0.0,
            "service_level": service_level,
        })

    logger.info("Computed safety stock for %d SKUs.", len(results))
    return results
