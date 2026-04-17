/**
 * api.ts — API client for ChainMind Frontend.
 */
import { KPIDashboardData, Disruption } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getKPIDashboard(period: string = "30d"): Promise<KPIDashboardData> {
  const resp = await fetch(`${API_BASE}/api/kpi/dashboard?period=${period}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch KPI dashboard: ${resp.statusText}`);
  }
  return resp.json();
}

export async function getDisruptions(): Promise<Disruption[]> {
  const resp = await fetch(`${API_BASE}/api/disruption/active`);
  if (!resp.ok) {
    return [];
  }
  return resp.json();
}

export async function triggerScenario(type: string, location: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/scenario/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, location, severity: "High" }),
  });
  return resp.json();
}
