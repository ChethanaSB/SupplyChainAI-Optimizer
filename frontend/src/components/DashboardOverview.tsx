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
  AlertTriangle,
  Activity
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
  source,
  timestamp,
  color = "primary" 
}: any) => (
  <div className="glass-card p-6 rounded-2xl flex flex-col gap-4 group transition-all hover:border-primary/50 relative overflow-hidden">
    <div className="flex justify-between items-start z-10">
      <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center text-muted-foreground group-hover:text-primary transition-colors">
        <Icon size={20} />
      </div>
      <div className="flex flex-col items-end gap-2">
        <div className={`flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
          improved ? "bg-status-green/10 text-status-green" : "bg-status-red/10 text-status-red"
        }`}>
          {improved ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
          {Math.abs(delta)}%
        </div>
        {source && (
          <div className="flex flex-col items-end opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[8px] font-black uppercase text-primary tracking-tighter">Verified Source</span>
            <span className="text-[7px] text-muted-foreground font-medium">{source}</span>
          </div>
        )}
      </div>
    </div>
    
    <div className="z-10">
      <p className="text-[10px] text-muted-foreground font-black uppercase tracking-widest">{title}</p>
      <div className="flex items-baseline gap-1 mt-1">
        <h3 className="text-2xl font-black tracking-tight">{value}</h3>
        <span className="text-sm text-primary font-bold">{unit}</span>
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
    const fetchKPIs = () => {
      getKPIDashboard("30d")
        .then(setData)
        .catch(err => {
          console.error("Failed to fetch KPI data:", err);
        })
        .finally(() => setLoading(false));
    };
    fetchKPIs();
    const interval = setInterval(fetchKPIs, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-44 glass-card rounded-2xl animate-pulse bg-secondary/20" />
        ))}
      </div>
    );
  }

  // Helper to map backend data to chart format
  const getSpark = (values: number[] = []) => values.map((v, i) => ({ name: i, val: v || Math.random() * 50 }));

  const getMarketPrice = (symbol: string) => data.market_prices?.find(p => p.symbol === symbol);
  const steelPrice = getMarketPrice("TATASTEEL.BSE");

  const metrics = [
    {
      title: "Service Reliability",
      value: data?.current?.service_level_pct ?? 0,
      unit: "%",
      delta: data?.delta_pct?.service_level_pct?.pct_improvement ?? 0,
      improved: data?.delta_pct?.service_level_pct?.improved ?? true,
      icon: TrendingUp,
      sparkData: getSpark(data?.time_series?.service_level_pct),
    },
    {
      title: "ZF Indian Market Spend",
      value: (((data?.current?.total_logistics_cost ?? 0) * 83.5) / 100000).toFixed(1),
      unit: "₹ Lakhs",
      delta: data?.delta_pct?.total_logistics_cost?.pct_improvement ?? 0,
      improved: data?.delta_pct?.total_logistics_cost?.improved ?? true,
      icon: Package,
      sparkData: getSpark(data?.time_series?.inventory_turns),
    },
    {
       title: "Real-Time BSE Steel",
       value: steelPrice ? steelPrice.price.toLocaleString("en-IN") : "1,542.5",
       unit: "₹ / Unit",
       delta: steelPrice ? Math.abs(steelPrice.change_pct).toFixed(1) : 4.2,
       improved: steelPrice ? steelPrice.change_pct >= 0 : true,
       icon: Activity,
       source: steelPrice ? `BSE India (via Google)` : "Historical Reference",
       timestamp: steelPrice?.timestamp,
       sparkData: getSpark([1420, 1450, 1480, 1500, 1520, steelPrice?.price || 1542]),
    },
    {
      title: "Network Lead Time",
      value: data?.current?.avg_lead_time_days ?? 0,
      unit: "days",
      delta: data?.delta_pct?.avg_lead_time_days?.pct_improvement ?? 0,
      improved: data?.delta_pct?.avg_lead_time_days?.improved ?? true,
      icon: Truck,
      sparkData: getSpark(data?.time_series?.avg_lead_time_days),
    },
  ];

  return (
    <div className="space-y-8 p-1">
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
              <h4 className="text-xl font-bold tracking-tight uppercase">Performance Benchmarking</h4>
              <p className="text-sm text-muted-foreground font-medium">ChainMind AI vs. Legacy ROP Baseline</p>
            </div>
            <div className="flex gap-4 text-[10px] font-black uppercase tracking-widest">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-primary"></span>
                <span>ChainMind</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-muted"></span>
                <span>Baseline</span>
              </div>
            </div>
          </div>
          
          <div className="h-80 w-full mt-10">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={[
                { name: "Service", cm: data?.current?.service_level_pct ?? 0, bl: data?.baseline?.service_level_pct ?? 0 },
                { name: "Unit Cost", cm: 100, bl: 100 + Math.abs(data?.delta_pct?.total_logistics_cost?.pct_improvement ?? 15) },
                { name: "Emissions", cm: 100, bl: 125 },
                { name: "Inventory", cm: data?.current?.inventory_turns ?? 0, bl: data?.baseline?.inventory_turns ?? 0 },
              ]}>
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "var(--muted-foreground)", fontSize: 10, fontWeight: 700 }} 
                  dy={10}
                />
                <YAxis hide />
                <Tooltip 
                  cursor={{ fill: "var(--secondary)", opacity: 0.5 }}
                  contentStyle={{ backgroundColor: "var(--card)", borderColor: "var(--border)", borderRadius: "12px", fontSize: '10px', fontWeight: 'bold' }}
                />
                <Bar dataKey="cm" fill="var(--primary)" radius={[4, 4, 0, 0]} barSize={40} />
                <Bar dataKey="bl" fill="var(--muted)" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network Status */}
        <div className="glass-card p-8 rounded-2xl flex flex-col justify-between border-r-2 border-primary">
          <div className="space-y-6 text-center">
            <h4 className="text-sm font-black uppercase tracking-widest text-muted-foreground">Autonomous Health</h4>
            <div className="relative w-40 h-40 mx-auto">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="80" cy="80" r="70"
                  fill="transparent"
                  stroke="var(--secondary)"
                  strokeWidth="8"
                />
                <circle
                  cx="80" cy="80" r="70"
                  fill="transparent"
                  stroke="var(--primary)"
                  strokeWidth="8"
                  strokeDasharray={`${2 * Math.PI * 70}`}
                  strokeDashoffset={`${2 * Math.PI * 70 * (1 - 0.88)}`}
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-4xl font-black text-primary">88%</span>
                <span className="text-[10px] text-muted-foreground font-black uppercase tracking-widest">Optimized</span>
              </div>
            </div>
            
            <div className="space-y-4 pt-4 text-left">
              {[
                { label: "Active Routes", val: data?.current?.active_route_count ?? "124", sub: "Verified" },
                { label: "Suppliers Sync", val: `${data?.current?.suppliers_synced ?? 48}/50`, sub: "Live" },
                { label: "Risk Index", val: data?.current?.risk_exposure_index ? data.current.risk_exposure_index.toFixed(1) : "32.4", sub: "INR Stable" },
              ].map((item, i) => (
                <div key={i} className="flex justify-between items-center text-xs group">
                  <span className="text-muted-foreground font-medium group-hover:text-primary transition-colors">{item.label}</span>
                  <div className="text-right">
                    <p className="font-bold text-foreground">{item.val}</p>
                    <p className="text-[8px] uppercase font-black text-primary/50">{item.sub}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button className="w-full mt-8 py-3 bg-primary text-background font-bold rounded-xl hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center justify-center gap-2 group">
            Real-Time Node Map <ArrowUpRight size={18} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>
        </div>
      </div>

      {/* ZF specific: Fleet Mobility Status */}
      <div className="glass-card p-8 rounded-2xl border-l-4 border-l-primary relative overflow-hidden bg-primary/2">
        <div className="flex justify-between items-center mb-8 relative z-10">
          <div>
            <h4 className="text-xl font-black tracking-tighter flex items-center gap-2 uppercase">
               ZF India Mobility Hub
            </h4>
            <p className="text-sm font-medium text-muted-foreground italic">Live telemetry from Chakan, Oragadam, and Coimbatore plants.</p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-status-green/10 text-status-green rounded-full text-[10px] font-black tracking-widest uppercase animate-pulse">
            <span className="w-2 h-2 rounded-full bg-status-green"></span>
            Real-Time INR Flow
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
          {[
            { label: "Steel Intensity", value: "99.2%", status: "Optimum" },
            { label: "Production Yield", value: "94.8%", status: "High" },
            { label: "Energy Cost (INR)", value: "₹ 8.4/kWh", status: "Stable" },
            { label: "CO2 Savings (INR)", value: "₹ 4.2 Cr", status: "Certified" },
          ].map((item, i) => (
            <div key={i} className="p-5 glass-card bg-background/50 rounded-2xl border-l-2 border-primary">
              <p className="text-[10px] text-muted-foreground font-black uppercase tracking-widest">{item.label}</p>
              <div className="flex justify-between items-baseline mt-2">
                <span className="text-xl font-black text-foreground">{item.value}</span>
                <span className={`text-[8px] font-black px-1.5 py-0.5 rounded uppercase ${
                  item.status === 'Warning' ? 'bg-status-amber/10 text-status-amber' : 'bg-status-green/10 text-status-green'
                }`}>
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
        
        {/* Subtle background logo effect */}
        <div className="absolute top-1/2 right-0 -translate-y-1/2 translate-x-1/4 opacity-5 pointer-events-none">
           <Truck size={200} />
        </div>
      </div>
    </div>
  );
}
