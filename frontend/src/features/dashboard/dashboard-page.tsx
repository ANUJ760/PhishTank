import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  ArrowRight,
  Search,
  Check,
  Copy,
  Cpu,
  Shield,
  Mic,
  FileSpreadsheet,
  Camera,
  Zap,
  Calendar,
  Lock,
} from "lucide-react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { cardMotionVariants } from "@/lib/motion";

export function DashboardPage() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { data: summary } = useQuery({
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
    toast.success("Copied to clipboard");
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const pipelineSteps = [
    { icon: Mic, label: "Multimodal Intake", desc: "Voice, photo & spreadsheet constraint extraction via Gemma 4" },
    { icon: Cpu, label: "CP-SAT Solver", desc: "Google OR-Tools guarantees zero double-bookings" },
    { icon: Shield, label: "Consent Ledger", desc: "Cryptographic audit trail for every schedule change" },
  ];

  const capabilities = [
    { icon: Mic, label: "Voice Rules", desc: "Hindi, Marathi, English" },
    { icon: Camera, label: "Photo Scanning", desc: "Whiteboard & roster OCR" },
    { icon: FileSpreadsheet, label: "Sheet Parsing", desc: "One-shot parser generation" },
    { icon: Zap, label: "Conflict Core", desc: "Minimal unsatisfiable subset" },
    { icon: Calendar, label: "Minimal Change", desc: "Fewest classes moved" },
    { icon: Lock, label: "Tamper-Proof", desc: "SHA-256 schedule hashes" },
  ];

  return (
    <div className="space-y-10 pb-16">
      {/* ─── Hero ─── */}
      <div className="text-center space-y-4 pt-2 pb-2 max-w-3xl mx-auto">
        <Link
          to="/app/conflicts"
          className="group inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.09] text-[12px] text-zinc-300 hover:text-white hover:border-white/25 hover:bg-white/[0.08] transition-all duration-200 shadow-sm hover:shadow-[0_0_15px_rgba(255,255,255,0.06)]"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400/80 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
          <span>New CP-SAT Conflict Core Isolated</span>
          <ArrowRight size={11} className="text-zinc-500 group-hover:text-white group-hover:translate-x-0.5 transition-all duration-200" />
        </Link>

        <h1 className="text-3xl md:text-[44px] font-bold tracking-tight text-white leading-[1.12]">
          Smart Scheduling with<br />Mathematical Guarantees
        </h1>

        <p className="text-zinc-400 text-sm md:text-[15px] max-w-2xl mx-auto leading-relaxed">
          GeCompose coordinates Gemma 4 multimodal intake, OR-Tools CP-SAT constraint solving, 
          and a cryptographic consent ledger to produce 100% clash-free schedules.
        </p>

        <div className="flex items-center justify-center gap-3 pt-3">
          <Link to="/app/intake">
            <button className="h-9 px-5 rounded-md bg-white text-zinc-950 font-medium text-sm hover:bg-zinc-100 hover:shadow-[0_0_20px_rgba(255,255,255,0.25)] hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] transition-all duration-200">
              Start Intake
            </button>
          </Link>
          <Link to="/app/rules">
            <button className="h-9 px-5 rounded-md bg-white/[0.04] text-zinc-200 font-medium text-sm border border-white/[0.1] hover:bg-white/[0.08] hover:border-white/20 hover:text-white hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] transition-all duration-200 backdrop-blur-md">
              View Constraints
            </button>
          </Link>
        </div>
      </div>

      {/* ─── Pipeline Overview (3 columns) ─── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {pipelineSteps.map((step, i) => (
          <motion.div
            key={step.label}
            custom={i}
            variants={cardMotionVariants}
            initial="initial"
            animate="animate"
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            whileTap={{ scale: 0.99 }}
            className="glass-box p-5 space-y-3 cursor-pointer group"
          >
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-md bg-white/[0.05] border border-white/[0.08] flex items-center justify-center group-hover:border-white/25 group-hover:bg-white/[0.1] group-hover:scale-105 transition-all duration-200">
                <step.icon size={16} className="text-zinc-300 group-hover:text-white transition-colors" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white tracking-tight group-hover:text-zinc-100 transition-colors">
                  {step.label}
                </h3>
                <p className="text-[12px] text-zinc-500 mt-0.5">Step {i + 1} of 3</p>
              </div>
            </div>
            <p className="text-[13px] text-zinc-400 leading-relaxed group-hover:text-zinc-300 transition-colors">
              {step.desc}
            </p>
          </motion.div>
        ))}
      </div>

      {/* ─── Capabilities Grid (6 items) ─── */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-300 tracking-tight mb-4">Core Capabilities</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {capabilities.map((cap, i) => (
            <motion.div
              key={cap.label}
              custom={i}
              variants={cardMotionVariants}
              initial="initial"
              animate="animate"
              whileHover={{ y: -3, scale: 1.02, transition: { duration: 0.2 } }}
              whileTap={{ scale: 0.98 }}
              className="glass-box-subtle p-4 flex flex-col items-center text-center gap-2 cursor-pointer group"
            >
              <div className="h-8 w-8 rounded-md bg-white/[0.04] border border-white/[0.06] flex items-center justify-center group-hover:border-white/20 group-hover:bg-white/[0.08] group-hover:scale-110 transition-all duration-200">
                <cap.icon size={15} className="text-zinc-400 group-hover:text-white transition-colors" />
              </div>
              <span className="text-[12px] font-medium text-zinc-200 group-hover:text-white transition-colors">{cap.label}</span>
              <span className="text-[11px] text-zinc-500 leading-tight">{cap.desc}</span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ─── System Status Row ─── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          {
            label: "Active Rules",
            value: summary?.confirmed_rules_count ?? "—",
            sub: `${summary?.draft_rules_count ?? 0} draft`,
          },
          {
            label: "Schedule Placements",
            value: schedule?.placements?.length ?? "—",
            sub: schedule?.placements ? "active" : "none loaded",
          },
          {
            label: "Chain Events",
            value: eventsData?.events?.length ?? "—",
            sub: "audit entries",
          },
          {
            label: "Solver Status",
            value: summary?.system_healthy !== false ? "Online" : "Offline",
            sub: "OR-Tools CP-SAT",
          },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            custom={i}
            variants={cardMotionVariants}
            initial="initial"
            animate="animate"
            whileHover={{ y: -2, transition: { duration: 0.2 } }}
            className="glass-box-subtle p-4 cursor-default"
          >
            <p className="text-[11px] text-zinc-500 font-medium uppercase tracking-wider">{stat.label}</p>
            <p className="text-2xl font-bold text-white mt-1 font-mono">{stat.value}</p>
            <p className="text-[11px] text-zinc-500 mt-0.5">{stat.sub}</p>
          </motion.div>
        ))}
      </div>

      {/* ─── Active Schedule + Chain Audit ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Current Active Timetable */}
        <div className="lg:col-span-2 glass-box p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Active Timetable</h3>
              <p className="text-[12px] text-zinc-500 mt-0.5">
                Schedule generated by Google OR-Tools CP-SAT solver
              </p>
            </div>
            <Link to="/app/schedule">
              <button className="h-7 px-3 rounded-md bg-white/[0.04] border border-white/[0.08] text-[12px] text-zinc-400 hover:text-white hover:bg-white/[0.08] hover:border-white/15 transition-all duration-200 flex items-center gap-1.5">
                <span>Full Grid</span>
                <ArrowRight size={11} />
              </button>
            </Link>
          </div>

          {schedule?.placements && schedule.placements.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-white/[0.06] text-zinc-500 uppercase tracking-wider">
                    <th className="py-2.5 px-3 font-medium text-[10px]">Session</th>
                    <th className="py-2.5 px-3 font-medium text-[10px]">Teacher</th>
                    <th className="py-2.5 px-3 font-medium text-[10px]">Room</th>
                    <th className="py-2.5 px-3 font-medium text-[10px]">Day</th>
                    <th className="py-2.5 px-3 font-medium text-[10px]">Slot</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {schedule.placements.slice(0, 6).map((p) => {
                    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri"];
                    const slotTimes = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"];
                    return (
                      <tr key={p.session_id} className="table-row-hover">
                        <td className="py-2.5 px-3 font-mono font-medium text-white text-[12px]">{p.session_id}</td>
                        <td className="py-2.5 px-3 text-zinc-300">{p.teacher}</td>
                        <td className="py-2.5 px-3 text-zinc-500">{p.room}</td>
                        <td className="py-2.5 px-3 text-zinc-500">{dayNames[p.day] || p.day}</td>
                        <td className="py-2.5 px-3 text-zinc-500">{slotTimes[p.slot] || p.slot}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="py-10 text-center text-[13px] text-zinc-600">
              No active schedule. Click <span className="text-zinc-400 font-medium">"Seed Demo Baseline"</span> in the navigation drawer to populate sample data.
            </div>
          )}
        </div>

        {/* ConsentLedger Audit */}
        <div className="glass-box p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">ConsentLedger</h3>
              <p className="text-[12px] text-zinc-500 mt-0.5">Audit trail</p>
            </div>
            <Link to="/app/chain-log">
              <button className="h-7 px-3 rounded-md bg-white/[0.04] border border-white/[0.08] text-[12px] text-zinc-400 hover:text-white hover:bg-white/[0.08] hover:border-white/15 transition-all duration-200 flex items-center gap-1.5">
                <span>Full Log</span>
                <ArrowRight size={11} />
              </button>
            </Link>
          </div>

          <div className="space-y-2">
            {recentEvents.length === 0 ? (
              <div className="py-10 text-center text-[13px] text-zinc-600">
                No on-chain events recorded yet.
              </div>
            ) : (
              recentEvents.map((ev, i) => (
                <div
                  key={`${ev.block}-${ev.idx}-${i}`}
                  className="p-3 rounded-md bg-white/[0.02] border border-white/[0.05] space-y-1.5 text-xs transition-all duration-200 hover:border-white/[0.1] hover:bg-white/[0.04]"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-200 text-[12px]">{ev.event}</span>
                    <span className="font-mono text-[10px] text-zinc-600">Block #{ev.block}</span>
                  </div>
                  {ev.args?.rule_id && (
                    <div className="text-[11px] text-zinc-500 flex items-center gap-1.5">
                      <span>Rule:</span>
                      <span className="font-mono text-zinc-400">{ev.args.rule_id}</span>
                    </div>
                  )}
                  {ev.args?.schedule_hash && (
                    <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500">
                      <span className="truncate max-w-[140px]">{ev.args.schedule_hash.slice(0, 14)}...</span>
                      <button
                        onClick={() => handleCopy(ev.args.schedule_hash, `dash_${i}`)}
                        className="text-zinc-500 hover:text-white transition-colors"
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

      {/* ─── Architecture Overview ─── */}
      <div className="glass-box p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white">System Architecture</h3>
        <p className="text-[13px] text-zinc-400 leading-relaxed max-w-4xl">
          GeCompose separates concerns into three layers: <span className="text-zinc-300">Gemma 4</span> handles 
          multimodal intake (voice, photos, spreadsheets) and conflict explanation. 
          <span className="text-zinc-300"> OR-Tools CP-SAT</span> performs mathematical constraint solving 
          with guaranteed feasibility. The <span className="text-zinc-300">Consent Ledger</span> records 
          cryptographically signed approvals for every schedule modification.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
          {[
            {
              title: "Gemma 4 — Translator Layer",
              items: ["Extracts rules from voice, photos & sheets", "Writes sandboxed Python parsers for Excel", "Explains conflicts in plain English"],
            },
            {
              title: "CP-SAT — Solver Layer",
              items: ["Boolean decision variables per session", "Hard constraints: no room/teacher overlap", "Minimal-change objective for re-solves"],
            },
            {
              title: "Consent Ledger — Trust Layer",
              items: ["SHA-256 hashed schedule records", "Rule-owner-only modification rights", "Immutable audit log with block indices"],
            },
          ].map((col) => (
            <div key={col.title} className="glass-box-subtle p-4 space-y-2">
              <h4 className="text-[12px] font-semibold text-zinc-200">{col.title}</h4>
              <ul className="space-y-1.5">
                {col.items.map((item) => (
                  <li key={item} className="flex items-start gap-2 text-[12px] text-zinc-500">
                    <span className="text-zinc-600 mt-0.5 shrink-0">›</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
