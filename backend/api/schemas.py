"""
schemas.py — Pydantic models for all API request/response shapes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Forecast ─────────────────────────────────────────────────────────────────

class ForecastResponse(BaseModel):
    sku_id: str
    region_id: str
    model: str
    horizon: int
    dates: list[str]
    p10: list[float]
    p50: list[float]
    p90: list[float]
    safety_stock_units: float
    reorder_point: float
    history_points: int
    warning: Optional[str] = None
    computed_at: Optional[str] = None


# ─── Disruption ───────────────────────────────────────────────────────────────

class RiskDriver(BaseModel):
    source: str
    weight: float
    description: str


class SupplierRiskNode(BaseModel):
    id: str
    name: str
    risk_score: float
    risk_level: str  # LOW | MEDIUM | HIGH
    top_drivers: list[RiskDriver]
    monte_carlo_p90: float
    lat: float
    lon: float


class DisruptionResponse(BaseModel):
    nodes: list[SupplierRiskNode]
    network_risk_index: float
    news_articles: list[dict] = Field(default_factory=list)
    computed_at: str


# ─── Routing ──────────────────────────────────────────────────────────────────

class CargoItem(BaseModel):
    sku_id: str
    units: int


class RouteConstraints(BaseModel):
    max_cost: Optional[float] = None
    max_co2: Optional[float] = None
    max_days: Optional[float] = None


class RoutingRequest(BaseModel):
    origin_ids: list[str] = Field(default_factory=list)
    destination_ids: list[str] = Field(default_factory=list)
    cargo: list[CargoItem] = Field(default_factory=list)
    constraints: Optional[RouteConstraints] = None
    scenario: Optional[str] = None


class RouteArc(BaseModel):
    supplier_id: str
    plant_id: str
    mode: str
    distance_km: float
    cost_usd: float
    co2_kg: float
    lead_time_days: float
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    provider: Optional[str] = None


class RouteOptResponse(BaseModel):
    routes: list[RouteArc]
    total_cost: float
    total_co2: float
    max_eta_days: float
    active_route_count: int
    carrier_utilization: dict[str, float]
    pareto_frontier: list[dict]
    computed_at: str


# ─── Inventory ────────────────────────────────────────────────────────────────

class InventoryItem(BaseModel):
    sku_id: str
    current_stock: float
    effective_stock: float
    pending_orders: float
    recommended_order: float
    safety_stock: float
    reorder_point: float
    eoq: float
    days_of_supply: float
    risk_score: float
    risk_adjusted: bool
    policy: str
    action: str  # ORDER | HOLD


class InventoryResponse(BaseModel):
    items: list[InventoryItem]
    policy: str
    service_level: float
    computed_at: str


# ─── Scenario ─────────────────────────────────────────────────────────────────

class PlaybookStep(BaseModel):
    step: int
    action: str
    owner: str
    timeline: str
    expected_impact: str


class Playbook(BaseModel):
    scenario: str
    severity: str
    summary: str
    steps: list[PlaybookStep]
    kpi_recovery_estimate_days: int
    source: str  # claude | rule_based
    model: Optional[str] = None


class ScenarioRequest(BaseModel):
    scenario_name: str
    override_params: Optional[dict] = None


class ScenarioResponse(BaseModel):
    scenario_name: str
    description: str
    delta_kpis: dict[str, Any]
    playbook: Playbook
    affected_routes: list[RouteArc]
    blocked_ports: list[str]
    top_3_affected_skus: list[str]
    recommendation_summary: str
    computed_at: str


# ─── KPI Dashboard ────────────────────────────────────────────────────────────

class KPIMetric(BaseModel):
    chainmind: float
    baseline: float
    absolute_delta: float
    pct_improvement: float
    improved: bool


class KPIDashResponse(BaseModel):
    current: dict[str, Any]
    baseline: dict[str, Any]
    delta_pct: dict[str, KPIMetric]
    time_series: dict[str, list]
    period: str
    computed_at: str
    missing_features: list[str] = Field(default_factory=list)


# ─── WebSocket Events ─────────────────────────────────────────────────────────

class LiveEvent(BaseModel):
    type: str  # disruption_alert | kpi_update | route_change | inventory_alert
    payload: dict[str, Any]
    timestamp: str
    severity: Optional[str] = None  # HIGH | MEDIUM | LOW
