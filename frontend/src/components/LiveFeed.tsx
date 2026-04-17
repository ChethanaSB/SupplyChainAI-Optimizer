"use client";

import React, { useEffect, useState, useRef } from "react";
import { 
  Bell, 
  AlertCircle, 
  Zap, 
  Truck, 
  Package, 
  Activity,
  X
} from "lucide-react";
import { LiveEvent } from "@/lib/types";

export default function LiveFeed() {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Determine WS URL (handling local/prod)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/live-feed`;

    const connect = () => {
      console.log("Connecting to WebSocket:", wsUrl);
      const ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        const data: LiveEvent = JSON.parse(event.data);
        if (data.payload.message !== "heartbeat") {
           setEvents(prev => [data, ...prev].slice(0, 10)); // Keep last 10
        }
      };

      ws.onclose = () => {
        console.log("WS closed. Retrying in 5s...");
        setTimeout(connect, 5000);
      };

      socketRef.current = ws;
    };

    connect();

    return () => {
      socketRef.current?.close();
    };
  }, []);

  const unreadCount = events.length;

  const getIcon = (type: string) => {
    switch (type) {
      case "disruption_alert": return <AlertCircle size={14} className="text-status-red" />;
      case "kpi_update": return <Activity size={14} className="text-primary" />;
      case "route_change": return <Truck size={14} className="text-blue-400" />;
      case "inventory_alert": return <Package size={14} className="text-status-amber" />;
      default: return <Bell size={14} />;
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setShowDropdown(!showDropdown)}
        className={`p-2 rounded-xl transition-all relative ${
          unreadCount > 0 ? "bg-primary/10 text-primary border border-primary/20" : "bg-secondary/50 text-muted-foreground hover:text-foreground"
        }`}
      >
        <Bell size={20} className={unreadCount > 0 ? "animate-pulse" : ""} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
             <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
             <span className="relative inline-flex rounded-full h-4 w-4 bg-primary text-[10px] items-center justify-center font-black text-background">
               {unreadCount}
             </span>
          </span>
        )}
      </button>

      {showDropdown && (
        <div className="absolute top-14 right-0 w-80 glass-card rounded-2xl shadow-2xl z-[100] border border-border/50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
           <div className="p-4 border-b border-border bg-secondary/30 flex justify-between items-center">
              <span className="text-xs font-bold uppercase tracking-widest flex items-center gap-2">
                 <Zap size={14} className="text-primary" /> Intelligence Stream
              </span>
              <button onClick={() => setEvents([])} className="text-[10px] text-muted-foreground hover:text-foreground uppercase font-bold transition-colors">Clear</button>
           </div>
           
           <div className="max-h-96 overflow-y-auto p-2 space-y-2">
              {events.length > 0 ? events.map((event, idx) => (
                <div key={idx} className="p-3 rounded-xl bg-card hover:bg-secondary/40 border border-border/10 transition-all space-y-1">
                   <div className="flex justify-between items-center">
                      <div className="flex items-center gap-2">
                         {getIcon(event.type)}
                         <span className="text-[10px] font-bold uppercase text-muted-foreground">
                            {event.type.replace('_', ' ')}
                         </span>
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                         {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                   </div>
                   <p className="text-xs text-foreground/90 leading-tight font-medium">
                      {(event.payload as any).message || "New activity detected in the network."}
                   </p>
                </div>
              )) : (
                <div className="py-12 text-center text-muted-foreground">
                   <Package size={32} className="mx-auto opacity-10 mb-2" />
                   <p className="text-[10px] font-bold uppercase tracking-widest">Normal Operations</p>
                </div>
              )}
           </div>

           <div className="p-3 bg-secondary/10 text-center border-t border-border">
              <button className="text-[10px] font-bold text-primary hover:underline transition-all">
                Launch Incident Command Center
              </button>
           </div>
        </div>
      )}
    </div>
  );
}
