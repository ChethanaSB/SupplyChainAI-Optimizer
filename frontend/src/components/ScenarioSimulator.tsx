"use client";

import React, { useState } from "react";
import { 
  Zap, 
  AlertCircle, 
  Play, 
  CheckCircle2, 
  Clock, 
  User, 
  TrendingUp, 
  ShieldAlert,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { runScenario } from "@/lib/api";
import { ScenarioData, PlaybookStep } from "@/lib/types";

const SCENARIO_TYPES = [
  { id: "PORT_CLOSURE", name: "Port Closure", desc: "Block top-2 congested ports for 14 days", icon: ShieldAlert, color: "text-red-400" },
  { id: "SUPPLIER_DELAY", name: "Supplier Delay", desc: "Highest-risk supplier lead time x 2.5", icon: Clock, color: "text-amber-400" },
  { id: "CARRIER_CRUNCH", name: "Carrier Crunch", desc: "Capacity reduced by 40% on all lanes", icon: AlertCircle, color: "text-orange-400" },
  { id: "DEMAND_SPIKE", name: "Demand Spike", desc: "Demand x 1.8 for top 10 SKUs", icon: TrendingUp, color: "text-blue-400" },
  { id: "COMBINED", name: "Crisis (Combined)", desc: "Port closure + Supplier delay concurrently", icon: Zap, color: "text-destructive" },
];

export default function ScenarioSimulator() {
  const [selectedId, setSelectedId] = useState("PORT_CLOSURE");
  const [result, setResult] = useState<ScenarioData | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const res = await runScenario(selectedId);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      {/* Selector */}
      <div className="xl:col-span-1 space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Resilience Testing</h2>
          <p className="text-muted-foreground text-sm">Stress-test your network against systemic disruptions.</p>
        </div>

        <div className="space-y-3">
          {SCENARIO_TYPES.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedId(s.id)}
              className={`w-full p-4 rounded-2xl border transition-all text-left flex items-start gap-4 ${
                selectedId === s.id 
                  ? "bg-primary/5 border-primary shadow-lg shadow-primary/5" 
                  : "bg-card/50 border-border hover:border-primary/30"
              }`}
            >
              <div className={`mt-1 p-2 rounded-lg bg-secondary ${s.color}`}>
                <s.icon size={20} />
              </div>
              <div className="flex-1">
                <p className={`font-bold text-sm ${selectedId === s.id ? "text-primary" : "text-foreground"}`}>{s.name}</p>
                <p className="text-xs text-muted-foreground leading-relaxed mt-1">{s.desc}</p>
              </div>
              {selectedId === s.id && <div className="mt-1"><ChevronRight size={18} className="text-primary" /></div>}
            </button>
          ))}
        </div>

        <button 
          onClick={handleSimulate}
          disabled={loading}
          className="w-full py-4 bg-primary text-background font-bold rounded-2xl shadow-xl shadow-primary/20 hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-3 disabled:opacity-50"
        >
          {loading ? (
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-background border-t-transparent" />
          ) : (
            <>Execute Simulation <Play size={18} fill="currentColor" /></>
          )}
        </button>
      </div>

      {/* Results / Playbook */}
      <div className="xl:col-span-2 min-h-[600px]">
        {result ? (
          <div className="glass-card rounded-2xl overflow-hidden flex flex-col h-full animate-in fade-in zoom-in-95 duration-500">
            {/* Playbook Header */}
            <div className="p-8 border-b border-border bg-gradient-to-r from-secondary/30 to-background/50 relative overflow-hidden">
               <div className="flex justify-between items-start z-10 relative">
                 <div className="space-y-1">
                   <div className="flex items-center gap-2">
                     <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-widest ${
                       result.playbook.severity === "HIGH" ? "bg-status-red/10 text-status-red" : "bg-status-amber/10 text-status-amber"
                     }`}>
                       {result.playbook.severity} SEVERITY
                     </div>
                     <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase">
                       <Sparkles size={12} /> {result.playbook.source.toUpperCase()} AI
                     </div>
                   </div>
                   <h3 className="text-2xl font-extrabold tracking-tight">{result.playbook.scenario.replace('_', ' ')} RECOVERY PLAN</h3>
                 </div>
                 <div className="text-right">
                   <p className="text-xs text-muted-foreground font-medium uppercase">Recovery Estimate</p>
                   <p className="text-2xl font-black text-primary">{result.playbook.kpi_recovery_estimate_days} Days</p>
                 </div>
               </div>
               
               <p className="mt-6 text-sm text-foreground/80 leading-relaxed max-w-2xl px-4 py-3 bg-background/40 border-l-2 border-primary rounded-r-lg italic">
                 {result.playbook.summary}
               </p>
               
               {/* Decorative background Icon */}
               <Zap className="absolute -bottom-10 -right-10 w-48 h-48 text-primary/5 -rotate-12 pointer-events-none" />
            </div>

            <div className="p-8 space-y-8 flex-1">
              <div className="grid grid-cols-3 gap-6">
                <div className="p-4 bg-secondary/20 rounded-xl border border-border">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase mb-1">Cost Impact</p>
                  <p className={`text-lg font-bold ${result.delta_kpis.total_cost_pct_change > 0 ? "text-status-red" : "text-status-green"}`}>
                    {result.delta_kpis.total_cost_pct_change > 0 ? "+" : ""}{result.delta_kpis.total_cost_pct_change}%
                  </p>
                </div>
                <div className="p-4 bg-secondary/20 rounded-xl border border-border">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase mb-1">Svc Level Delta</p>
                  <p className="text-lg font-bold text-status-red">
                    {result.delta_kpis.service_level_pct_change}%
                  </p>
                </div>
                <div className="p-4 bg-secondary/20 rounded-xl border border-border">
                  <p className="text-[10px] text-muted-foreground font-bold uppercase mb-1">Stockout Risk</p>
                  <p className="text-lg font-bold text-status-amber">
                    +{result.delta_kpis.stockout_risk_increase_pct}%
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="text-sm font-bold flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-primary" /> Recommended Playbook Steps
                </h4>
                <div className="space-y-3">
                  {result.playbook.steps.map((step) => (
                    <div key={step.step} className="group flex items-start gap-4 p-4 bg-card hover:bg-secondary/30 border border-border rounded-xl transition-all">
                      <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center font-black text-xs text-muted-foreground group-hover:text-primary transition-colors">
                        0{step.step}
                      </div>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-bold">{step.action}</p>
                        <div className="flex gap-4">
                          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-medium uppercase">
                            <User size={12} /> {step.owner}
                          </span>
                          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground font-medium uppercase">
                            <Clock size={12} /> {step.timeline}
                          </span>
                        </div>
                      </div>
                      <div className="text-right whitespace-nowrap">
                         <span className="text-[10px] font-bold text-status-green bg-status-green/5 px-2 py-1 rounded">
                           IMPACT: {step.expected_impact}
                         </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full glass-card rounded-2xl border-dashed border-2 flex flex-col items-center justify-center text-center p-12 space-y-6">
            <div className="w-20 h-20 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
               <Play size={32} className="ml-2" />
            </div>
            <div className="max-w-md space-y-2">
              <h3 className="text-xl font-bold tracking-tight">Ready for Simulation</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Select a disruption scenario from the left panel and execute to see AI-generated recovery playbooks and KPI impacts.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
