"""
anomaly_detector.py — Isolation Forest + Z-score disruption anomaly detection.
Detects anomalies in lead times, port congestion, weather severity, news scores.
"""
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger("chainmind.anomaly")

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "isolation_forest.pkl"
SCALER_PATH = Path(__file__).parent.parent.parent / "models" / "if_scaler.pkl"

FEATURES = [
    "lead_time_days",
    "port_congestion_index",
    "weather_severity_score",
    "news_severity_score",
]


def _build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Extract and normalize features for anomaly detection."""
    feature_df = pd.DataFrame()

    for col in FEATURES:
        if col in df.columns:
            feature_df[col] = df[col].fillna(df[col].median())
        else:
            feature_df[col] = 0.0  # Missing feature → zero (neutral)

    # Add z-score of lead_time_days as a derived feature
    if "lead_time_days" in df.columns:
        lt = df["lead_time_days"].fillna(df["lead_time_days"].median())
        feature_df["lead_time_z"] = (lt - lt.mean()) / (lt.std() + 1e-8)
    else:
        feature_df["lead_time_z"] = 0.0

    return feature_df.values


def train_isolation_forest(df: pd.DataFrame, contamination: float = 0.05) -> dict:
    """Train Isolation Forest on supply chain feature matrix."""
    X = _build_feature_matrix(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_scaled)

    # Save
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(iso, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    # Evaluate on training data
    scores = iso.score_samples(X_scaled)  # More negative = more anomalous
    labels = iso.predict(X_scaled)  # -1 = anomaly, 1 = normal
    n_anomalies = int((labels == -1).sum())

    logger.info("Isolation Forest trained. Anomalies: %d/%d (%.1f%%)",
                n_anomalies, len(df), n_anomalies / len(df) * 100)

    return {
        "n_samples": len(df),
        "n_anomalies": n_anomalies,
        "contamination_rate": n_anomalies / len(df),
        "model_path": str(MODEL_PATH),
    }


def load_isolation_forest():
    with open(MODEL_PATH, "rb") as f:
        iso = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        scaler = pickle.load(f)
    return iso, scaler


def score_anomaly(observation: dict) -> float:
    """
    Score a single observation for anomaly.
    Returns 0.0 (normal) to 1.0 (highly anomalous).
    """
    if not MODEL_PATH.exists():
        return _z_score_fallback(observation)

    try:
        iso, scaler = load_isolation_forest()
        X = np.array([[
            observation.get("lead_time_days", 14),
            observation.get("port_congestion_index", 30),
            observation.get("weather_severity_score", 0),
            observation.get("news_severity_score", 0),
            0.0,  # lead_time_z placeholder
        ]])
        X_scaled = scaler.transform(X)
        raw_score = iso.score_samples(X_scaled)[0]
        # Map: -0.5 (very anomalous) to 0.5 (very normal) → 0–1
        normalized = float(np.clip((-raw_score - 0.0) / 0.5, 0.0, 1.0))
        return normalized
    except Exception as exc:
        logger.warning("Anomaly score failed: %s. Using z-score fallback.", exc)
        return _z_score_fallback(observation)


def _z_score_fallback(observation: dict) -> float:
    """Simple z-score based anomaly score when model not available."""
    lead_time = observation.get("lead_time_days", 14)
    port_cong = observation.get("port_congestion_index", 30)
    weather = observation.get("weather_severity_score", 0)

    # Normalized deviations from typical values
    lt_z = abs(lead_time - 14) / 7.0
    port_z = max(0, (port_cong - 40) / 30.0)
    weather_z = weather / 100.0

    combined = (lt_z * 0.5 + port_z * 0.3 + weather_z * 0.2)
    return float(min(1.0, combined))


def z_score_batch(series: pd.Series) -> pd.Series:
    """Compute z-scores for a pandas Series."""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - mean) / std
