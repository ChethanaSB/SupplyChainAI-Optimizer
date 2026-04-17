"""
erp_mock.py — ERP mock stream using synthetic data.
Also defines the ERPAdapter abstract base class and concrete implementations:
  - SyntheticAdapter (for demo/development)
  - CSVAdapter (reads user-uploaded CSV)
  - SAP_REST_Adapter (skeleton for SAP OData integration)

Publishes inventory updates every ERP_POLL_INTERVAL_SEC to stream:erp.
"""
import asyncio
import csv
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np
import redis.asyncio as aioredis

from backend.config import REDIS_URL, ERP_POLL_INTERVAL_SEC, SKU_IDS, PLANT_IDS

logger = logging.getLogger("chainmind.erp")

rng = np.random.default_rng(2024)


# ─── Domain models ──────────────────────────────────────────────────────────

@dataclass
class StockRecord:
    sku_id: str
    plant_id: str
    current_stock: int
    pending_orders: int
    confirmed_receipts: int
    timestamp: str


@dataclass
class OrderRecord:
    order_id: str
    sku_id: str
    plant_id: str
    quantity: int
    expected_delivery: str
    status: str  # OPEN | CONFIRMED | DELAYED


@dataclass
class DemandRecord:
    date: str
    sku_id: str
    plant_id: str
    demand_units: int
    fulfilled_units: int


# ─── Abstract adapter ────────────────────────────────────────────────────────

class ERPAdapter(ABC):
    """Abstract interface for ERP data sources."""

    @abstractmethod
    def get_current_stock(self, sku_id: str) -> StockRecord:
        ...

    @abstractmethod
    def get_pending_orders(self, sku_id: str) -> list[OrderRecord]:
        ...

    @abstractmethod
    def get_historical_demand(self, sku_id: str, days: int) -> list[DemandRecord]:
        ...

    def iter_all_stocks(self) -> Iterator[StockRecord]:
        """Iterate over all SKU × Plant combinations."""
        for sku_id in SKU_IDS:
            for plant_id in PLANT_IDS:
                yield self.get_current_stock(sku_id)
                break  # One plant per SKU for stream efficiency


# ─── Synthetic adapter ────────────────────────────────────────────────────────

