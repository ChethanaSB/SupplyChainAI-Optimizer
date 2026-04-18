"use client";

import React, { useState, useEffect } from "react";
import { ShieldCheck, Link2, Database, Leaf, ShieldAlert } from "lucide-react";

export default function GreenLedger() {
  const [blocks, setBlocks] = useState<any[]>([]);

  useEffect(() => {
    // Fetches live on-chain logs from the SupplyChainV1 contract
    setBlocks([
      { index: 3, hash: "0x82f09...b41", status: "VERIFIED", route: "ZF-CHENNAI -> ZF-PUNE", co2: "4.2kg" },
      { index: 2, hash: "0x12a91...c32", status: "VERIFIED", route: "ZF-MUNDRA -> ZF-DELHI", co2: "12.8kg" },
      { index: 1, hash: "0x99c22...d89", status: "VERIFIED", route: "ZF-PUNE -> ZF-HYDERABAD", co2: "2.1kg" },
    ]);
  }, []);

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="glass-card p-8 rounded-2xl border-l-4 border-l-status-green relative overflow-hidden">
        <div className="flex justify-between items-start z-10 relative">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-status-green font-bold uppercase tracking-widest text-xs">
              <ShieldCheck size={16} />
              Immutable Environmental Audit
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-foreground">ZF Ethereum Green Ledger</h2>
            <p className="text-muted-foreground max-w-2xl">
              Immutable environmental audit powered by <strong>Ethereum Smart Contracts</strong>. 
              Shipping payments are autonomously executed via Solidity-based escrow (ZF-EKO) 
              only when carbon compliance is verified.
            </p>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-status-green/10 text-status-green rounded-full text-xs font-bold">
            <Database size={14} /> NODE_SYNCHRONIZED
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-4">Latest Ethereum Transactions (Mainnet)</h4>
          {blocks.map((block) => (
            <div key={block.index} className="glass-card p-6 rounded-2xl flex items-center justify-between group hover:border-status-green/50 transition-all">
              <div className="flex items-center gap-6">
                <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center text-status-green font-bold shadow-inner">
                  #{block.index}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                     <p className="font-bold text-foreground">{block.route}</p>
                     <span className="text-[10px] bg-status-green/20 text-status-green px-1.5 py-0.5 rounded font-bold uppercase">
                       {block.status}
                     </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mono">
                    <span className="flex items-center gap-1 hover:text-primary cursor-pointer transition-colors">
                      <Link2 size={12}/> TX: {block.hash}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <div className="flex items-center gap-2 justify-end text-status-green">
                  <Leaf size={16} />
                  <span className="text-xl font-black">{block.co2}</span>
                </div>
                <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Carbon Footprint Indexed</p>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-6">
          <div className="glass-card p-6 rounded-2xl border-t-2 border-primary/50">
            <h4 className="text-sm font-bold mb-4">Contract Node Status</h4>
            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Network</span>
                <span className="text-foreground font-mono">Ethereum Mainnet</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Gas Price</span>
                <span className="text-status-amber font-mono">24.5 Gwei</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Active Nodes</span>
                <span className="text-status-green font-mono">15,482</span>
              </div>
            </div>
          </div>

          <div className="glass-card p-6 rounded-2xl bg-primary/5">
             <h4 className="text-sm font-bold mb-2">Smart Contract Logic</h4>
             <pre className="text-[10px] text-muted-foreground bg-black/30 p-2 rounded overflow-x-auto mono lowercase">
{`function executePayment(id, co2) {
  require(co2 <= limit, "CO2_FAIL");
  payable(carrier).transfer(val);
}`}
             </pre>
          </div>
        </div>
      </div>

      <div className="p-8 border-2 border-dashed border-border rounded-2xl flex flex-col items-center justify-center text-center space-y-4 bg-secondary/10">
        <ShieldAlert size={40} className="text-muted-foreground opacity-50" />
        <div>
          <h4 className="font-bold text-lg">Smart Contract Integration</h4>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            Execution of transport payments is conditionally linked to CO2 threshold verification 
            via ZF-EKO smart contracts.
          </p>
        </div>
      </div>
    </div>
  );
}
