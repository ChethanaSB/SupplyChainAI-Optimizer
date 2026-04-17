"use client";

import React, { useEffect, useState } from "react";
import { 
  ArrowUpRight, 
  ArrowDownRight, 
  Info, 
  TrendingUp, 
  Leaf, 
  Truck, 
  Package, 
  AlertTriangle 
} from "lucide-react";
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  BarChart, 
  Bar 
} from "recharts";
import { getKPIDashboard } from "@/lib/api";
import { KPIDashboardData } from "@/lib/types";

const MetricCard = ({ 
  title, 
  value, 
  unit, 
  delta, 
  improved, 
  icon: Icon, 
  sparkData, 
  color = "primary" 
}: any) => (
  <div className="glass-card p-6 rounded-2xl flex flex-col gap-4 group transition-all hover:border-primary/50 relative overflow-hidden">
    <div className="flex justify-between items-start z-10">
      <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center text-muted-foreground group-hover:text-primary transition-colors">
        <Icon size={20} />
      </div>
      <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
        improved ? "bg-status-green/10 text-status-green" : "bg-status-red/10 text-status-red"
      }`}>
        {improved ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
        {Math.abs(delta)}%
      </div>
    </div>
    
    <div className="z-10">
      <p className="text-sm text-muted-foreground font-medium">{title}</p>
      <div className="flex items-baseline gap-1 mt-1">
        <h3 className="text-2xl font-bold tracking-tight">{value}</h3>
        <span className="text-sm text-muted-foreground font-medium">{unit}</span>
      </div>
    </div>

    <div className="h-16 w-full mt-2 -mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={sparkData}>
          <defs>
            <linearGradient id={`grad-${title}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={improved ? "var(--status-green)" : "var(--status-red)"} stopOpacity={0.3}/>
              <stop offset="95%" stopColor={improved ? "var(--status-green)" : "var(--status-red)"} stopOpacity={0}/>
            </linearGradient>
          </defs>
          <Area 
            type="monotone" 
            dataKey="val" 
            stroke={improved ? "var(--status-green)" : "var(--status-red)"} 
            strokeWidth={2} 
            fillOpacity={1} 
            fill={`url(#grad-${title})`} 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

export default function DashboardOverview() {
  const [data, setData] = useState<KPIDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getKPIDashboard("30d")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-44 glass-card rounded-2xl animate-pulse bg-secondary/20" />
        ))}
      </div>
    );
  }

  // Helper to map backend data to chart format
  const getSpark = (values: number[] = []) => values.map((v, i) => ({ name: i, val: v }));

  const metrics = [
    {
      title: "Service Level",
      value: data.current.service_level_pct,
      unit: "%",
      delta: data.delta_pct.service_level_pct.pct_improvement,
      improved: data.delta_pct.service_level_pct.improved,
      icon: TrendingUp,
      sparkData: getSpark(data.time_series.service_level_pct),
    },
    {
      title: "Logistics Cost",
      value: (data.current.total_logistics_cost / 1000).toFixed(1),
      unit: "k USD",
      delta: data.delta_pct.total_logistics_cost.pct_improvement,
      improved: data.delta_pct.total_logistics_cost.improved,
      icon: Package,
      sparkData: getSpark(data.time_series.inventory_turns), // Placeholder spark
    },
    {
      title: "CO2 Emissions",
      value: (data.current.co2_emissions_kg / 1000).toFixed(1),
      unit: "t CO2",
      delta: data.delta_pct.co2_emissions_kg.pct_improvement,
      improved: data.delta_pct.co2_emissions_kg.improved,
      icon: Leaf,
      sparkData: getSpark([40, 35, 38, 32, 30, 28, 25]), // Trend mock
    },
    {
      title: "Avg Lead Time",
      value: data.current.avg_lead_time_days,
      unit: "days",
      delta: data.delta_pct.avg_lead_time_days.pct_improvement,
      improved: data.delta_pct.avg_lead_time_days.improved,
      icon: Truck,
      sparkData: getSpark(data.time_series.avg_lead_time_days),
    },
  ];

  return (
    <div className="space-y-8">
      {/* KPI Matrix */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m) => (
          <MetricCard key={m.title} {...m} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Comparison Chart */}
        <div className="lg:col-span-2 glass-card p-8 rounded-2xl space-y-6">
          <div className="flex justify-between items-center">
            <div>
              <h4 className="text-xl font-bold tracking-tight">Performance Delta</h4>
              <p className="text-sm text-muted-foreground">ChainMind vs. Reorder-Point Baseline</p>
            </div>
            <div className="flex gap-4 text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-primary"></span>
                <span>ChainMind</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-muted"></span>
                <span>Baseline</span>
              </div>
            </div>
          </div>
          
          <div className="h-80 w-full mt-10">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: "Service", cm: data.current.service_level_pct, bl: data.baseline.service_level_pct },
                { name: "Cost (Idx)", cm: 100, bl: 100 + data.delta_pct.total_logistics_cost.pct_improvement },
                { name: "CO2 (Idx)", cm: 100, bl: 100 + data.delta_pct.co2_emissions_kg.pct_improvement },
                { name: "Inventory", cm: data.current.inventory_turns, bl: data.baseline.inventory_turns },
              ]}>
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} 
                  dy={10}
                />
                <YAxis hide />
                <Tooltip 
                  cursor={{ fill: "var(--secondary)", opacity: 0.5 }}
                  contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "12px" }}
                />
                <Bar dataKey="cm" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={40} />
                <Bar dataKey="bl" fill="var(--muted)" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network Status */}
        <div className="glass-card p-8 rounded-2xl flex flex-col justify-between">
          <div className="space-y-6 text-center">
            <h4 className="text-lg font-bold tracking-tight">Network Health</h4>
            <div className="relative w-40 h-40 mx-auto">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="80" cy="80" r="70"
                  fill="transparent"
                  stroke="var(--secondary)"
                  strokeWidth="12"
                />
                <circle
                  cx="80" cy="80" r="70"
                  fill="transparent"
                  stroke="var(--primary)"
                  strokeWidth="12"
                  strokeDasharray={`${2 * Math.PI * 70}`}
                  strokeDashoffset={`${2 * Math.PI * 70 * (1 - 0.88)}`}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold">88%</span>
                <span className="text-xs text-muted-foreground font-medium uppercase tracking-widest">Optimized</span>
              </div>
            </div>
            
            <div className="space-y-3 pt-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Active Routes</span>
                <span className="font-semibold text-primary">124</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Suppliers Online</span>
                <span className="font-semibold text-primary">48/50</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Current Risk Index</span>
                <span className="font-semibold text-status-amber">32.4 (MED)</span>
              </div>
            </div>
          </div>

          <button className="w-full mt-8 py-3 bg-secondary hover:bg-muted text-foreground font-semibold rounded-xl transition-all flex items-center justify-center gap-2">
            View Node Status <ArrowUpRight size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
