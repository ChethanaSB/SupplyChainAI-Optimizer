"""
normalizer.py — Feature scaling, lag features, and time-series preprocessing.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import pickle
from pathlib import Path

logger = logging.getLogger("chainmind.normalizer")

SCALER_PATH = Path(__file__).parent.parent.parent / "models" / "scaler.pkl"


def add_lag_features(
    df: pd.DataFrame,
    target_col: str = "demand_units",
    lags: list[int] = [1, 7, 14, 28],
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Add lag and rolling features for time series modeling."""
    df = df.copy()
    group_cols = group_cols or ["sku_id", "region_id"]

    sort_cols = group_cols + ["date"]
    df = df.sort_values(sort_cols).reset_index(drop=True)

    group = df.groupby(group_cols)[target_col]

    for lag in lags:
        df[f"{target_col}_lag_{lag}"] = group.shift(lag)

    # Rolling statistics
    for window in [7, 14, 30]:
        df[f"{target_col}_rollmean_{window}"] = (
            group.shift(1).transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f"{target_col}_rollstd_{window}"] = (
            group.shift(1).transform(lambda x: x.rolling(window, min_periods=1).std().fillna(0))
        )

    # Time features
    df["date"] = pd.to_datetime(df["date"])
    df["day_of_week"] = df["date"].dt.dayofweek
    df["day_of_year"] = df["date"].dt.dayofyear
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["year"] = df["date"].dt.year
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    logger.info("Added lag features; shape: %s", df.shape)
    return df


def fit_scalers(
    df: pd.DataFrame,
    numerical_cols: list[str],
) -> dict[str, StandardScaler]:
    """Fit StandardScalers for each numerical column."""
    scalers = {}
    for col in numerical_cols:
        if col in df.columns:
            sc = StandardScaler()
            sc.fit(df[[col]].dropna())
            scalers[col] = sc

    # Save scalers
    SCALER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scalers, f)
    logger.info("Fitted %d scalers, saved to %s", len(scalers), SCALER_PATH)
    return scalers


def load_scalers() -> dict[str, StandardScaler]:
    if not SCALER_PATH.exists():
        raise FileNotFoundError(f"Scalers not found at {SCALER_PATH}. Run training first.")
    with open(SCALER_PATH, "rb") as f:
        return pickle.load(f)


def apply_scalers(df: pd.DataFrame, scalers: dict) -> pd.DataFrame:
    df = df.copy()
    for col, sc in scalers.items():
        if col in df.columns:
            df[col] = sc.transform(df[[col]])
    return df
