"""
seeding.py — Seed Supabase with historical supply chain data.
Fills the dashboard with 30 days of synthetic history.
"""
import asyncio
import random
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from backend.db.database import AsyncSessionLocal, init_db
from backend.db.schema import Inventory, Shipment, Disruption, WeatherCache, MarketPrice, KPIHistory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chainmind.seeding")

PLANTS = ["DE-STU", "CN-SHA", "US-DET", "IN-PUN", "BR-CUR"]
PARTS = ["GEARBOX-X1", "SENSOR-A2", "MOTOR-Z", "CHASSIS-H", "BATTERY-V2"]


async def seed_historical_data(days=30):
    """Seed 30 days of supply chain history."""
    logger.info("Starting historical seed for %d days...", days)
    
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # 1. Seed Inventory History
            for i in range(days):
                date = datetime.now(timezone.utc) - timedelta(days=i)
                for plant in PLANTS:
                    for part in PARTS:
                        inv = Inventory(
                            item_id=part,
                            site_id=plant,
                            stock_level=random.uniform(500, 2000),
                            safety_stock=500,
                            demand_forecast=random.uniform(100, 300),
                            updated_at=date
                        )
                        session.add(inv)

            # 2. Seed Shipments (Active and Arrived)
            for i in range(20):
                shipment = Shipment(
                    id=f"SHP-{1000+i}",
                    origin=random.choice(PLANTS),
                    destination=random.choice(PLANTS),
                    status=random.choice(["Transit", "Arrived", "Delayed"]),
                    lat=random.uniform(-90, 90),
                    lon=random.uniform(-180, 180),
                    co2_impact=random.uniform(10, 100),
                    eta=datetime.now(timezone.utc) + timedelta(days=random.randint(1, 10))
                )
                session.add(shipment)

            # 3. Seed Disruptions
            disruption_types = ["Port Closure", "Labor Strike", "Cyber Attack", "Extreme Storm"]
            for i in range(5):
                dis = Disruption(
                    type=random.choice(disruption_types),
                    location=random.choice(PLANTS),
                    severity=random.choice(["High", "Medium"]),
                    description="Simulated historical disruption event.",
                    impact_score=random.uniform(40, 90),
                    timestamp=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30)),
                    resolved=random.choice([True, False])
                )
                session.add(dis)

            # 4. Seed KPIs
            metrics = ["fulfillment_rate", "cost_efficiency", "carbon_footprint"]
            for i in range(days):
                date = datetime.now(timezone.utc) - timedelta(days=i)
                for metric in metrics:
                    kpi = KPIHistory(
                        metric=metric,
                        value=random.uniform(85, 98),
                        baseline=90.0,
                        timestamp=date
                    )
                    session.add(kpi)

        await session.commit()
    logger.info("Seeding complete.")


if __name__ == "__main__":
    async def run():
        await init_db()
        await seed_historical_data()
    asyncio.run(run())
