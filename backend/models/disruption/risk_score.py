"""
risk_score.py — Composite risk index (0–100) for supply chain nodes.
Weights: anomaly × 0.3 + NLP severity × 0.4 + Monte Carlo P90 × 0.3
"""
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("chainmind.risk_score")


def compute_risk_score(
    anomaly_score: float,          # 0.0 – 1.0 from Isolation Forest
    nlp_severity_score: float,     # 0.0 – 1.0 (normalized from 1–5 severity)
    monte_carlo_p90: float,        # 0.0 – 1.0 disruption probability at P90
    weights: dict | None = None,
) -> dict:
    """
    Compute composite risk index.

    Args:
        anomaly_score: Isolation Forest anomaly score (0=normal, 1=highly anomalous)
        nlp_severity_score: Normalized NLP severity (0=low, 1=high disruption risk)
        monte_carlo_p90: Monte Carlo P90 disruption probability (0–1)
        weights: Override default {anomaly: 0.3, nlp: 0.4, mc: 0.3}

    Returns:
        {risk_score: 0–100, components: {...}, risk_level: "LOW"|"MEDIUM"|"HIGH"}
    """
    w = weights or {"anomaly": 0.3, "nlp": 0.4, "mc": 0.3}

    # Clamp inputs
    a = float(np.clip(anomaly_score, 0.0, 1.0))
    n = float(np.clip(nlp_severity_score, 0.0, 1.0))
    m = float(np.clip(monte_carlo_p90, 0.0, 1.0))

    composite = (a * w["anomaly"]) + (n * w["nlp"]) + (m * w["mc"])
    risk_score = round(float(np.clip(composite * 100, 0, 100)), 1)

    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "components": {
            "anomaly_contribution": round(a * w["anomaly"] * 100, 1),
            "nlp_contribution": round(n * w["nlp"] * 100, 1),
            "monte_carlo_contribution": round(m * w["mc"] * 100, 1),
        },
        "inputs": {
            "anomaly_score": round(a, 3),
            "nlp_severity_score": round(n, 3),
            "monte_carlo_p90": round(m, 3),
        },
        "weights": w,
    }


def normalize_nlp_severity(severity_1_to_5: int) -> float:
    """Convert 1–5 severity scale to 0–1."""
    return float(np.clip((severity_1_to_5 - 1) / 4.0, 0.0, 1.0))


def compute_network_risk_index(node_risks: list[dict], volumes: list[float] | None = None) -> float:
    """
    Compute network-level risk as volume-weighted average of node risk scores.
    """
    if not node_risks:
        return 0.0

    scores = [n.get("risk_score", 0.0) for n in node_risks]

    if volumes and len(volumes) == len(scores):
        total_vol = sum(volumes)
        if total_vol > 0:
            weighted = sum(s * v for s, v in zip(scores, volumes)) / total_vol
            return round(weighted, 1)

    return round(float(np.mean(scores)), 1)
