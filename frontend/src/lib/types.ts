/**
 * types.ts — Frontend type definitions for ChainMind.
 */

export interface KPIMetric {
  chainmind: number;
  baseline: number;
  absolute_delta: number;
  pct_improvement: number;
  improved: boolean;
}

export interface KPIDashboardData {
  current: {
    service_level_pct: number;
    total_logistics_cost: number;
    co2_emissions_kg: number;
    avg_lead_time_days: number;
    inventory_turns: number;
    active_route_count?: number;
    suppliers_synced?: number;
    risk_exposure_index?: number;
  };
  baseline: {
    service_level_pct: number;
    total_logistics_cost: number;
    co2_emissions_kg: number;
    avg_lead_time_days: number;
    inventory_turns: number;
  };
  delta_pct: {
    [key: string]: KPIMetric;
  };
  time_series: {
    [key: string]: number[];
  };
  market_prices: Array<{
    symbol: string;
    price: number;
    change_pct: number;
    timestamp: string;
  }>;
  period: string;
  computed_at: string;
  missing_features: string[];
}

export interface Disruption {
  id: number;
  type: string;
  location: string;
  severity: "High" | "Medium" | "Low";
  description: string;
  impact_score: number;
  timestamp: string;
}

export interface RouteArc {
  supplier_id: string;
  plant_id: string;
  mode: string;
  distance_km: number;
  cost_inr: number;
  co2_kg: number;
  lead_time_days: number;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  provider?: string;
}

export interface RoutingData {
  routes: RouteArc[];
  total_cost: number;
  total_co2: number;
  max_eta_days: number;
  active_route_count: number;
  carrier_utilization: Record<string, number>;
  computed_at: string;
}

/* ── Forecast ────────────────────────────────────────────────── */
export interface ForecastData {
  sku_id: string;
  region_id: string;
  model: string;
  horizon: number;
  dates: string[];
  p10: number[];
  p50: number[];
  p90: number[];
  safety_stock_units: number;
  reorder_point: number;
  history_points: number;
  warning?: string;
  computed_at?: string;
}

/* ── Disruption Radar ────────────────────────────────────────── */
export interface RiskDriver {
  source: string;
  weight: number;
  description: string;
}

export interface SupplierRiskNode {
  id: string;
  name: string;
  risk_score: number;
  risk_level: string;
  top_drivers: RiskDriver[];
  monte_carlo_p90: number;
  lat: number;
  lon: number;
}

export interface NewsArticle {
  title: string;
  source: string;
  severity: number;
  sentiment_label: string;
  entities: string[];
  published_at: string;
  url: string;
}

export interface DisruptionData {
  nodes: SupplierRiskNode[];
  network_risk_index: number;
  news_articles: NewsArticle[];
  computed_at: string;
}

/* ── Live Feed ───────────────────────────────────────────────── */
export interface LiveEvent {
  type: string;
  payload: Record<string, any>;
  timestamp: string;
  severity?: string;
}

/* ── Scenario Simulator ──────────────────────────────────────── */
export interface PlaybookStep {
  step: number;
  action: string;
  owner: string;
  timeline: string;
  expected_impact: string;
}

export interface Playbook {
  scenario: string;
  severity: string;
  summary: string;
  steps: PlaybookStep[];
  kpi_recovery_estimate_days: number;
  source: string;
  model?: string;
}

export interface ScenarioData {
  scenario_name: string;
  description: string;
  delta_kpis: Record<string, any>;
  playbook: Playbook;
  affected_routes: RouteArc[];
  blocked_ports: string[];
  top_3_affected_skus: string[];
  recommendation_summary: string;
  computed_at: string;
}

/* ── Validation Report ───────────────────────────────────────── */
export interface ValidationReportData {
  summary: string;
  metrics: Record<string, KPIMetric>;
  scenarios_tested: number;
  baseline_policy: string;
  optimization_method: string;
  recommendation: string;
  computed_at: string;
}

/* ── Intelligence Feed ────────────────────────────────────────── */
export interface IntelItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  timestamp: string;
  category: string;
  sentiment: string;
  relevance_score: number;
}

export interface IntelFeedData {
  articles: IntelItem[];
  computed_at: string;
}
