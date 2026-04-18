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
  ShieldCheck,
  FileText,
  Newspaper,
  Globe2
} from "lucide-react";
import DashboardOverview from "@/components/DashboardOverview";
import ForecastPanel from "@/components/ForecastPanel";
import RouteMap from "@/components/RouteMap";
import DisruptionRadar from "@/components/DisruptionRadar";
import LiveFeed from "@/components/LiveFeed";
import ValidationReport from "@/components/ValidationReport";
import GreenLedger from "@/components/GreenLedger";
import IntelligenceBlog from "@/components/IntelligenceBlog";
import { globalSearch, getIntelFeed } from "@/lib/api";

type Tab = "overview" | "forecast" | "routes" | "radar" | "validation" | "ledger" | "intel";

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [globalIntel, setGlobalIntel] = useState<any[]>([]);

  useEffect(() => {
    // Initial fetch for global intel from verified blog feed
    getIntelFeed()
      .then(res => setGlobalIntel(res?.articles || []))
      .catch(err => console.error("Initial intel feed failed", err));
    
    const interval = setInterval(() => {
        getIntelFeed()
          .then(res => setGlobalIntel(res?.articles || []))
          .catch(err => console.error("Periodic intel feed failed", err));
    }, 45000); // 45s refresh
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults(null);
      setShowSearchDropdown(false);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await globalSearch(searchQuery);
        setSearchResults(res);
        setShowSearchDropdown(true);
      } catch (err) {
        console.error("Search error", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const navItems = [
    { id: "overview", label: "ZF Control Tower", icon: LayoutDashboard },
    { id: "forecast", label: "LSTM Forecasting", icon: TrendingUp },
    { id: "routes", label: "Smart Routing", icon: MapIcon },
    { id: "ledger", label: "Ethereum Ledger", icon: ShieldCheck },
    { id: "radar", label: "Early Warning EWS", icon: Activity },
    { id: "validation", label: "Impact Report", icon: FileText },
    { id: "intel", label: "Intelligence Blog", icon: Newspaper },
  ];

  return (
    <div className="flex h-screen bg-background text-foreground selection:bg-primary/30">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-56" : "w-16"} transition-all duration-300 ease-in-out border-r border-border bg-card/50 backdrop-blur-md flex flex-col z-50`}>
        <div className="p-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-background shadow-lg shadow-primary/20">
            <ShieldCheck size={18} />
          </div>
          {sidebarOpen && <span className="font-bold text-lg tracking-tight">ZF ChainMind</span>}
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id as Tab)}
              className={`w-full flex items-center gap-3 p-2.5 rounded-xl transition-all ${
                activeTab === item.id 
                  ? "bg-primary text-background font-medium shadow-md shadow-primary/20" 
                  : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
              }`}
            >
              <item.icon size={18} />
              {sidebarOpen && <span className="text-sm">{item.label}</span>}
              {activeTab === item.id && sidebarOpen && <ChevronRight size={14} className="ml-auto" />}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-border">
          <button className="w-full flex items-center gap-4 p-3 text-muted-foreground hover:text-foreground transition-all">
            <Settings size={20} />
            {sidebarOpen && <span>ZF System Config</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <header className="h-16 border-b border-border bg-card/30 backdrop-blur-sm px-6 flex items-center justify-between z-40 transition-all">
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
                placeholder="Search ZF SKU, Route or Supplier..." 
                className="bg-transparent border-none outline-none pl-10 pr-4 py-2 w-full text-sm placeholder:text-muted-foreground"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onBlur={() => setTimeout(() => setShowSearchDropdown(false), 200)}
                onFocus={() => searchQuery.length >= 2 && setShowSearchDropdown(true)}
              />
              {isSearching && <div className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>}
              
              {showSearchDropdown && searchResults && (
                <div className="absolute top-full left-0 w-full mt-2 bg-card border border-border rounded-2xl shadow-2xl p-4 z-[2000] max-h-96 overflow-y-auto animate-in fade-in slide-in-from-top-2">
                   {searchResults.topology.length > 0 && (
                     <div className="mb-4">
                       <h4 className="text-[10px] font-black uppercase text-muted-foreground tracking-widest mb-2 px-2">Network Nodes</h4>
                       <div className="space-y-1">
                         {searchResults.topology.map((t: any, i: number) => (
                           <div key={i} className="flex items-center gap-3 p-2 hover:bg-secondary rounded-xl transition-all cursor-pointer">
                              <div className={`w-8 h-8 flex items-center justify-center rounded-lg ${t.type === 'PLANT' ? 'bg-sky-500/10 text-sky-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                                <Zap size={14} />
                              </div>
                              <div className="flex flex-col">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-xs font-bold">{t.data.name}</span>
                                  <span className="text-[7px] bg-primary/20 text-primary px-1 rounded font-black">LIVE</span>
                                </div>
                                <span className="text-[10px] text-muted-foreground uppercase">{t.type} • {t.data.id}</span>
                              </div>
                           </div>
                         ))}
                       </div>
                     </div>
                   )}
                   {searchResults.news.length > 0 && (
                     <div>
                       <h4 className="text-[10px] font-black uppercase text-muted-foreground tracking-widest mb-2 px-2">Intelligence Signals</h4>
                       <div className="space-y-1">
                         {searchResults.news.map((n: any, i: number) => (
                           <a key={i} href={n.url} target="_blank" rel="noreferrer" className="block p-2 hover:bg-secondary rounded-xl transition-all">
                             <p className="text-xs font-bold line-clamp-1">{n.title}</p>
                             <p className="text-[10px] text-primary font-medium">{n.source}</p>
                           </a>
                         ))}
                       </div>
                     </div>
                   )}
                   {searchResults.topology.length === 0 && searchResults.news.length === 0 && (
                     <div className="py-8 text-center text-muted-foreground">
                        <p className="text-xs">No matches found in ZF Global Network</p>
                     </div>
                   )}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="hidden xl:flex items-center gap-2 max-w-sm px-4 py-1.5 bg-primary/5 border border-primary/10 rounded-full overflow-hidden">
               <Globe2 size={14} className="text-primary animate-spin-slow" />
               <div className="flex whitespace-nowrap overflow-hidden">
                 <div className="flex animate-marquee hover:pause-marquee gap-8">
                    {globalIntel.length > 0 ? globalIntel.map((item, i) => (
                      <span key={i} className="text-[10px] font-bold text-muted-foreground">
                        <span className="text-primary uppercase mr-2">{item.source}:</span>
                        {item.title}
                      </span>
                    )) : (
                      <span className="text-[10px] font-bold text-muted-foreground animate-pulse uppercase tracking-widest">
                        Initializing Live Global Logistics Stream...
                      </span>
                    )}
                 </div>
               </div>
            </div>
            <LiveFeed />
            <div className="flex items-center gap-3 pl-6 border-l border-border">
              <div className="text-right">
                <p className="text-xs text-muted-foreground">ZF Logistics Admin</p>
                <p className="text-sm font-semibold">ZF User</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center font-bold text-primary">
                ZF
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6 relative scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
          <div className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {activeTab === "overview" && <DashboardOverview />}
            {activeTab === "forecast" && <ForecastPanel />}
            {activeTab === "routes" && <RouteMap />}
            {activeTab === "ledger" && <GreenLedger />}
            {activeTab === "radar" && <DisruptionRadar />}
            {activeTab === "validation" && <ValidationReport />}
            {activeTab === "intel" && <IntelligenceBlog />}
          </div>
        </div>

        {/* Decorative Background Accents */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] -z-10 translate-x-1/2 -translate-y-1/2"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-primary/3 rounded-full blur-[100px] -z-10 -translate-x-1/2 translate-y-1/2"></div>
      </main>
    </div>
  );
}
