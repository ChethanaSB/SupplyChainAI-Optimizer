"use client";

import React, { useEffect, useState, useMemo } from "react";
import dynamic from "next/dynamic";
import { Truck, Navigation, DollarSign, Leaf, Zap, Globe, Anchor } from "lucide-react";
import { getKPIDashboard, optimizeRouting, getLiveVessels } from "@/lib/api";

// Dynamically import Leaflet components to avoid SSR issues
const MapContainer = dynamic(() => import("react-leaflet").then(mod => mod.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(mod => mod.TileLayer), { ssr: false });
const Polyline = dynamic(() => import("react-leaflet").then(mod => mod.Polyline), { ssr: false });
const CircleMarker = dynamic(() => import("react-leaflet").then(mod => mod.CircleMarker), { ssr: false });
const Marker = dynamic(() => import("react-leaflet").then(mod => mod.Marker), { ssr: false });
const Tooltip = dynamic(() => import("react-leaflet").then(mod => mod.Tooltip), { ssr: false });

// Dynamic routing visualization centered on India

export default function RouteMap() {
  const [data, setData] = useState<RoutingData | null>(null);
  const [vessels, setVessels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null);

  useEffect(() => {
    // Initial data fetch
    optimizeRouting([])
      .then(setData)
      .finally(() => setLoading(false));

    // Polling for live vessels
    const interval = setInterval(() => {
        getLiveVessels().then(setVessels);
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading || !data) {
    return <div className="h-[600px] glass-card rounded-2xl animate-pulse flex items-center justify-center text-muted-foreground">Initializing Global Route Optimizer...</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[800px]">
      {/* Route List Sidebar */}
      <div className="lg:col-span-1 glass-card rounded-2xl flex flex-col overflow-hidden">
        <div className="p-6 border-b border-border bg-secondary/20">
          <h3 className="text-xl font-bold tracking-tight">ZF Fleet & Routes</h3>
          <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest mt-1">Tier-1 Node Management</p>
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
      <div className="lg:col-span-3 glass-card rounded-2xl overflow-hidden relative group">
        <div className="absolute top-6 left-6 z-[1000] flex flex-col gap-3">
            <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-3 shadow-xl pointer-events-auto">
               <Globe size={18} className="text-primary animate-pulse" />
               <div className="flex flex-col">
                 <span className="text-xs font-bold tracking-tight">ZF Global Shipments</span>
                 <span className="text-[10px] text-primary/80 font-medium">Sea-Distances.org Optimized</span>
               </div>
            </div>
            <div className="bg-background/80 backdrop-blur-md px-4 py-2 rounded-xl border border-border flex items-center gap-3 shadow-xl">
               <Anchor size={18} className="text-sky-400" />
               <div className="flex flex-col">
                 <span className="text-xs font-bold tracking-tight">Active Sea Traffic</span>
                 <span className="text-[10px] text-sky-400/80 font-medium">{vessels.length} Vessels Tracked</span>
               </div>
            </div>
        </div>
        
        <div className="absolute top-6 right-6 z-[1000] pointer-events-none">
            <div className="bg-background/60 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-border/50 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_var(--primary)] animate-pulse"></div>
                <span className="text-[10px] font-bold uppercase tracking-tighter text-muted-foreground">ZF System Live</span>
            </div>
        </div>

        <div className="w-full h-full bg-[#0b0e14]">
          {/* Leaflet CSS is handled via CDN or global import in root */}
          <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossOrigin="" />
          
            <MapContainer 
            center={[20.5937, 78.9629]} 
            zoom={5} 
            className="w-full h-full" 
            zoomControl={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            
            {/* Draw Routes */}
            {data.routes.map((route, idx) => {
              const startLat = route.origin_lat;
              const startLon = route.origin_lon;
              const endLat = route.dest_lat;
              const endLon = route.dest_lon;

              if (typeof startLat !== 'number' || typeof startLon !== 'number' ||
                  typeof endLat !== 'number' || typeof endLon !== 'number' ||
                  isNaN(startLat) || isNaN(startLon) || isNaN(endLat) || isNaN(endLon)) {
                return null;
              }
              
              const start: [number, number] = [startLat, startLon];
              const end: [number, number] = [endLat, endLon];
              const isSelected = selectedRoute === `${route.supplier_id}-${route.plant_id}`;
              
              // Calculate truck position based on current time
              const time = Date.now() / 10000; // Slow movement
              const progress = (time + idx * 0.2) % 1; // Different offset per route
              const truckLat = startLat + (endLat - startLat) * progress;
              const truckLon = startLon + (endLon - startLon) * progress;

              return (
                <React.Fragment key={idx}>
                  <Polyline 
                    positions={[start, end]} 
                    color={isSelected ? "var(--primary)" : "#334155"} 
                    weight={isSelected ? 3 : 1}
                    opacity={isSelected ? 1 : 0.4}
                  />
                  
                  {/* Origin */}
                  <CircleMarker center={start} radius={isSelected ? 6 : 4} color="var(--primary)" fillColor="var(--primary)" fillOpacity={1}>
                    <Tooltip direction="top">ZF {route.supplier_id}</Tooltip>
                  </CircleMarker>
                  
                  {/* Destination */}
                  <CircleMarker center={end} radius={isSelected ? 6 : 4} color="var(--status-amber)" fillColor="var(--status-amber)" fillOpacity={1}>
                    <Tooltip direction="top">ZF {route.plant_id}</Tooltip>
                  </CircleMarker>

                  {/* Moving Truck (Simulated Live) */}
                  <CircleMarker 
                    center={[truckLat, truckLon]} 
                    radius={3} 
                    color="white" 
                    fillColor="var(--primary)" 
                    fillOpacity={1}
                  >
                     <Tooltip direction="right" permanent={isSelected}>
                        <div className="flex items-center gap-2">
                             <Truck size={10} className="text-primary" />
                             <span className="text-[9px] font-bold">ZF-TRANS-{idx+100}</span>
                        </div>
                     </Tooltip>
                  </CircleMarker>
                </React.Fragment>
              );
            })}

            {/* Draw Real-Time AIS Vessels */}
            {vessels.filter(v => v.lat != null && v.lon != null).map((v, i) => (
                <CircleMarker 
                    key={`vessel-${i}`} 
                    center={[v.lat, v.lon]} 
                    radius={4} 
                    color="#0ea5e9" 
                    fillColor="#0ea5e9" 
                    fillOpacity={0.6}
                    className="animate-pulse"
                >
                    <Tooltip direction="bottom">
                        <div className="p-1">
                            <p className="font-bold text-[10px] uppercase">{v.name}</p>
                            <div className="flex items-center gap-1 text-[8px] text-sky-400 font-bold">
                                <Anchor size={8} /> LIVE AIS TRACKING
                            </div>
                        </div>
                    </Tooltip>
                </CircleMarker>
            ))}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
