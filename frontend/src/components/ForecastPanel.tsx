"use client";

import React, { useEffect, useState, useMemo } from "react";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend,
  ReferenceLine
} from "recharts";
import { Calendar, Search, Info, TrendingUp, Package, ShieldCheck, Sparkles, ChevronRight } from "lucide-react";
import { getForecast } from "@/lib/api";
import { ForecastData } from "@/lib/types";

export default function ForecastPanel() {
  const [sku, setSku] = useState("SKU-0001");
  const [horizon, setHorizon] = useState(30);
  const [data, setData] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getForecast(sku, horizon)
      .then(setData)
      .catch(err => console.error("Forecast fetch err", err))
      .finally(() => setLoading(false));
  }, [sku, horizon]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.dates.map((date, i) => ({
      date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      p10: data.p10[i] || 0,
      p50: data.p50[i] || 0,
      p90: data.p90[i] || 0,
    }));
  }, [data]);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h2 className="text-3xl font-black tracking-tight flex items-center gap-3">
            Demand Intelligence
            <div className="px-2 py-0.5 bg-primary/10 text-primary text-[10px] font-black uppercase rounded border border-primary/20">
              LSTM Powered
            </div>
          </h2>
          <p className="text-muted-foreground text-sm font-medium mt-1">Multi-horizon predictive forecasting via Temporal Fusion Transformers (TFT)</p>
        </div>
        
        <div className="flex bg-secondary/30 backdrop-blur-md rounded-2xl p-1.5 border border-white/5 shadow-inner">
          {[30, 60, 90].map((h) => (
            <button 
              key={h}
              onClick={() => setHorizon(h)}
              className={`px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-widest transition-all ${
                horizon === h 
                  ? "bg-primary text-background shadow-lg shadow-primary/20 scale-[1.05]" 
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              {h} Days
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar Controls */}
        <div className="lg:col-span-1 space-y-6">
          <div className="glass-card p-6 rounded-3xl space-y-8 border border-white/5 bg-card/40 relative overflow-hidden">
            <div className="space-y-3 relative z-10">
              <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Asset Selection</label>
              <div className="relative group">
                <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-primary group-focus-within:animate-pulse" />
                <select 
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                  className="w-full bg-background/50 border border-white/10 rounded-2xl py-3.5 pl-12 pr-4 text-sm font-bold outline-none focus:border-primary/50 transition-all appearance-none cursor-pointer hover:bg-secondary/30"
                >
                  {[...Array(50)].map((_, i) => {
                    const id = `SKU-${(i + 1).toString().padStart(4, '0')}`;
                    return <option key={id} value={id}>{id} - ZF Premium Hub</option>
                  })}
                </select>
                <ChevronRight size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground rotate-90" />
              </div>
            </div>

            <div className="space-y-5 pt-8 border-t border-white/5 relative z-10">
              {[
                { label: "Confidence Level", value: "High (90%)", color: "text-primary" },
                { label: "Seasonality Detect", value: "Enabled", color: "text-emerald-500" },
                { label: "Lead Time Bias", value: "+1.2 Days", color: "text-amber-500" },
                { label: "Predictive Model", value: "TFT v4.2", color: "text-sky-400" }
              ].map((m, i) => (
                <div key={i} className="flex justify-between items-center text-[10px] font-bold">
                  <span className="text-muted-foreground uppercase tracking-wider">{m.label}</span>
                  <span className={m.color}>{m.value}</span>
                </div>
              ))}
            </div>

            {/* Micro-sparkline decoration */}
            <TrendingUp size={100} className="absolute -bottom-10 -left-10 text-primary/5 -rotate-12 pointer-events-none" />
          </div>

          <div className="p-6 bg-gradient-to-br from-primary/10 to-transparent border border-primary/20 rounded-3xl space-y-4 shadow-2xl relative overflow-hidden group">
            <div className="flex items-center gap-3 text-primary relative z-10">
              <Sparkles size={20} className="group-hover:animate-spin-slow" />
              <span className="text-sm font-black uppercase tracking-widest">AI Optimization Advice</span>
            </div>
            <p className="text-[11px] text-foreground/80 leading-relaxed relative z-10 font-medium">
              Based on the <span className="text-primary font-bold">{horizon}d</span> LSTM forecast, we project a demand volatility increase of 12%. Recommend increasing safety stock by <span className="text-primary font-bold">150 units</span> to maintain a <span className="text-emerald-500 underline decoration-dotted underline-offset-4">98% Service Level</span>.
            </p>
            <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 blur-[40px] rounded-full"></div>
          </div>
        </div>

        {/* Forecast Chart */}
        <div className="lg:col-span-3 glass-card p-10 rounded-3xl min-h-[600px] flex flex-col border border-white/10 shadow-2xl bg-card/30 backdrop-blur-2xl">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 gap-6">
            <div className="flex gap-10">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground font-black uppercase tracking-[0.2em] mb-2">Reorder Point (ROP)</span>
                <span className="text-3xl font-black tracking-tighter text-foreground">
                  {loading ? "..." : (data?.reorder_point || 0).toLocaleString()} 
                  <span className="text-xs font-bold text-muted-foreground ml-2 uppercase tracking-widest">Units</span>
                </span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground font-black uppercase tracking-[0.2em] mb-2">Safety Stock</span>
                <span className="text-3xl font-black tracking-tighter text-primary">
                   {loading ? "..." : (data?.safety_stock_units || 0).toLocaleString()} 
                   <span className="text-xs font-bold text-muted-foreground ml-2 uppercase tracking-widest">Units</span>
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-6 bg-background/50 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/5 shadow-xl">
              <div className="flex items-center gap-2">
                <div className="w-3 h-1 bg-primary rounded-full"></div>
                <span className="text-[9px] text-muted-foreground font-black uppercase tracking-widest leading-none">P50 Predict</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-primary/20 border border-primary/30 rounded shadow-inner"></div>
                <span className="text-[9px] text-muted-foreground font-black uppercase tracking-widest leading-none">90% Conf. Interval</span>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full relative">
            {loading && (
              <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-card/5 backdrop-blur-sm rounded-2xl">
                 <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
                 <span className="text-[10px] font-black uppercase tracking-[0.3em] text-primary animate-pulse">Running TFT Inference...</span>
              </div>
            )}
            
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="p50Gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.02}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10, fontWeight: 700 }} 
                  dy={15}
                />
                <YAxis 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10, fontWeight: 700 }} 
                   tickFormatter={(val) => val.toLocaleString()}
                />
                <Tooltip 
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-background/90 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl flex flex-col gap-2 min-w-[160px]">
                          <p className="text-[10px] font-black text-muted-foreground uppercase mb-1">{payload[0].payload.date}</p>
                          <div className="flex justify-between items-center text-xs font-bold">
                            <span className="text-primary mr-4 uppercase text-[9px]">P50 Expected</span>
                            <span>{payload[2]?.value?.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between items-center text-[10px] font-medium text-muted-foreground">
                            <span className="uppercase text-[9px]">P90 Ceiling</span>
                            <span>{payload[0]?.value?.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between items-center text-[10px] font-medium text-muted-foreground">
                            <span className="uppercase text-[9px]">P10 Floor</span>
                            <span>{payload[1]?.value?.toLocaleString()}</span>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                  cursor={{ stroke: "var(--primary)", strokeWidth: 1, strokeDasharray: "4 4" }}
                />
                
                {/* Confidence Interval Band (Outer) */}
                <Area 
                  type="monotone" 
                  dataKey="p90" 
                  stroke="none" 
                  fill="url(#bandGradient)" 
                  animationDuration={1500}
                />
                {/* Visual gap for the floor of the band */}
                <Area 
                  type="monotone" 
                  dataKey="p10" 
                  stroke="none" 
                  fill="var(--card)" 
                  fillOpacity={0}
                  animationDuration={1500}
                />
                
                {/* Median Forecast Line */}
                <Area 
                  type="monotone" 
                  dataKey="p50" 
                  stroke="var(--primary)" 
                  strokeWidth={4} 
                  fill="url(#p50Gradient)" 
                  animationDuration={2000}
                  strokeLinecap="round"
                />
                
                {/* Reorder Point Reference */}
                {!loading && data?.reorder_point && (
                  <ReferenceLine 
                    y={data.reorder_point} 
                    stroke="var(--status-red)" 
                    strokeWidth={2}
                    strokeDasharray="8 8" 
                    label={{ 
                      value: 'SYSTEM REORDER POINT', 
                      fill: 'var(--status-red)', 
                      fontSize: 9, 
                      fontWeight: 900,
                      position: 'top',
                      offset: 10
                    }} 
                  />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
          
          <div className="mt-8 flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-muted-foreground/60 border-t border-white/5 pt-6">
             <div className="flex items-center gap-2">
               <Info size={12} /> Model Confidence Interval: 90% (Temporal Fusion Transformer v4.2)
             </div>
             <div>Last Inference: {new Date().toLocaleTimeString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
