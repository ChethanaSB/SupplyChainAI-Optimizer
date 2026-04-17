"use client";

import React, { useState, useEffect } from "react";
import { 
  LayoutDashboard, 
  TrendingUp, 
  Map as MapIcon, 
  Zap, 
  Activity, 
  Settings,
  Bell,
  Search,
  Menu,
  ChevronRight,
  ShieldCheck
} from "lucide-react";
import DashboardOverview from "@/components/DashboardOverview";
import ForecastPanel from "@/components/ForecastPanel";
import RouteMap from "@/components/RouteMap";
import ScenarioSimulator from "@/components/ScenarioSimulator";
import DisruptionRadar from "@/components/DisruptionRadar";
import LiveFeed from "@/components/LiveFeed";

type Tab = "overview" | "forecast" | "routes" | "scenarios" | "radar";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const navItems = [
    { id: "overview", label: "Network Overview", icon: LayoutDashboard },
    { id: "forecast", label: "Demand Forecasting", icon: TrendingUp },
    { id: "routes", label: "Optimized Routing", icon: MapIcon },
    { id: "scenarios", label: "Scenario Simulator", icon: Zap },
    { id: "radar", label: "Disruption Radar", icon: Activity },
  ];

  return (
    <div className="flex h-screen bg-background text-foreground selection:bg-primary/30">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-20"} transition-all duration-300 ease-in-out border-r border-border bg-card/50 backdrop-blur-md flex flex-col z-50`}>
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-background">
            <ShieldCheck size={20} weight="bold" />
          </div>
          {sidebarOpen && <span className="font-bold text-xl tracking-tight">ChainMind</span>}
        </div>

        <nav className="flex-1 px-4 py-6 space-y-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as Tab)}
              className={`w-full flex items-center gap-4 p-3 rounded-xl transition-all ${
                activeTab === item.id 
                  ? "bg-primary text-background font-medium shadow-lg shadow-primary/20" 
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              <item.icon size={20} />
              {sidebarOpen && <span>{item.label}</span>}
              {activeTab === item.id && sidebarOpen && <ChevronRight size={16} className="ml-auto" />}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-border">
          <button className="w-full flex items-center gap-4 p-3 text-muted-foreground hover:text-foreground transition-all">
            <Settings size={20} />
            {sidebarOpen && <span>System Config</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <header className="h-20 border-b border-border bg-card/30 backdrop-blur-sm px-8 flex items-center justify-between z-40">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-secondary rounded-lg transition-all"
            >
              <Menu size={20} />
            </button>
            <div className="relative group overflow-hidden rounded-xl bg-secondary/50 border border-border focus-within:border-primary/50 transition-all max-w-md">
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input 
                type="text" 
                placeholder="Search SKU, Route or Supplier..." 
                className="bg-transparent border-none outline-none pl-10 pr-4 py-2 w-full text-sm placeholder:text-muted-foreground"
              />
            </div>
          </div>

          <div className="flex items-center gap-6">
            <LiveFeed />
            <button className="relative p-2 hover:bg-secondary rounded-lg transition-all text-muted-foreground hover:text-foreground">
              <Bell size={20} />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-destructive rounded-full border-2 border-background"></span>
            </button>
            <div className="flex items-center gap-3 pl-6 border-l border-border">
              <div className="text-right">
                <p className="text-xs text-muted-foreground">Logistics Lead</p>
                <p className="text-sm font-semibold">Supply Chain Admin</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center font-bold text-primary">
                CM
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 relative scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
          <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {activeTab === "overview" && <DashboardOverview />}
            {activeTab === "forecast" && <ForecastPanel />}
            {activeTab === "routes" && <RouteMap />}
            {activeTab === "scenarios" && <ScenarioSimulator />}
            {activeTab === "radar" && <DisruptionRadar />}
          </div>
        </div>

        {/* Decorative Background Accents */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] -z-10 translate-x-1/2 -translate-y-1/2"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-primary/3 rounded-full blur-[100px] -z-10 -translate-x-1/2 translate-y-1/2"></div>
      </main>
    </div>
  );
}
