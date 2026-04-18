"use client";

import React, { useEffect, useState } from "react";
import { 
  Activity, 
  ExternalLink, 
  Globe, 
  MapPin, 
  AlertTriangle, 
  TrendingUp,
  ShieldCheck,
  Newspaper,
  Calendar
} from "lucide-react";
import { getDisruptionRisk } from "@/lib/api";
import { DisruptionData, SupplierRiskNode } from "@/lib/types";

export default function DisruptionRadar() {
  const [data, setData] = useState<DisruptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [ewsData, setEwsData] = useState<any[]>([]);

  useEffect(() => {
    const fetch = () => {
      getDisruptionRisk().then((res) => {
        setData(res);
        if (res.ews_predictions) {
          setEwsData(res.ews_predictions);
        }
      }).finally(() => setLoading(false));
    };

    fetch();
    const interval = setInterval(fetch, 5000); // Live refresh
    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
     return <div className="h-[600px] glass-card rounded-2xl animate-pulse flex items-center justify-center text-muted-foreground font-bold tracking-widest uppercase text-xs">Calibrating Planetary Risk Matrix...</div>;
  }

  return (
    <div className="space-y-8">
      {/* 90-Day Early Warning Panel */}
      <div className="glass-card p-8 rounded-2xl border-t-4 border-t-primary bg-primary/5">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
             <div className="w-12 h-12 rounded-2xl bg-primary flex items-center justify-center text-background shadow-lg shadow-primary/20">
               <Activity size={24} />
             </div>
             <div>
                <h2 className="text-2xl font-bold tracking-tight">Early Warning System (EWS)</h2>
                <p className="text-muted-foreground text-sm font-medium">Predictive disaster forecasting for the next 90 days.</p>
             </div>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-background border border-border rounded-full text-xs font-bold text-primary animate-pulse-subtle">
             <span className="w-2 h-2 rounded-full bg-primary"></span>
             PREDICTIVE MODE ACTIVE
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {ewsData.map((item, i) => (
            <div key={i} className="p-6 bg-card border border-border/50 rounded-2xl space-y-4 hover:border-primary transition-all group">
              <div className="flex justify-between items-start">
                <div>
                   <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none">{item.month}</p>
                   <h4 className="text-lg font-bold mt-1">{item.date}</h4>
                </div>
                <span className={`px-2 py-1 rounded text-[10px] font-bold ${
                  item.severity === 'CRITICAL' ? 'bg-status-red text-white' : 
                  item.severity === 'HIGH' ? 'bg-status-red/10 text-status-red' : 
                  'bg-status-amber/10 text-status-amber'
                }`}>
                  {item.severity}
                </span>
              </div>
              
              <div className="py-3 border-y border-border/10 space-y-2">
                 <div className="flex justify-between text-xs font-medium">
                   <span className="text-muted-foreground">Hazard</span>
                   <span className="text-foreground">{item.hazard}</span>
                 </div>
                 <div className="flex justify-between text-xs font-medium">
                   <span className="text-muted-foreground">Probability</span>
                   <span className="text-status-red font-bold">{item.prob}</span>
                 </div>
              </div>

              <div className="bg-secondary/20 p-3 rounded-xl">
                 <p className="text-[9px] font-black text-primary uppercase tracking-tighter mb-1">AI Mitigation Strategy</p>
                 <p className="text-xs leading-relaxed text-muted-foreground group-hover:text-foreground transition-colors">{item.mitigation}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Risk Matrix / Nodes */}
        <div className="lg:col-span-2 space-y-8">
          <div className="flex justify-between items-center">
             <h3 className="text-xl font-bold tracking-tight">Asset Vulnerability Matrix</h3>
             <div className="flex bg-secondary/30 rounded-xl px-4 py-2 border border-border items-center gap-4">
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Network Risk Index</span>
                <span className={`text-xl font-black ${
                  data.network_risk_index > 60 ? "text-status-red" : data.network_risk_index > 30 ? "text-status-amber" : "text-status-green"
                }`}>{data.network_risk_index.toFixed(1)}</span>
             </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
             {data.nodes.map((node) => (
               <div key={node.id} className="glass-card p-5 rounded-2xl border border-border hover:border-primary/50 transition-all group overflow-hidden relative">
                  <div className="flex justify-between items-start mb-4">
                     <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center text-muted-foreground group-hover:bg-primary/20 group-hover:text-primary transition-all">
                           <MapPin size={20} />
                        </div>
                        <div>
                           <p className="text-xs text-muted-foreground font-bold uppercase tracking-wider">{node.id}</p>
                           <h4 className="text-sm font-bold tracking-tight">{node.name}</h4>
                        </div>
                     </div>
                     <div className={`px-2 py-1 rounded text-[10px] font-bold ${
                       node.risk_level === 'HIGH' ? 'bg-status-red/10 text-status-red' : 
                       node.risk_level === 'MEDIUM' ? 'bg-status-amber/10 text-status-amber' : 
                       'bg-status-green/10 text-status-green'
                     }`}>
                       {node.risk_score.toFixed(0)} - {node.risk_level}
                     </div>
                  </div>

                  <div className="space-y-1">
                     {node.top_drivers.slice(0, 2).map((driver, idx) => (
                       <div key={idx} className="flex items-center gap-2 text-[10px] text-muted-foreground">
                          <AlertTriangle size={12} className={node.risk_level === 'HIGH' ? "text-status-red" : "text-status-amber"} />
                          <span className="truncate">{driver.description}</span>
                       </div>
                     ))}
                  </div>
               </div>
             ))}
          </div>
        </div>

        {/* OSINT News Intelligence */}
        <div className="lg:col-span-1 space-y-8">
          <h3 className="text-xl font-bold tracking-tight">Intelligence Signal Feed</h3>
          <div className="glass-card rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-320px)] bg-card/30">
             <div className="flex-1 overflow-y-auto p-5 space-y-6">
                {data.news_articles.map((article, idx) => (
                  <div key={idx} className="group space-y-2">
                     <h5 className="text-sm font-bold leading-tight group-hover:text-primary transition-colors cursor-pointer">
                       {article.title}
                     </h5>
                     <div className="flex items-center gap-3 text-[10px] text-muted-foreground font-semibold">
                        <span className="flex items-center gap-1 uppercase tracking-wider"><Globe size={11} /> {article.source}</span>
                        <span className={`px-2 py-0.5 rounded ${article.sentiment_label === 'NEGATIVE' ? 'bg-status-red/10 text-status-red' : 'bg-status-green/10 text-status-green'}`}>
                           {article.sentiment_label}
                        </span>
                     </div>
                     {idx < data.news_articles.length - 1 && <div className="h-px bg-border/50 pt-3"></div>}
                  </div>
                ))}
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}
