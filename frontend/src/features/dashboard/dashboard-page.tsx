import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sliders,
  Calendar,
  ArrowRight,
  Link2,
  Search,
  Check,
  Copy,
  Layers,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";

export function DashboardPage() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [minimalChange, setMinimalChange] = useState(true);

  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: api.dashboardSummary,
    refetchInterval: 8000,
  });

  const { data: schedule } = useQuery({
    queryKey: ["latest-schedule"],
    queryFn: api.schedules.latest,
  });

  const { data: eventsData } = useQuery({
    queryKey: ["chain-events"],
    queryFn: api.chainEvents,
  });

  const recentEvents = (eventsData?.events || []).slice(-4).reverse();

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Hash copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-12 text-left pb-16">
      {/* Hero Section matching shadcn design showcase */}
      <div className="text-center space-y-4 pt-4 pb-2 max-w-3xl mx-auto">
        <Link
          to="/app/conflicts"
          className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-zinc-900 border border-white/10 text-xs text-zinc-300 hover:text-white hover:border-white/20 transition-all shadow-xs"
        >
          <span>New CP-SAT Conflict Core Isolated</span>
          <ArrowRight size={12} className="text-zinc-400" />
        </Link>

        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white leading-tight">
          The Foundation for your Design System
        </h1>

        <p className="text-zinc-400 text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
          Composable, accessible components with thoughtful defaults. Build your own
          component library with code you can customize, extend, and make your own.
        </p>

        <div className="flex items-center justify-center gap-3 pt-2">
          <Link to="/app/schedule">
            <button className="h-10 px-6 rounded-full bg-white text-zinc-950 font-medium text-sm hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98]">
              Get Started
            </button>
          </Link>
          <Link to="/app/rules">
            <button className="h-10 px-6 rounded-full bg-zinc-900 text-zinc-300 font-medium text-sm border border-white/10 hover:bg-zinc-800 hover:text-white transition-all active:scale-[0.98]">
              View Components
            </button>
          </Link>
        </div>
      </div>

      {/* 4 Frosted Glass Boxes Grid matching the picture */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Interactive Component Controls */}
        <div className="glass-box p-5 flex flex-col justify-between space-y-4">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <button className="h-7 px-3 rounded-full bg-white text-zinc-950 font-medium text-xs flex items-center gap-1">
                <span>Button</span>
                <ArrowRight size={11} />
              </button>
              <button className="h-7 px-3 rounded-full bg-zinc-800/80 text-zinc-300 text-xs border border-white/5">
                Secondary
              </button>
              <button className="h-7 px-3 rounded-full bg-transparent text-zinc-400 text-xs border border-white/10">
                Outline
              </button>
            </div>

            <div className="relative">
              <input
                type="text"
                placeholder="Name"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full h-8 px-3 pr-8 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
              />
              <Search size={12} className="absolute right-2.5 top-2.5 text-zinc-500" />
            </div>

            <textarea
              rows={2}
              placeholder="Message"
              defaultValue="CS101, Room 101 Monday Morning"
              className="w-full p-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-zinc-300 placeholder:text-zinc-500 focus:outline-none focus:border-white/20 resize-none"
            />

            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-white text-zinc-950 text-[11px] font-medium">
                Badge
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[11px] border border-white/5">
                Secondary
              </span>

              <div className="ml-auto flex items-center gap-2 text-zinc-400">
                <button
                  type="button"
                  onClick={() => setMinimalChange(!minimalChange)}
                  className={`w-8 h-4 rounded-full transition-colors relative p-0.5 ${
                    minimalChange ? "bg-white" : "bg-zinc-800"
                  }`}
                >
                  <div
                    className={`w-3 h-3 rounded-full transition-transform ${
                      minimalChange ? "translate-x-4 bg-zinc-950" : "translate-x-0 bg-zinc-400"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2 border-t border-white/5">
            <Link to="/app/conflicts" className="flex-1">
              <button className="w-full h-7 rounded-xl bg-zinc-900 border border-white/10 text-[11px] text-zinc-300 hover:text-white">
                Alert Dialog
              </button>
            </Link>
            <Link to="/app/schedule" className="flex-1">
              <button className="w-full h-7 rounded-xl bg-zinc-900 border border-white/10 text-[11px] text-zinc-300 hover:text-white">
                Button Group
              </button>
            </Link>
          </div>
        </div>

        {/* Card 2: Contribution / Solver Activity (Rounded Vertical Bars) */}
        <div className="glass-box p-5 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-white tracking-tight">Contribution History</h3>
            <p className="text-xs text-zinc-400 mt-0.5">Last 6 months of activity</p>

            {/* Vertical Activity Bars matching the screenshot */}
            <div className="flex items-end justify-between gap-2.5 h-32 pt-4 px-1">
              {[
                { label: "Dec", height: "h-20", active: true },
                { label: "Jan", height: "h-28", active: false },
                { label: "Feb", height: "h-16", active: false },
                { label: "Mar", height: "h-32", active: false },
                { label: "Apr", height: "h-24", active: false },
              ].map((bar, i) => (
                <div key={bar.label} className="flex-1 flex flex-col items-center gap-2">
                  <div className="w-full h-24 bg-zinc-900/50 rounded-xl relative flex items-end overflow-hidden">
                    <div
                      className={`w-full ${bar.height} rounded-xl transition-all ${
                        bar.active ? "bg-zinc-200" : "bg-zinc-800/80 hover:bg-zinc-700"
                      }`}
                    />
                  </div>
                  <span className="text-[10px] text-zinc-500 font-medium">{bar.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px] text-zinc-400 border-t border-white/5 pt-3">
            <span>UPCOMING</span>
            <span className="text-zinc-300 font-medium">SAVINGS PLAN</span>
          </div>
        </div>

        {/* Card 3: Milestone / Goal Setting Form */}
        <div className="glass-box p-5 flex flex-col justify-between space-y-3">
          <div className="space-y-3">
            <div>
              <h3 className="text-sm font-semibold text-white tracking-tight">Set a new milestone</h3>
              <p className="text-xs text-zinc-400 mt-0.5 leading-snug">
                Define your financial target and we'll help you pace your savings.
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400 font-medium">Goal Name</label>
              <input
                type="text"
                defaultValue="e.g. New Car, Home Downpayment"
                className="w-full h-8 px-3 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-400 font-medium">Target Amount</label>
                <div className="h-8 px-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-zinc-200 flex items-center font-mono">
                  $15,000
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] text-zinc-400 font-medium">Target Date</label>
                <div className="h-8 px-2.5 rounded-xl bg-zinc-900/90 border border-white/10 text-xs text-zinc-200 flex items-center">
                  Dec 2025
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-1.5 pt-2">
            <Link to="/app/publish">
              <button className="w-full h-8 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm">
                Create Goal
              </button>
            </Link>
          </div>
        </div>

        {/* Card 4: Mobile Device / QR Code Verification Card */}
        <div className="glass-box p-5 flex flex-col items-center justify-between text-center space-y-3">
          <div className="p-3 bg-white rounded-2xl w-32 h-32 flex items-center justify-center shadow-md">
            {/* Crisp SVG QR code matching the screenshot */}
            <svg viewBox="0 0 100 100" className="w-full h-full text-black" fill="currentColor">
              {/* Outer corners */}
              <rect x="10" y="10" width="24" height="24" rx="2" />
              <rect x="14" y="14" width="16" height="16" fill="white" />
              <rect x="18" y="18" width="8" height="8" rx="1" />

              <rect x="66" y="10" width="24" height="24" rx="2" />
              <rect x="70" y="14" width="16" height="16" fill="white" />
              <rect x="74" y="18" width="8" height="8" rx="1" />

              <rect x="10" y="66" width="24" height="24" rx="2" />
              <rect x="14" y="70" width="16" height="16" fill="white" />
              <rect x="18" y="74" width="8" height="8" rx="1" />

              {/* Data blocks */}
              <rect x="42" y="12" width="6" height="10" />
              <rect x="52" y="16" width="6" height="6" />
              <rect x="42" y="28" width="16" height="6" />
              <rect x="12" y="42" width="10" height="6" />
              <rect x="28" y="42" width="8" height="16" />
              <rect x="42" y="42" width="16" height="16" />
              <rect x="66" y="42" width="10" height="8" />
              <rect x="80" y="46" width="8" height="12" />
              <rect x="42" y="66" width="8" height="8" />
              <rect x="54" y="66" width="8" height="18" />
              <rect x="68" y="68" width="20" height="8" />
              <rect x="72" y="80" width="16" height="8" />
            </svg>
          </div>

          <div className="space-y-1">
            <h4 className="text-xs font-semibold text-white tracking-tight">
              Scan to connect your mobile device
            </h4>
            <p className="text-[11px] text-zinc-400 leading-tight">
              Open the Ledger mobile app and scan this code to link your device.
            </p>
          </div>

          <Link to="/app/publish" className="w-full">
            <span className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors">
              ConsentLedger Anchor &bull; 0x5FbD...
            </span>
          </Link>
        </div>
      </div>

      {/* Main Bottom Section: Active Schedule & On-Chain Audit in Glass Boxes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
        {/* Current Active Timetable */}
        <div className="lg:col-span-2 glass-box p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Current Active Timetable</h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Verified schedule placements generated by Google OR-Tools CP-SAT.
              </p>
            </div>
            <Link to="/app/schedule">
              <button className="h-7 px-3 rounded-full bg-zinc-900 border border-white/10 text-xs text-zinc-300 hover:text-white flex items-center gap-1">
                <span>Full Grid</span>
                <ArrowRight size={11} />
              </button>
            </Link>
          </div>

          {schedule?.placements && schedule.placements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-white/5 text-zinc-400">
                    <th className="py-2.5 px-3 font-medium">Session ID</th>
                    <th className="py-2.5 px-3 font-medium">Teacher</th>
                    <th className="py-2.5 px-3 font-medium">Room</th>
                    <th className="py-2.5 px-3 font-medium">Day</th>
                    <th className="py-2.5 px-3 font-medium">Slot</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {schedule.placements.slice(0, 6).map((p) => {
                    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri"];
                    const slotTimes = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"];
                    return (
                      <tr key={p.session_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-2.5 px-3 font-mono font-medium text-white">{p.session_id}</td>
                        <td className="py-2.5 px-3 text-zinc-300">{p.teacher}</td>
                        <td className="py-2.5 px-3 text-zinc-400">{p.room}</td>
                        <td className="py-2.5 px-3 text-zinc-400">{dayNames[p.day] || p.day}</td>
                        <td className="py-2.5 px-3 text-zinc-400">{slotTimes[p.slot] || p.slot}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-8 text-center text-xs text-zinc-500">
              No active schedule loaded. Click &quot;Seed Demo&quot; to populate.
            </div>
          )}
        </div>

        {/* Recent Blockchain Events */}
        <div className="glass-box p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-white/5 pb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">ConsentLedger Audit</h3>
              <p className="text-xs text-zinc-400 mt-0.5">On-chain consensus events</p>
            </div>
            <Link to="/app/chain-log">
              <button className="h-7 px-3 rounded-full bg-zinc-900 border border-white/10 text-xs text-zinc-300 hover:text-white flex items-center gap-1">
                <span>View Log</span>
                <ArrowRight size={11} />
              </button>
            </Link>
          </div>

          <div className="space-y-2.5">
            {recentEvents.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-500">
                No on-chain events yet.
              </div>
            ) : (
              recentEvents.map((ev, i) => (
                <div
                  key={`${ev.block}-${ev.idx}-${i}`}
                  className="p-3 rounded-xl bg-white/[0.02] border border-white/5 space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 text-xs">{ev.event}</span>
                    <span className="font-mono text-[10px] text-zinc-500">Block #{ev.block}</span>
                  </div>
                  {ev.args?.rule_id && (
                    <div className="text-[11px] text-zinc-400 flex items-center gap-1.5">
                      <span>Rule:</span>
                      <span className="font-mono text-zinc-300">{ev.args.rule_id}</span>
                    </div>
                  )}
                  {ev.args?.schedule_hash && (
                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-400">
                      <span className="truncate max-w-[140px]">{ev.args.schedule_hash.slice(0, 14)}...</span>
                      <button
                        onClick={() => handleCopy(ev.args.schedule_hash, `dash_${i}`)}
                        className="text-zinc-400 hover:text-white transition-colors"
                      >
                        {copiedKey === `dash_${i}` ? <Check size={12} className="text-white" /> : <Copy size={12} />}
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
