import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Link2,
  RefreshCw,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  Lock,
  Layers,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import { ChainEvent, LedgerVerifyResult } from "@/types/api";

export function ChainPage() {
  const [filterType, setFilterType] = useState<string>("ALL");
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<LedgerVerifyResult | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);

  const {
    data: chainData,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["chain-events"],
    queryFn: () => api.ledger.events(),
    refetchInterval: 15000,
  });

  const handleVerifyIntegrity = async () => {
    setIsVerifying(true);
    try {
      const res = await api.ledger.verify();
      setVerifyResult(res);
      if (res.valid) {
        toast.success(`Ledger Integrity Intact (${res.total_entries} entries verified)`);
      } else {
        toast.error(`Tampering detected: ${res.reason || res.message}`);
      }
    } catch (e: any) {
      toast.error(`Verification error: ${e.message || "Failed to verify ledger"}`);
    } finally {
      setIsVerifying(false);
    }
  };

  const events: ChainEvent[] = chainData?.events || [];

  const filteredEvents = events.filter((ev) => {
    if (filterType === "ALL") return true;
    return ev.event === filterType;
  });

  const toggleExpand = (idx: number) => {
    setExpandedIndices((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    toast.success("Copied to clipboard");
    setTimeout(() => {
      setCopiedKey(null);
    }, 2000);
  };

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Link2 className="w-5 h-5 text-zinc-300" />
            Cryptographic Audit Ledger
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Immutable event stream logged with SHA-256 state commitments and role authorizations.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleVerifyIntegrity}
            disabled={isVerifying}
            className="h-8 px-4 rounded-md bg-white text-zinc-950 hover:bg-zinc-200 font-medium text-xs transition-all flex items-center gap-1.5 self-start sm:self-auto shadow-sm active:scale-[0.98] disabled:opacity-50"
          >
            <ShieldCheck className={`w-3.5 h-3.5 ${isVerifying ? "animate-spin" : ""}`} />
            <span>Verify Integrity</span>
          </button>

          <button
            onClick={() => refetch()}
            disabled={isLoading || isRefetching}
            className="h-8 px-4 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white font-medium text-xs transition-all flex items-center gap-1.5 self-start sm:self-auto"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            <span>Refresh Log</span>
          </button>
        </div>
      </div>

      {verifyResult && (
        <div
          className={`p-4 rounded-lg border text-xs leading-relaxed flex items-center justify-between ${
            verifyResult.valid
              ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
              : "border-rose-500/30 bg-rose-950/20 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>{verifyResult.message}</span>
          </div>
          {verifyResult.latest_hash && (
            <span className="font-mono text-[10px] opacity-75 hidden sm:inline">
              Latest SHA-256: {verifyResult.latest_hash.slice(0, 16)}...
            </span>
          )}
        </div>
      )}

      {/* Info notice in glass box */}
      <div className="p-4 rounded-lg border border-white/10 bg-zinc-900/80 backdrop-blur-xl text-xs text-zinc-400 leading-relaxed flex items-start gap-3">
        <ShieldCheck className="w-4 h-4 text-zinc-300 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-white">Cryptographic State & Hash Privacy Guarantee:</span> The Audit Ledger stores cryptographic commitments (<code className="font-mono text-zinc-200">rule_hash</code>, <code className="font-mono text-zinc-200">schedule_hash</code>) and authorized institutional actor IDs. PII, names, audio, and draft timetable schedules never leak in plaintext.
        </div>
      </div>

      {/* Filters & Metrics */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 rounded-md bg-zinc-900 border border-white/10 text-xs">
          <span className="text-xs text-zinc-400 px-2 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Event:
          </span>
          {["ALL", "RuleRegistered", "RelaxationApproved", "ScheduleAnchored"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`text-xs px-3 py-1 rounded-md font-medium transition-all ${
                filterType === type
                  ? "bg-white text-zinc-950 font-medium shadow-xs"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              {type === "ALL" ? "All Events" : type}
            </button>
          ))}
        </div>

        <div className="text-xs text-zinc-400 flex items-center gap-4">
          <span>Total Recorded Events: <strong className="text-white font-mono">{events.length}</strong></span>
          <span>Filtered: <strong className="text-white font-mono">{filteredEvents.length}</strong></span>
        </div>
      </div>

      {/* Event list in glass cards */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="p-12 text-center text-zinc-500 text-xs flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5 animate-spin text-zinc-400" />
            Querying audit ledger log entries...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="glass-box p-12 text-center text-zinc-500">
            <Layers className="w-7 h-7 mx-auto mb-2 text-zinc-600" />
            <p className="text-xs font-medium text-white">No Audit Events Recorded</p>
            <p className="text-[11px] mt-1">
              Events are emitted when rules are confirmed, relaxation options are authorized, or final timetables are published.
            </p>
          </div>
        ) : (
          filteredEvents.map((ev, i) => {
            const isExpanded = !!expandedIndices[i];
            const eventPayloadStr = JSON.stringify(ev.args, null, 2);

            return (
              <div
                key={`${ev.block}-${ev.idx}-${i}`}
                className="glass-box p-4 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleExpand(i)}
                      className="p-1 rounded-lg hover:bg-white/5 text-zinc-400 transition-colors"
                      title={isExpanded ? "Collapse payload" : "Expand payload"}
                    >
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>

                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-xs font-mono font-medium border border-white/5">
                        {ev.event}
                      </span>
                      <span className="font-mono text-xs px-2 py-0.5 rounded-md bg-white/[0.04] text-zinc-400 border border-white/5">
                        Seq #{ev.seq ?? ev.block}
                      </span>
                      {ev.entry_hash ? (
                        <span className="font-mono text-xs text-zinc-500">
                          Hash: {ev.entry_hash.slice(0, 10)}...
                        </span>
                      ) : (
                        <span className="font-mono text-xs text-zinc-500">
                          Entry #{ev.idx}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Quick preview of key args */}
                  <div className="flex items-center gap-3 text-xs">
                    {ev.args?.rule_id && (
                      <div className="flex items-center gap-1 font-mono text-xs bg-white/[0.03] px-2 py-0.5 rounded-md border border-white/5">
                        <span className="text-zinc-500">Rule:</span>
                        <span className="font-medium text-white">{ev.args.rule_id}</span>
                      </div>
                    )}
                    {ev.args?.rule_hash && (
                      <button
                        onClick={() => handleCopy(ev.args.rule_hash, `rule_hash_${i}`)}
                        className="flex items-center gap-1 font-mono text-[11px] text-zinc-400 hover:text-white bg-white/[0.02] hover:bg-white/5 px-2 py-0.5 rounded-md border border-white/5 transition-colors"
                        title="Click to copy hash"
                      >
                        <span>{ev.args.rule_hash.slice(0, 10)}...</span>
                        {copiedKey === `rule_hash_${i}` ? <Check className="w-3 h-3 text-white" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                    {ev.args?.schedule_hash && (
                      <button
                        onClick={() => handleCopy(ev.args.schedule_hash, `sched_hash_${i}`)}
                        className="flex items-center gap-1 font-mono text-[11px] text-zinc-400 hover:text-white bg-white/[0.02] hover:bg-white/5 px-2 py-0.5 rounded-md border border-white/5 transition-colors"
                        title="Click to copy schedule hash"
                      >
                        <span>{ev.args.schedule_hash.slice(0, 10)}...</span>
                        {copiedKey === `sched_hash_${i}` ? <Check className="w-3 h-3 text-white" /> : <Copy className="w-3 h-3" />}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expandable JSON detail */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="border-t border-white/5 pt-3"
                    >
                      <div className="flex items-center justify-between pb-2">
                        <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">
                          Decoded Event Arguments
                        </span>
                        <button
                          className="h-6 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white text-[11px] flex items-center gap-1"
                          onClick={() => handleCopy(eventPayloadStr, `raw_${i}`)}
                        >
                          {copiedKey === `raw_${i}` ? <Check className="w-3 h-3 text-white" /> : <Copy className="w-3 h-3" />}
                          <span>Copy Raw JSON</span>
                        </button>
                      </div>
                      <pre className="text-xs font-mono bg-black p-3 rounded-md border border-white/10 overflow-x-auto text-zinc-300 leading-relaxed max-h-60">
                        {eventPayloadStr}
                      </pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
