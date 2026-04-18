"use client";

import React, { useState, useEffect } from "react";
import { 
  Newspaper, 
  ExternalLink, 
  Clock, 
  Tag, 
  TrendingDown, 
  TrendingUp, 
  Minus,
  RefreshCw,
  Info
} from "lucide-react";
import { getIntelFeed } from "@/lib/api";
import { IntelItem } from "@/lib/types";

export default function IntelligenceBlog() {
  const [articles, setArticles] = useState<IntelItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());
  const [countdown, setCountdown] = useState(30);

  const fetchIntel = async () => {
    try {
      setLoading(true);
      const data = await getIntelFeed();
      setArticles(data.articles);
      setLastRefreshed(new Date());
      setCountdown(30);
    } catch (error) {
      console.error("Error fetching intel:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntel();
    
    // Auto-refresh timer
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          fetchIntel();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment.toUpperCase()) {
      case "POSITIVE": return <TrendingUp className="text-emerald-400" size={16} />;
      case "NEGATIVE": return <TrendingDown className="text-rose-400" size={16} />;
      default: return <Minus className="text-sky-400" size={16} />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toUpperCase()) {
      case "POSITIVE": return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
      case "NEGATIVE": return "text-rose-400 bg-rose-400/10 border-rose-400/20";
      default: return "text-sky-400 bg-sky-400/10 border-sky-400/20";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-primary mb-1">
            <Newspaper size={20} />
            <span className="text-sm font-semibold tracking-wider uppercase">Real-Time Intelligence</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Supply Chain Intelligence Blog</h1>
          <p className="text-muted-foreground mt-1 max-w-2xl">
            Live scraped market insights, geopolitical signals, and logistics disruptions affecting the ZF Global Network. 
            All intelligence is scored in real-time by our NLP engine.
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-card/50 backdrop-blur-md border border-border p-2 px-4 rounded-2xl self-start md:self-auto">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-muted-foreground uppercase font-bold">Auto-Refreshing In</span>
            <div className="flex items-center gap-2">
              <span className="text-xl font-mono font-bold text-primary">{countdown}s</span>
              <div className="w-12 h-1 bg-secondary rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary transition-all duration-1000 ease-linear" 
                  style={{ width: `${(countdown / 30) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
          <button 
            onClick={fetchIntel}
            disabled={loading}
            className={`p-2 rounded-xl hover:bg-secondary transition-all ${loading ? "animate-spin" : ""}`}
          >
            <RefreshCw size={20} className="text-muted-foreground" />
          </button>
        </div>
      </div>

      {loading && articles.length === 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-pulse">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-64 rounded-3xl bg-card/50 border border-border"></div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((article, idx) => (
            <div 
              key={article.id + idx}
              className="group flex flex-col bg-card/40 hover:bg-card/60 backdrop-blur-md border border-border hover:border-primary/50 rounded-3xl transition-all duration-300 overflow-hidden shadow-xl hover:shadow-primary/5 shadow-black/20"
            >
              <div className="p-6 flex-1 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider ${getSentimentColor(article.sentiment)}`}>
                    {getSentimentIcon(article.sentiment)}
                    {article.sentiment}
                  </div>
                  <div className="flex items-center gap-1.5 text-muted-foreground text-[11px] font-medium">
                    <Clock size={12} />
                    {new Date(article.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                <h3 className="text-lg font-bold leading-tight group-hover:text-primary transition-colors line-clamp-2">
                  {article.title}
                </h3>
                
                <p className="mt-3 text-sm text-muted-foreground line-clamp-3 flex-1">
                  {article.summary || "No detailed summary available for this intelligence signal."}
                </p>

                <div className="mt-6 flex flex-wrap gap-2">
                  <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-secondary/50 text-[10px] text-muted-foreground font-semibold">
                    <Tag size={10} />
                    {article.category}
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-secondary/50 text-[10px] text-muted-foreground font-semibold">
                    <Info size={10} />
                    {article.source}
                  </div>
                </div>
              </div>

              <a 
                href={article.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="block p-4 bg-secondary/30 group-hover:bg-primary group-hover:text-background text-center transition-all duration-300 font-bold text-xs uppercase tracking-widest border-t border-border group-hover:border-primary"
              >
                <div className="flex items-center justify-center gap-2">
                  Read Full Intel 
                  <ExternalLink size={14} />
                </div>
              </a>
            </div>
          ))}
          
          {articles.length === 0 && !loading && (
            <div className="col-span-full h-80 flex flex-col items-center justify-center text-muted-foreground bg-card/20 rounded-3xl border border-dashed border-border">
              <Newspaper size={48} className="mb-4 opacity-20" />
              <p className="text-lg font-medium">No live intelligence signals found.</p>
              <p className="text-sm">Check back shortly or verify your NewsAPI configuration.</p>
            </div>
          )}
        </div>
      )}

      {/* Footer Info */}
      <div className="bg-primary/5 border border-primary/10 rounded-2xl p-4 flex gap-4 items-start">
        <div className="p-2 rounded-xl bg-primary/10 text-primary">
          <Info size={18} />
        </div>
        <div className="text-sm">
          <p className="font-bold text-primary">AI Signal Scoring System</p>
          <p className="text-muted-foreground">
            All news items are processed through ChainMind's NLP engine to extract entities and score sentiment polarity. 
            Real-time scraping is currently configured for a <span className="text-foreground font-semibold">30-second polling interval</span>.
          </p>
        </div>
      </div>
    </div>
  );
}
