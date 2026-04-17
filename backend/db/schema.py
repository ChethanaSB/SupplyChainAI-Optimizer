"""
schema.py — SQLAlchemy ORM models for ChainMind.
Defines the persistent data structure for inventory, shipments, and risks.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True)
    item_id = Column(String, index=True)
    site_id = Column(String, index=True)
    stock_level = Column(Float)
    safety_stock = Column(Float)
    demand_forecast = Column(Float)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(String, primary_key=True)
    origin = Column(String)
    destination = Column(String)
    status = Column(String, index=True)  # Transit, Delayed, Arrived
    lat = Column(Float)
    lon = Column(Float)
    co2_impact = Column(Float)
    eta = Column(DateTime)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Disruption(Base):
    __tablename__ = "disruptions"

    id = Column(Integer, primary_key=True)
    type = Column(String, index=True)  # Port, Storm, Strike
    location = Column(String)
    severity = Column(String)  # High, Med, Low
    description = Column(String)
    impact_score = Column(Float)
    resolved = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class WeatherCache(Base):
    __tablename__ = "weather_history"

    id = Column(Integer, primary_key=True)
    location_id = Column(String, index=True)
    data = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True)
    price = Column(Float)
    change_pct = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class KPIHistory(Base):
    __tablename__ = "kpi_history"

    id = Column(Integer, primary_key=True)
    metric = Column(String, index=True)  # fulfillment, cost, co2
    value = Column(Float)
    baseline = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
