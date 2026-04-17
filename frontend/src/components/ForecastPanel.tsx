"use client";

import React, { useEffect, useState } from "react";
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
import { Calendar, Search, Info, TrendingUp, Package, ShieldCheck } from "lucide-react";
import { getForecast } from "@/lib/api";
import { ForecastData } from "@/lib/types";

export default function ForecastPanel() {
  const [sku, setSku] = useState("SKU-0001");
  const [data, setData] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getForecast(sku, 30)
      .then(setData)
      .finally(() => setLoading(false));
  }, [sku]);

  const chartData = data?.dates.map((date, i) => ({
    date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    p10: data.p10[i],
    p50: data.p50[i],
    p90: data.p90[i],
  })) || [];

  return (
    <div className="space-y-8 h-full">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Demand Intelligence</h2>
          <p className="text-muted-foreground text-sm">Multi-horizon forecasting powered by Temporal Fusion Transformers (TFT)</p>
        </div>
        
        <div className="flex bg-secondary/50 rounded-xl p-1 border border-border">
          <button className="px-4 py-2 bg-primary text-background text-xs font-bold rounded-lg transition-all">30 Days</button>
          <button className="px-4 py-2 text-muted-foreground text-xs font-bold rounded-lg hover:text-foreground transition-all">60 Days</button>
          <button className="px-4 py-2 text-muted-foreground text-xs font-bold rounded-lg hover:text-foreground transition-all">90 Days</button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Controls */}
        <div className="glass-card p-6 rounded-2xl space-y-6 flex flex-col h-full">
          <div className="space-y-2">
            <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Asset Selection</label>
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <select 
                value={sku}
                onChange={(e) => setSku(e.target.value)}
                className="w-full bg-secondary/50 border border-border rounded-xl py-2 pl-10 pr-4 text-sm outline-none focus:border-primary/50 transition-all appearance-none cursor-pointer"
              >
                {[...Array(20)].map((_, i) => (
                  <option key={i} value={`SKU-00${(i+1).toString().padStart(2, '0')}`}>SKU-00${(i+1).toString().padStart(2, '0')}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-4 pt-4 border-t border-border">
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Confidence Level</span>
              <span className="font-bold text-primary">High (90%)</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Seasonality Detect</span>
              <span className="font-bold text-status-green">Enabled</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-muted-foreground">Lead Time Bias</span>
              <span className="font-bold text-status-amber">+1.2 Days</span>
            </div>
          </div>

          <div className="flex-1"></div>

          <div className="space-y-4">
            <div className="p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-2">
              <div className="flex items-center gap-2 text-primary">
                <ShieldCheck size={18} />
                <span className="text-sm font-bold">Optimization Advice</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Projected demand spike in 12 days. Recommend increasing Safety Stock by <span className="text-primary font-bold">150 units</span> to maintain 98% SL.
              </p>
            </div>
          </div>
        </div>

        {/* Forecast Chart */}
        <div className="lg:col-span-3 glass-card p-8 rounded-2xl min-h-[500px] flex flex-col">
          <div className="flex justify-between items-center mb-8">
            <div className="flex gap-6">
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-semibold uppercase tracking-widest">Reorder Point</span>
                <span className="text-xl font-bold">{data?.reorder_point || 0} <span className="text-sm font-normal text-muted-foreground">units</span></span>
              </div>
              <div className="flex flex-col">
                <span className="text-xs text-muted-foreground font-semibold uppercase tracking-widest">Safety Stock</span>
                <span className="text-xl font-bold text-primary">{data?.safety_stock_units || 0} <span className="text-sm font-normal text-muted-foreground">units</span></span>
              </div>
            </div>
            
            <div className="flex items-center gap-4 bg-secondary/30 p-2 rounded-xl border border-border">
              <div className="flex items-center gap-2">
                <div className="w-3 h-1 bg-muted-foreground"></div>
                <span className="text-[10px] text-muted-foreground font-bold uppercase">History</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-primary/30 border border-primary rounded-sm"></div>
                <span className="text-[10px] text-muted-foreground font-bold uppercase">P10-P90 Range</span>
              </div>
            </div>
          </div>

          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="p50Gradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} 
                  dy={10}
                />
                <YAxis 
                   axisLine={false} 
                   tickLine={false} 
                   tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} 
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "12px", fontSize: "12px" }}
                  cursor={{ stroke: "var(--primary)", strokeWidth: 1 }}
                />
                
                {/* Confidence Interval Band */}
                <Area 
                  type="monotone" 
                  dataKey="p90" 
                  stroke="none" 
                  fill="var(--primary)" 
                  fillOpacity={0.05} 
                />
                <Area 
                  type="monotone" 
                  dataKey="p10" 
                  stroke="none" 
                  fill="var(--background)" 
                  fillOpacity={1} 
                />
                
                {/* Median Forecast */}
                <Area 
                  type="monotone" 
                  dataKey="p50" 
                  stroke="var(--primary)" 
                  strokeWidth={3} 
                  fill="url(#p50Gradient)" 
                  animationDuration={1500}
                />
                
                <ReferenceLine y={data?.reorder_point} stroke="var(--status-red)" strokeDasharray="5 5" label={{ value: 'ROP', fill: 'var(--status-red)', fontSize: 10, position: 'right' }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
