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

  useEffect(() => {
    getDisruptionRisk()
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
     return <div className="h-[600px] glass-card rounded-2xl animate-pulse flex items-center justify-center text-muted-foreground">Synthesizing Global Risk Matrix...</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Risk Matrix / Nodes */}
      <div className="lg:col-span-2 space-y-8">
        <div className="flex justify-between items-center">
           <div>
             <h2 className="text-2xl font-bold tracking-tight">Active Disruption Risk</h2>
             <p className="text-muted-foreground text-sm">Real-time monitoring of 50 global supplier nodes.</p>
           </div>
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

                <div className="space-y-2 mb-4">
                   <div className="flex justify-between items-center text-[10px] text-muted-foreground">
                      <span>MONTE CARLO PROB</span>
                      <span className="font-bold">{(node.monte_carlo_p90 * 100).toFixed(1)}%</span>
                   </div>
                   <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-1000 ${
                          node.risk_level === 'HIGH' ? 'bg-status-red' : 
                          node.risk_level === 'MEDIUM' ? 'bg-status-amber' : 
                          'bg-status-green'
                        }`}
                        style={{ width: `${node.risk_score}%` }}
                      ></div>
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

                {/* Status Indicator Glow */}
                <div className={`absolute -bottom-4 -right-4 w-12 h-12 rounded-full blur-xl opacity-20 ${
                   node.risk_level === 'HIGH' ? 'bg-status-red' : 
                   node.risk_level === 'MEDIUM' ? 'bg-status-amber' : 
                   'bg-status-green'
                }`}></div>
             </div>
           ))}
        </div>
      </div>

      {/* OSINT News Intelligence */}
      <div className="lg:col-span-1 space-y-8">
        <div>
           <h2 className="text-2xl font-bold tracking-tight">Intelligence Feed</h2>
           <p className="text-muted-foreground text-sm">Real-time signal analysis from NewsAPI & HF NER.</p>
        </div>

        <div className="glass-card rounded-2xl overflow-hidden flex flex-col h-[calc(100vh-280px)]">
           <div className="p-4 bg-secondary/20 border-b border-border flex items-center gap-2">
              <Activity size={16} className="text-primary animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-widest">Live Signals</span>
           </div>
           
           <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-hide">
              {data.news_articles.length > 0 ? data.news_articles.map((article, idx) => (
                <div key={idx} className="group space-y-3">
                   <div className="flex justify-between items-start gap-3">
                      <div className={`mt-1 p-2 rounded-lg ${
                        article.severity >= 4 ? "bg-status-red/10 text-status-red" : "bg-blue-500/10 text-blue-400"
                      }`}>
                         <Newspaper size={16} />
                      </div>
                      <div className="flex-1">
                         <h5 className="text-sm font-bold leading-tight group-hover:text-primary transition-colors cursor-pointer flex items-start gap-2">
                           {article.title}
                           <ExternalLink size={12} className="mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
                         </h5>
                         <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground font-semibold">
                            <span className="flex items-center gap-1 uppercase tracking-wider"><Globe size={11} /> {article.source}</span>
                            <span className="flex items-center gap-1 uppercase tracking-wider"><Calendar size={11} /> {new Date(article.published_at).toLocaleDateString()}</span>
                         </div>
                      </div>
                   </div>
                   
                   <div className="flex flex-wrap gap-2 pl-12">
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase ${
                        article.sentiment_label === 'NEGATIVE' ? 'bg-status-red/10 text-status-red' : 'bg-status-green/10 text-status-green'
                      }`}>
                         {article.sentiment_label}
                      </span>
                      {article.entities.map((ent, eidx) => (
                        <span key={eidx} className="px-2 py-0.5 rounded bg-secondary text-muted-foreground text-[9px] font-bold uppercase">
                           {ent}
                        </span>
                      ))}
                   </div>
                   
                   {idx < data.news_articles.length - 1 && <div className="h-px bg-border w-10/12 mx-auto pt-4"></div>}
                </div>
              )) : (
                <div className="text-center py-20 text-muted-foreground flex flex-col items-center gap-4">
                   <Globe size={40} className="opacity-20" />
                   <p className="text-xs font-bold uppercase tracking-widest">No Active Threat Signals</p>
                </div>
              )}
           </div>

           <div className="p-4 border-t border-border bg-card">
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground font-bold p-3 bg-secondary/30 rounded-xl border border-border/50 leading-relaxed">
                 <ShieldCheck size={16} className="text-primary flex-shrink-0" />
                 <span>All signals are processed through a multi-layer NLP sentiment and NER engine for false-potection.</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
