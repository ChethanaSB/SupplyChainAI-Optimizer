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
  cost_usd: number;
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
