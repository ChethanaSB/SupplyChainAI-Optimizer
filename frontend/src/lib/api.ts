import { KPIDashboardData, Disruption, ValidationReportData } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getKPIDashboard(period: string = "30d"): Promise<KPIDashboardData> {
  const resp = await fetch(`${API_BASE}/api/kpi/dashboard?period=${period}`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch KPI dashboard: ${resp.statusText}`);
  }
  return resp.json();
}

export async function getValidationReport(): Promise<ValidationReportData> {
  const resp = await fetch(`${API_BASE}/api/kpi/validation`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch validation report: ${resp.statusText}`);
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

export async function getDisruptionRisk(supplierIds: string = "all"): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/disruption/risk?supplier_ids=${supplierIds}`);
    if (!resp.ok) throw new Error("Failed to fetch risk data");
    return resp.json();
}

export async function getForecast(skuId: string, horizon: number = 30): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/forecast/${skuId}?horizon=${horizon}`);
    if (!resp.ok) throw new Error("Failed to fetch forecast");
    return resp.json();
}

export async function optimizeRouting(request: any): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/routing/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
    });
    if (!resp.ok) throw new Error("Failed to optimize routing");
    return resp.json();
}

export async function runScenario(scenarioName: string, overrideParams: any = {}): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/scenario/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario_name: scenarioName, override_params: overrideParams }),
    });
    if (!resp.ok) throw new Error("Failed to run scenario");
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

export async function getLiveVessels(): Promise<any[]> {
    const resp = await fetch(`${API_BASE}/api/routing/vessels`);
    if (!resp.ok) return [];
    return resp.json();
}

export async function getIntelFeed(): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/intel/feed`);
    if (!resp.ok) throw new Error("Failed to fetch intel feed");
    return resp.json();
}

export async function globalSearch(query: string): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/intel/search?q=${encodeURIComponent(query)}`);
    if (!resp.ok) throw new Error("Search failed");
    return resp.json();
}

export async function executePlan(plan: any): Promise<any> {
    const resp = await fetch(`${API_BASE}/api/routing/execute-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan),
    });
    if (!resp.ok) throw new Error("Execution failed");
    return resp.json();
}
