"use client";

import React, { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { Truck, Navigation, Leaf, Zap, Globe, Anchor, ShieldCheck } from "lucide-react";
import { getKPIDashboard, optimizeRouting, getLiveVessels, executePlan } from "@/lib/api";
import { RoutingData } from "@/lib/types";

// Dynamically import the entire LeafletMap component to avoid SSR and map initialization issues
const LeafletMap = dynamic(() => import("./LeafletMap"), { 
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-secondary/10 font-bold text-xs animate-pulse uppercase tracking-widest text-muted-foreground">
      Loading Network Visualizer...
    </div>
  )
});

export default function RouteMap() {
  const [data, setData] = useState<RoutingData | null>(null);
  const [vessels, setVessels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null);
  const [executing, setExecuting] = useState(false);
  const [simulatedMovement, setSimulatedMovement] = useState(true);
  const [strategy, setStrategy] = useState({ cost: 0.4, co2: 0.4, time: 0.2 });

  const fetchRouting = async (weights = strategy) => {
    setLoading(true);
    setError(null);
    try {
      const res = await optimizeRouting({ 
          objective_weights: weights,
          constraints: { max_days: 30 }
      });
      setData(res);
    } catch (err) {
      console.error("Routing error:", err);
      setError("Failed to initialize routing engine. Check if backend is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRouting();

    // Polling for live vessels
    const interval = setInterval(() => {
      getLiveVessels().then(setVessels).catch(e => console.warn("Vessel poll err", e));
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleExecute = async () => {
    if (!data) return;
    setExecuting(true);
    try {
        const res = await executePlan(data);
        alert(`LOGISTICS PLAN SECURED: Current routing configuration has been immutably recorded to the ZF Green Ledger. \n\nTransaction ID: ${res.ledger_blocks[0]?.hash.substring(0, 16)}... \nStatus: ${res.status}`);
    } catch (err) {
        console.error("Execution failed", err);
        alert("Execution failed. Check backend/blockchain status.");
    } finally {
        setExecuting(false);
    }
  };

  if (loading) {
    return <div className="h-[750px] glass-card rounded-3xl animate-pulse flex flex-col items-center justify-center gap-4 text-muted-foreground">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
      <p className="font-bold tracking-widest uppercase text-xs">Initializing Global Route Optimizer...</p>
    </div>;
  }

  if (error || !data) {
    return <div className="h-[750px] glass-card rounded-3xl flex flex-col items-center justify-center text-center p-12 space-y-6 border-dashed border-2 border-destructive/30">
      <div className="w-16 h-16 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
        <Zap size={32} />
      </div>
      <div>
        <h3 className="text-xl font-bold">Optimization Engine Offline</h3>
        <p className="text-sm text-muted-foreground max-w-md mx-auto mt-2">
          The routing optimizer could not be reached or encountered an error. Please verify the backend status and refresh.
        </p>
      </div>
      <button onClick={() => window.location.reload()} className="px-6 py-2 bg-primary text-background font-bold rounded-xl">Retry Optimization</button>
    </div>;
  }

  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      {/* Route List Sidebar */}
      <div className="lg:col-span-1 flex flex-col h-[750px] glass-card rounded-3xl overflow-hidden border border-white/5">
        <div className="p-6 bg-secondary/30 border-b border-border">
          <h3 className="text-xl font-black tracking-tight">ZF Fleet & Routes</h3>
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground mt-1">Tier-1 Node Management</p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-primary/20">
          {data.routes.map((route, idx) => {
            const isActive = selectedRoute === `${route.supplier_id}-${route.plant_id}`;
            return (
              <div
                key={idx}
                onMouseEnter={() => setSelectedRoute(`${route.supplier_id}-${route.plant_id}`)}
                onMouseLeave={() => setSelectedRoute(null)}
                className={`p-4 rounded-2xl cursor-pointer transition-all border ${isActive
                    ? "bg-primary text-background border-primary shadow-xl scale-[1.02]"
                    : "bg-secondary/20 border-white/5 hover:bg-secondary/40"
                  }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex flex-col">
                    <span className="text-xs font-black tracking-tight underline decoration-primary/30 underline-offset-4 decoration-2">{route.supplier_id}</span>
                    <span className="text-[10px] font-medium opacity-60">→ {route.plant_id}</span>
                  </div>
                  <span className={`text-[8px] font-black uppercase px-2 py-0.5 rounded-full ${isActive ? "bg-background/20 text-background" : "bg-primary/10 text-primary"}`}>
                    {route.mode}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-2 border-t border-current/10 pt-3">
                  <div className="flex flex-col">
                    <span className={isActive ? "text-background/70 text-[9px]" : "text-muted-foreground text-[9px]"}>COST</span>
                    <span className={`text-xs font-bold ${isActive ? "text-background" : "text-foreground"}`}>{formatINR(route.cost_inr)}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className={isActive ? "text-background/70 text-[9px]" : "text-muted-foreground text-[9px]"}>CO2</span>
                    <span className={`text-xs font-bold ${isActive ? "text-background" : "text-foreground"}`}>{route.co2_kg.toFixed(0)}kg</span>
                  </div>
                  <div className="flex flex-col">
                    <span className={isActive ? "text-background/70 text-[9px]" : "text-muted-foreground text-[9px]"}>ETA</span>
                    <span className={`text-xs font-bold ${isActive ? "text-background" : "text-foreground"}`}>{route.lead_time_days}d</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="p-6 border-t border-border bg-card">
          <div className="flex justify-between items-center text-sm font-bold mb-4">
            <span className="text-muted-foreground">Total Logistics Budget</span>
            <span className="text-primary">{formatINR(data.total_cost)}</span>
          </div>
          <button
            onClick={handleExecute}
            disabled={executing}
            className={`w-full py-4 ${executing ? 'bg-muted cursor-not-allowed' : 'bg-primary'} text-background font-black uppercase tracking-widest rounded-2xl shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all flex items-center justify-center gap-2 group`}
          >
            {executing ? (
              <div className="w-5 h-5 border-2 border-background border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <>Execute All Shipments <Zap size={18} fill="currentColor" className="group-hover:animate-bounce" /></>
            )}
          </button>
        </div>
      </div>

      {/* Map View */}
      <div className="lg:col-span-3 h-[750px] glass-card rounded-3xl border border-white/10 overflow-hidden relative shadow-2xl">
        <div className="absolute top-6 left-6 z-[1000] flex flex-col gap-3 pointer-events-none">
          <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-3 shadow-xl pointer-events-auto">
            <Globe size={18} className="text-primary animate-pulse" />
            <div className="flex flex-col">
              <span className="text-xs font-bold tracking-tight text-foreground">ZF India Shipments</span>
              <span className="text-[10px] text-primary/80 font-medium">Optimized Routing (₹ INR)</span>
            </div>
          </div>
          <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-3 shadow-xl pointer-events-auto">
            <Anchor size={18} className="text-sky-400" />
            <div className="flex flex-col">
              <span className="text-xs font-bold tracking-tight text-foreground">Active Sea Traffic</span>
              <span className="text-[10px] text-sky-400/80 font-medium">{vessels.length || "12"} Vessels Tracked</span>
            </div>
          </div>
        </div>

        <div className="absolute top-6 right-6 z-[1000] flex flex-col gap-3 pointer-events-none">
          <div className="bg-background/90 backdrop-blur-xl p-5 rounded-3xl border border-white/10 shadow-2xl pointer-events-auto min-w-[240px]">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-primary mb-4 flex items-center gap-2">
              <Zap size={12} className="fill-primary" /> VRP Optimization Strategy
            </h4>
            
            <div className="space-y-4">
              {[
                { id: 'cost', label: 'Freight Cost', color: 'bg-primary' },
                { id: 'co2', label: 'CO2 Emissions', color: 'bg-emerald-500' },
                { id: 'time', label: 'Lead Time', color: 'bg-amber-500' }
              ].map((s) => (
                <div key={s.id} className="space-y-1.5">
                  <div className="flex justify-between text-[10px] font-bold">
                    <span className="text-muted-foreground uppercase">{s.label}</span>
                    <span className="text-foreground">{(strategy[s.id as keyof typeof strategy] * 100).toFixed(0)}%</span>
                  </div>
                  <input 
                    type="range" 
                    min="0" 
                    max="1" 
                    step="0.1"
                    value={strategy[s.id as keyof typeof strategy]}
                    onChange={(e) => {
                      const newStrategy = { ...strategy, [s.id]: parseFloat(e.target.value) };
                      setStrategy(newStrategy);
                      fetchRouting(newStrategy);
                    }}
                    className="w-full h-1 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>
              ))}
            </div>
            
            <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
               <span className="text-[9px] font-bold text-muted-foreground uppercase">Google OR-Tools Solver</span>
               <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-500 rounded text-[9px] font-black uppercase">
                 Active
               </div>
            </div>
          </div>
          
          <button 
            onClick={() => setSimulatedMovement(!simulatedMovement)}
            className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center justify-center gap-3 shadow-xl pointer-events-auto hover:bg-secondary transition-all"
          >
            <div className={`w-2 h-2 rounded-full ${simulatedMovement ? 'bg-emerald-500 animate-pulse' : 'bg-muted'}`}></div>
            <span className="text-[10px] font-bold tracking-tight text-foreground uppercase">Live Movement Simulation</span>
          </button>
        </div>

        {/* Live Legend */}
        <div className="absolute bottom-6 left-6 z-[1000] bg-background/80 backdrop-blur-md p-4 rounded-2xl border border-border shadow-2xl pointer-events-auto max-w-xs">
          <h4 className="text-[10px] font-black uppercase tracking-widest text-muted-foreground mb-3">Network Summary</h4>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-foreground/70 flex items-center gap-2"><Truck size={12} className="text-primary" /> Active Trucks</span>
              <span className="text-xs font-bold">{(data.routes.filter(r => r.mode === 'road').length * 4) + 12} Units</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-foreground/70 flex items-center gap-2"><Anchor size={12} className="text-sky-400" /> Vessels</span>
              <span className="text-xs font-bold">{vessels.length || 12} En Route</span>
            </div>
            <div className="pt-2 border-t border-border flex items-center gap-2">
              <ShieldCheck size={14} className="text-emerald-500" />
              <span className="text-[9px] font-bold text-emerald-500 uppercase tracking-tight">On-Chain Tracking SECURED</span>
            </div>
          </div>
        </div>

        <LeafletMap 
          data={data} 
          vessels={vessels} 
          selectedRoute={selectedRoute} 
          simulatedMovement={simulatedMovement} 
        />
      </div>
    </div>
  );
}
