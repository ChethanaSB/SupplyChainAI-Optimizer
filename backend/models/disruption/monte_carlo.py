"""
monte_carlo.py — Monte Carlo disruption probability simulator.
Simulates 10,000 paths for 30-day window per supplier node.
Outputs P50/P90 disruption probability.
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("chainmind.monte_carlo")

N_SIMULATIONS = 10_000
FORECAST_DAYS = 30


def simulate_supplier_disruption(
    supplier_id: str,
    base_lead_time: float = 14.0,
    lead_time_std: float = 3.0,
    port_congestion: float = 30.0,
    weather_severity: float = 0.0,
    news_severity: float = 1.0,
    seed: Optional[int] = None,
) -> dict:
    """
    Monte Carlo simulation of disruption probability for a supplier node.

    Returns:
        {
          supplier_id, p50_probability, p90_probability,
          expected_delay_days_p50, expected_delay_days_p90,
          paths_summary
        }
    """
    rng = np.random.default_rng(seed)

    # Base disruption probability from signals
    base_prob = _compute_base_probability(port_congestion, weather_severity, news_severity)

    # Simulate N paths of daily disruption events over FORECAST_DAYS days
    # Each day has an independent disruption event probability
    daily_prob = base_prob / FORECAST_DAYS  # Spread over horizon

    # Bernoulli trials: disruption on day i
    disruptions = rng.binomial(n=1, p=daily_prob, size=(N_SIMULATIONS, FORECAST_DAYS))

    # Total disruption days per path
    disruption_days = disruptions.sum(axis=1)  # Shape: (N_SIMULATIONS,)

    # Lead time augmentation per path
    lead_time_samples = rng.normal(base_lead_time, lead_time_std, N_SIMULATIONS)
    delay_factor = 1.0 + (disruption_days / FORECAST_DAYS) * 2.5  # Up to 3.5× delay
    simulated_lead_times = lead_time_samples * delay_factor

    # Probability that at least one disruption day occurs
    any_disruption = (disruption_days > 0).astype(float)
    p50_prob = float(np.percentile(any_disruption, 50))
    p90_prob = float(np.percentile(any_disruption, 90))

    # Mean probability across simulations
    mean_prob = float(any_disruption.mean())

    # Expected delay days
    delay_days = simulated_lead_times - base_lead_time
    p50_delay = float(np.percentile(delay_days, 50))
    p90_delay = float(np.percentile(delay_days, 90))

    logger.debug(
        "MC supplier=%s: base_prob=%.3f, mean_disruption_prob=%.3f, P90_delay=%.1fd",
        supplier_id, base_prob, mean_prob, p90_delay
    )

    return {
        "supplier_id": supplier_id,
        "n_simulations": N_SIMULATIONS,
        "forecast_days": FORECAST_DAYS,
        "base_disruption_probability": round(base_prob, 4),
        "mean_disruption_probability": round(mean_prob, 4),
        "p50_disruption_probability": round(p50_prob, 4),
        "p90_disruption_probability": round(p90_prob, 4),
        "expected_delay_days_p50": round(p50_delay, 1),
        "expected_delay_days_p90": round(p90_delay, 1),
        "disruption_days_distribution": {
            "p25": float(np.percentile(disruption_days, 25)),
            "p50": float(np.percentile(disruption_days, 50)),
            "p75": float(np.percentile(disruption_days, 75)),
            "p90": float(np.percentile(disruption_days, 90)),
            "max": float(disruption_days.max()),
        },
        "lead_time_distribution": {
            "p10": round(float(np.percentile(simulated_lead_times, 10)), 1),
            "p50": round(float(np.percentile(simulated_lead_times, 50)), 1),
            "p90": round(float(np.percentile(simulated_lead_times, 90)), 1),
        },
    }


def _compute_base_probability(
    port_congestion: float,
    weather_severity: float,
    news_severity: float,
) -> float:
    """
    Compute base 30-day disruption probability from input signals.
    Returns value in [0, 1].
    """
    # Port congestion: 0-100 → 0-0.4 contribution
    port_contribution = (port_congestion / 100.0) * 0.4

    # Weather severity: 0-100 → 0-0.3 contribution
    weather_contribution = (weather_severity / 100.0) * 0.3

    # News severity: 1-5 → 0-0.3 contribution
    news_contribution = ((news_severity - 1) / 4.0) * 0.3

    total = port_contribution + weather_contribution + news_contribution
    return float(np.clip(total, 0.0, 0.95))


def run_network_simulation(
    supplier_contexts: list[dict],
) -> list[dict]:
    """Run Monte Carlo for all supplier nodes."""
    results = []
    for ctx in supplier_contexts:
        result = simulate_supplier_disruption(
            supplier_id=ctx.get("supplier_id", "UNKNOWN"),
            base_lead_time=ctx.get("base_lead_time", 14.0),
            lead_time_std=ctx.get("lead_time_std", 3.0),
            port_congestion=ctx.get("port_congestion_index", 30.0),
            weather_severity=ctx.get("weather_severity_score", 0.0),
            news_severity=ctx.get("news_severity_score", 1.0),
            seed=42,
        )
        results.append(result)
    logger.info("Monte Carlo simulation complete for %d suppliers.", len(results))
    return results
