"use client";

import React, { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { optimizeRouting } from "@/lib/api";
import { RoutingData, RouteArc } from "@/lib/types";
import { Truck, Navigation, DollarSign, Leaf, Zap, Globe } from "lucide-react";

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(() => import("react-leaflet").then(mod => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(mod => mod.TileLayer), { ssr: false });
const Polyline = dynamic(() => import("react-leaflet").then(mod => mod.Polyline), { ssr: false });
const CircleMarker = dynamic(() => import("react-leaflet").then(mod => mod.CircleMarker), { ssr: false });
const Tooltip = dynamic(() => import("react-leaflet").then(mod => mod.Tooltip), { ssr: false });

// Mock coordinates for Suppliers and Plants (Centralized for dashboard feel)
const LOCATIONS: Record<string, [number, number]> = {
  "SUP-01": [52.52, 13.40], // Berlin
  "SUP-02": [48.85, 2.35],  // Paris
  "SUP-03": [51.50, -0.12], // London
  "SUP-04": [41.38, 2.17],  // Barcelona
  "SUP-05": [35.68, 139.65], // Tokyo
  "SUP-06": [31.23, 121.47], // Shanghai
  "PLT-01": [50.11, 8.68],  // Frankfurt
  "PLT-02": [45.46, 9.18],  // Milan
  "PLT-03": [40.71, -74.00], // New York
};

export default function RouteMap() {
  const [data, setData] = useState<RoutingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null);

  useEffect(() => {
    optimizeRouting({})
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data) {
    return <div className="h-[600px] glass-card rounded-2xl animate-pulse flex items-center justify-center text-muted-foreground">Initializing Global Route Optimizer...</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[700px]">
      {/* Route List Sidebar */}
      <div className="lg:col-span-1 glass-card rounded-2xl flex flex-col overflow-hidden">
        <div className="p-6 border-b border-border bg-secondary/20">
          <h3 className="text-xl font-bold tracking-tight">Active Logistics</h3>
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest mt-1">Multi-Objective Optimization</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
          {data.routes.map((route, idx) => {
            const id = `${route.supplier_id}-${route.plant_id}`;
            const isActive = selectedRoute === id;
            return (
              <div 
                key={idx}
                onClick={() => setSelectedRoute(id)}
                className={`p-4 rounded-xl border transition-all cursor-pointer group ${
                  isActive ? "bg-primary border-primary" : "bg-card/50 border-border hover:border-primary/50"
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <Truck size={16} className={isActive ? "text-background" : "text-primary"} />
                    <span className={`text-sm font-bold ${isActive ? "text-background" : "text-foreground"}`}>
                      {route.supplier_id} → {route.plant_id}
                    </span>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isActive ? "bg-background text-primary" : "bg-secondary text-muted-foreground"
                  }`}>
                    {route.mode.toUpperCase()}
                  </span>
                </div>
                
                <div className="grid grid-cols-3 gap-2 mt-3">
                  <div className="flex flex-col">
                    <span className={isActive ? "text-background/70 text-[9px]" : "text-muted-foreground text-[9px]"}>COST</span>
                    <span className={`text-xs font-bold ${isActive ? "text-background" : "text-foreground"}`}>${route.cost_usd.toFixed(0)}</span>
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
            <span className="text-primary">${data.total_cost.toLocaleString()}</span>
          </div>
          <button className="w-full py-3 bg-primary text-background font-bold rounded-xl shadow-lg shadow-primary/20 hover:scale-[1.02] transition-all flex items-center justify-center gap-2">
            Execute All Shipments <Zap size={18} fill="currentColor" />
          </button>
        </div>
      </div>

      {/* Map View */}
      <div className="lg:col-span-2 glass-card rounded-2xl overflow-hidden relative group">
        <div className="absolute top-6 left-6 z-[1000] flex gap-3">
            <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-2 shadow-xl">
               <Globe size={16} className="text-primary animate-pulse" />
               <span className="text-xs font-bold tracking-tight">Active Network Monitoring</span>
            </div>
            <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-2 shadow-xl">
               <Leaf size={16} className="text-status-green" />
               <span className="text-xs font-bold tracking-tight">Eco-Routing Active</span>
            </div>
        </div>

        <div className="w-full h-full bg-[#0b0e14]">
          {/* Leaflet CSS is handled via CDN or global import in root */}
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossOrigin="" />
          
          <MapContainer 
            center={[40, 0]} 
            zoom={2} 
            className="w-full h-full" 
            zoomControl={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            
            {data.routes.map((route, idx) => {
              const start = LOCATIONS[route.supplier_id] || [0, 0];
              const end = LOCATIONS[route.plant_id] || [0, 0];
              const isSelected = selectedRoute === `${route.supplier_id}-${route.plant_id}`;
              
              return (
                <React.Fragment key={idx}>
                  <Polyline 
                    positions={[start, end]} 
                    color={isSelected ? "var(--primary)" : "var(--primary)"} 
                    weight={isSelected ? 4 : 2}
                    opacity={isSelected ? 1 : 0.3}
                  />
                  
                  <CircleMarker center={start} radius={isSelected ? 6 : 4} color="var(--primary)" fillColor="var(--primary)" fillOpacity={1}>
                    <Tooltip direction="top" className="bg-card border-border text-foreground">Supplier {route.supplier_id}</Tooltip>
                  </CircleMarker>
                  
                  <CircleMarker center={end} radius={isSelected ? 6 : 4} color="var(--status-amber)" fillColor="var(--status-amber)" fillOpacity={1}>
                    <Tooltip direction="top">Plant {route.plant_id}</Tooltip>
                  </CircleMarker>
                </React.Fragment>
              );
            })}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