class SyntheticAdapter(ERPAdapter):
    """
    Synthetic ERP adapter — generates realistic but clearly labeled
    synthetic inventory data. Used when no real ERP is configured.
    All records include 'source': 'synthetic' to prevent confusion.
    """

    def get_current_stock(self, sku_id: str) -> StockRecord:
        base = int(rng.integers(50, 2000))
        return StockRecord(
            sku_id=sku_id,
            plant_id=rng.choice(PLANT_IDS),
            current_stock=base,
            pending_orders=int(rng.integers(0, 300)),
            confirmed_receipts=int(rng.integers(0, 200)),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_pending_orders(self, sku_id: str) -> list[OrderRecord]:
        from datetime import date, timedelta
        return [
            OrderRecord(
                order_id=f"ORD-{sku_id}-{i:03d}",
                sku_id=sku_id,
                plant_id=rng.choice(PLANT_IDS),
                quantity=int(rng.integers(10, 500)),
                expected_delivery=(date.today() + timedelta(days=int(rng.integers(1, 30)))).isoformat(),
                status=rng.choice(["OPEN", "CONFIRMED", "DELAYED"]),
            )
            for i in range(int(rng.integers(0, 5)))
        ]

    def get_historical_demand(self, sku_id: str, days: int) -> list[DemandRecord]:
        from datetime import date, timedelta
        records = []
        for i in range(days):
            d = date.today() - timedelta(days=days - i)
            demand = int(rng.integers(20, 400))
            fulfilled = min(demand, int(rng.integers(10, demand + 1)))
            records.append(
                DemandRecord(
                    date=d.isoformat(),
                    sku_id=sku_id,
                    plant_id=PLANT_IDS[0],
                    demand_units=demand,
                    fulfilled_units=fulfilled,
                )
            )
        return records


# ─── CSV adapter ──────────────────────────────────────────────────────────────

class CSVAdapter(ERPAdapter):
    """
    Reads inventory data from user-uploaded CSV.
    Required CSV columns: date, sku_id, plant_id, demand_units,
    fulfilled_units, current_stock, pending_orders, confirmed_receipts
    """

    def __init__(self, csv_path: str):
        self.path = Path(csv_path)
        if not self.path.exists():
            raise FileNotFoundError(f"ERP CSV not found: {csv_path}")
        self._data: list[dict] = []
        self._load()

    def _load(self) -> None:
        with open(self.path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self._data = list(reader)
        logger.info("CSVAdapter loaded %d rows from %s", len(self._data), self.path)

    def _rows_for_sku(self, sku_id: str) -> list[dict]:
        return [r for r in self._data if r.get("sku_id") == sku_id]

    def get_current_stock(self, sku_id: str) -> StockRecord:
        rows = self._rows_for_sku(sku_id)
        if not rows:
            return StockRecord(sku_id=sku_id, plant_id="UNKNOWN", current_stock=0,
                               pending_orders=0, confirmed_receipts=0,
                               timestamp=datetime.now(timezone.utc).isoformat())
        latest = max(rows, key=lambda r: r.get("date", ""))
        return StockRecord(
            sku_id=sku_id,
            plant_id=latest.get("plant_id", "PLT-01"),
            current_stock=int(latest.get("current_stock", 0)),
            pending_orders=int(latest.get("pending_orders", 0)),
            confirmed_receipts=int(latest.get("confirmed_receipts", 0)),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_pending_orders(self, sku_id: str) -> list[OrderRecord]:
        return []  # Not supported by basic CSV format

    def get_historical_demand(self, sku_id: str, days: int) -> list[DemandRecord]:
        rows = self._rows_for_sku(sku_id)
        rows = sorted(rows, key=lambda r: r.get("date", ""), reverse=True)[:days]
        return [
            DemandRecord(
                date=r.get("date", ""),
                sku_id=sku_id,
                plant_id=r.get("plant_id", "PLT-01"),
                demand_units=int(r.get("demand_units", 0)),
                fulfilled_units=int(r.get("fulfilled_units", 0)),
            )
            for r in rows
        ]


# ─── SAP REST adapter skeleton ───────────────────────────────────────────────

class SAP_REST_Adapter(ERPAdapter):
    """
    Skeleton for SAP OData API integration.
    Configure: SAP_BASE_URL, SAP_CLIENT_ID, SAP_CLIENT_SECRET in .env
    """

    def __init__(self):
        self.base_url = os.getenv("SAP_BASE_URL")
        self.client_id = os.getenv("SAP_CLIENT_ID")
        self.client_secret = os.getenv("SAP_CLIENT_SECRET")
        if not self.base_url:
            raise ValueError("SAP_BASE_URL not configured in environment.")

    def _get_token(self) -> str:
        import requests
        resp = requests.post(
            f"{self.base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def get_current_stock(self, sku_id: str) -> StockRecord:
        raise NotImplementedError("SAP_REST_Adapter.get_current_stock not yet implemented. "
                                  "Implement against your SAP MM OData API.")

    def get_pending_orders(self, sku_id: str) -> list[OrderRecord]:
        raise NotImplementedError("SAP_REST_Adapter.get_pending_orders not yet implemented.")

    def get_historical_demand(self, sku_id: str, days: int) -> list[DemandRecord]:
        raise NotImplementedError("SAP_REST_Adapter.get_historical_demand not yet implemented.")


# ─── Active adapter selection ────────────────────────────────────────────────

def get_adapter() -> ERPAdapter:
    """
    Returns the appropriate ERP adapter based on configuration.
    Priority: SAP → CSV → Synthetic (with warning)
    """
    if os.getenv("SAP_BASE_URL"):
        logger.info("Using SAP_REST_Adapter.")
        return SAP_REST_Adapter()

    csv_path = os.getenv("ERP_CSV_PATH", "")
    if csv_path and Path(csv_path).exists():
        logger.info("Using CSVAdapter from %s.", csv_path)
        return CSVAdapter(csv_path)

    logger.warning(
        "No ERP adapter configured. Using SyntheticAdapter. "
        "Set ERP_CSV_PATH or SAP_BASE_URL in .env for real data."
    )
    return SyntheticAdapter()


# ─── Stream publisher ─────────────────────────────────────────────────────────

async def run_erp_streamer() -> None:
    """Publish ERP inventory updates every ERP_POLL_INTERVAL_SEC to stream:erp."""
    logger.info("Starting ERP streamer (interval: %ds).", ERP_POLL_INTERVAL_SEC)
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    adapter = get_adapter()

    while True:
        try:
            for stock in adapter.iter_all_stocks():
                record = {
                    "sku_id": stock.sku_id,
                    "plant_id": stock.plant_id,
                    "current_stock": stock.current_stock,
                    "pending_orders": stock.pending_orders,
                    "confirmed_receipts": stock.confirmed_receipts,
                    "timestamp": stock.timestamp,
                    "source": adapter.__class__.__name__,
                }
                await redis.xadd("stream:erp", {"data": json.dumps(record)}, maxlen=2000)
        except Exception as exc:
            logger.error("ERP streamer error: %s", exc)

        await asyncio.sleep(ERP_POLL_INTERVAL_SEC)
