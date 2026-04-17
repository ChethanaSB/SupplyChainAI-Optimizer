"""
generate_dataset.py — Synthetic 3-year supply chain dataset generator.

Generates realistic daily supply chain data for 50 SKUs, 8 suppliers,
5 plants, 12 customer regions. Injects seasonality, holiday spikes,
and historical disruption events. Saves to PostgreSQL via SQLAlchemy.
"""
import asyncio
import logging
import random
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("chainmind.synthetic")

SEED = 42
rng = np.random.default_rng(SEED)

# ─── Topology ─────────────────────────────────────────────────────────────────
SUPPLIER_IDS = [f"SUP-{i:02d}" for i in range(1, 9)]
PLANT_IDS = [f"PLT-{i:02d}" for i in range(1, 6)]
REGION_IDS = [f"REG-{i:02d}" for i in range(1, 13)]
CARRIER_IDS = ["CAR-DHL", "CAR-FEDEX", "CAR-MSC", "CAR-MAERSK", "CAR-DB-SCHENKER"]
SKU_IDS = [f"SKU-{i:04d}" for i in range(1, 51)]

# ─── SKU metadata ─────────────────────────────────────────────────────────────
SKU_META: dict[str, dict] = {
    sku: {
        "base_demand": rng.integers(50, 500),
        "unit_cost": round(rng.uniform(10, 2000), 2),
        "co2_per_unit": round(rng.uniform(0.5, 25.0), 3),
        "lead_time_base": rng.integers(3, 21),
        "volatility": rng.uniform(0.05, 0.35),
    }
    for sku in SKU_IDS
}

# ─── Historical disruption windows ────────────────────────────────────────────
DISRUPTIONS: list[dict] = [
    {
        "name": "Suez Canal Blockage",
        "start": date(2023, 3, 23),
        "end": date(2023, 4, 3),
        "type": "PORT_DISRUPTION",
        "affected_suppliers": ["SUP-01", "SUP-07"],
        "lead_time_multiplier": 2.8,
        "demand_multiplier": 0.7,
    },
    {
        "name": "Shanghai COVID Lockdown",
        "start": date(2023, 4, 1),
        "end": date(2023, 5, 31),
        "type": "SUPPLIER_DELAY",
        "affected_suppliers": ["SUP-01", "SUP-07"],
        "lead_time_multiplier": 3.5,
        "demand_multiplier": 0.85,
    },
    {
        "name": "European Energy Crisis",
        "start": date(2024, 1, 1),
        "end": date(2024, 3, 31),
        "type": "COST_SPIKE",
        "affected_suppliers": ["SUP-02", "SUP-06"],
        "lead_time_multiplier": 1.4,
        "demand_multiplier": 0.9,
    },
    {
        "name": "Port Strike Rotterdam",
        "start": date(2024, 7, 10),
        "end": date(2024, 7, 25),
        "type": "PORT_CLOSURE",
        "affected_suppliers": ["SUP-02", "SUP-06", "SUP-08"],
        "lead_time_multiplier": 4.0,
        "demand_multiplier": 0.6,
    },
    {
        "name": "Semiconductor Shortage Q4",
        "start": date(2024, 10, 1),
        "end": date(2024, 12, 31),
        "type": "SUPPLIER_BANKRUPTCY",
        "affected_suppliers": ["SUP-04"],
        "lead_time_multiplier": 2.0,
        "demand_multiplier": 1.2,
    },
]


def _is_disrupted(
    row_date: date,
    supplier_id: str,
) -> tuple[float, float, str | None]:
    """Return (lead_time_mult, demand_mult, disruption_name) for a given row."""
    for d in DISRUPTIONS:
        if d["start"] <= row_date <= d["end"] and supplier_id in d["affected_suppliers"]:
            return d["lead_time_multiplier"], d["demand_multiplier"], d["name"]
    return 1.0, 1.0, None


def _holiday_multiplier(row_date: date) -> float:
    """Spike demand around Christmas, Chinese New Year, Q-end."""
    # Chinese New Year (approx Feb 1–15)
    if row_date.month == 2 and row_date.day <= 15:
        return 0.75  # demand dips during CNY
    # Christmas / holiday buying surge (Nov 15 – Dec 24)
    if (row_date.month == 11 and row_date.day >= 15) or (
        row_date.month == 12 and row_date.day <= 24
    ):
        return 1.35
    # Q-end purchasing surge (last 5 days of each quarter)
    if row_date.month in (3, 6, 9, 12) and row_date.day >= 26:
        return 1.25
    return 1.0


def generate_rows(start: date, end: date) -> list[dict[str, Any]]:
    """Generate all supply chain rows for the date range."""
    rows: list[dict[str, Any]] = []
    current = start
    supplier_pool = SUPPLIER_IDS.copy()

    while current <= end:
        dow = current.isoweekday()  # 1=Mon … 7=Sun
        weekly_factor = 1.0 if dow <= 5 else 0.3  # weekends suppress

        holiday_factor = _holiday_multiplier(current)

        for sku in SKU_IDS:
            meta = SKU_META[sku]
            # Assign primary supplier deterministically
            sup_idx = SKU_IDS.index(sku) % len(SUPPLIER_IDS)
            supplier_id = SUPPLIER_IDS[sup_idx]
            plant_id = PLANT_IDS[sup_idx % len(PLANT_IDS)]
            region_id = REGION_IDS[SKU_IDS.index(sku) % len(REGION_IDS)]
            carrier_id = CARRIER_IDS[sup_idx % len(CARRIER_IDS)]

            # Disruption modifiers
            lt_mult, dm_mult, dis_name = _is_disrupted(current, supplier_id)

            # Trend: slight upward trend over 3 years
            elapsed_days = (current - start).days
            trend = 1.0 + (elapsed_days / (3 * 365)) * 0.15

            # Demand
            noise = float(rng.normal(1.0, meta["volatility"]))
            demand = max(
                0,
                int(
                    meta["base_demand"]
                    * weekly_factor
                    * holiday_factor
                    * dm_mult
                    * trend
                    * noise
                ),
            )

            # Lead time
            base_lt = int(meta["lead_time_base"] * lt_mult)
            lead_time = max(1, int(rng.normal(base_lt, base_lt * 0.15)))

            # Unit cost with disruption / commodity noise
            cost_noise = float(rng.normal(1.0, 0.08))
            unit_cost = round(meta["unit_cost"] * (1.0 + 0.3 * (lt_mult - 1)) * cost_noise, 2)

            # Stock level (bounded random walk)
            stock_level = int(rng.integers(0, int(meta["base_demand"] * 3)))

            # CO2 affected by routing congestion during disruption
            co2 = round(meta["co2_per_unit"] * (1.0 + 0.4 * (lt_mult - 1)), 3)

            # On-time delivery: probability decreases with disruption
            otd_prob = max(0.2, 0.92 - 0.15 * (lt_mult - 1))
            on_time = bool(rng.random() < otd_prob)

            rows.append(
                {
                    "date": current,
                    "sku_id": sku,
                    "supplier_id": supplier_id,
                    "plant_id": plant_id,
                    "region_id": region_id,
                    "carrier_id": carrier_id,
                    "demand_units": demand,
                    "lead_time_days": lead_time,
                    "unit_cost": unit_cost,
                    "co2_kg_per_unit": co2,
                    "stock_level": stock_level,
                    "on_time_delivery": on_time,
                    "disruption_event": dis_name,
                    "day_of_week": dow,
                    "month": current.month,
                    "year": current.year,
                    "holiday_factor": holiday_factor,
                }
            )

        current += timedelta(days=1)

    return rows


async def save_to_db(engine, rows: list[dict]) -> None:
    """Bulk-insert rows using raw COPY for speed."""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    # Use synchronous psycopg2 for COPY
    import io
    from sqlalchemy import create_engine as sync_create_engine

    from backend.config import DATABASE_URL_SYNC

    sync_engine = sync_create_engine(DATABASE_URL_SYNC, echo=False)
    df.to_sql(
        "supply_chain_daily",
        sync_engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5000,
    )
    logger.info("Saved %d rows to supply_chain_daily.", len(df))
    sync_engine.dispose()


def generate_and_save_sync() -> pd.DataFrame:
    """Synchronous version for use in scripts / training."""
    start = date(2022, 1, 1)
    end = date(2024, 12, 31)
    logger.info("Generating synthetic dataset %s → %s …", start, end)
    rows = generate_rows(start, end)
    df = pd.DataFrame(rows)
    logger.info("Generated %d rows (%d SKUs × %d days).", len(df), NUM_SKUS, (end - start).days + 1)
    return df


NUM_SKUS = len(SKU_IDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = generate_and_save_sync()
    print(df.head())
    print(df.dtypes)
    print(f"Shape: {df.shape}")
    # Persist to parquet for ML training use
    df.to_parquet("data/synthetic_supply_chain.parquet", index=False)
    print("Saved to data/synthetic_supply_chain.parquet")
