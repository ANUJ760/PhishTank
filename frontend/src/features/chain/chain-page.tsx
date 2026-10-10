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
  FileCheck2,
  Lock,
  Layers,
  Filter,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { ChainEvent } from "@/types/api";

export function ChainPage() {
  const [filterType, setFilterType] = useState<string>("ALL");
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({});
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const {
    data: chainData,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ["chain-events"],
    queryFn: api.chainEvents,
    refetchInterval: 15000,
  });

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

  const getEventBadge = (eventName: string) => {
    switch (eventName) {
      case "RuleRegistered":
        return <Badge variant="outline" className="text-blue-500 border-blue-500/30 bg-blue-500/10"><Lock className="w-3 h-3 mr-1" /> RuleRegistered</Badge>;
      case "RelaxationApproved":
        return <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10"><ShieldCheck className="w-3 h-3 mr-1" /> RelaxationApproved</Badge>;
      case "ScheduleAnchored":
        return <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10"><FileCheck2 className="w-3 h-3 mr-1" /> ScheduleAnchored</Badge>;
      default:
        return <Badge variant="secondary">{eventName}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Link2 className="w-6 h-6 text-primary" />
            ConsentLedger Audit Log
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Immutable on-chain event stream queried directly from the ConsentLedger smart contract on local Anvil node.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoading || isRefetching}
            className="gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh Log
          </Button>
        </div>
      </div>

      {/* Info notice */}
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-xs text-muted-foreground leading-relaxed flex items-start gap-3">
        <ShieldCheck className="w-4 h-4 text-primary shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-foreground">Zero-Knowledge & Hash Privacy Guarantee:</span> The ConsentLedger contract only stores cryptographic commitments (<code className="font-mono text-primary">rule_hash</code>, <code className="font-mono text-primary">schedule_hash</code>) and authorized institutional signer addresses. PII, names, audio, and draft timetable schedules never leak on-chain.
        </div>
      </div>

      {/* Filters & Metrics */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 bg-muted/40 p-1 rounded-lg border border-border">
          <span className="text-xs text-muted-foreground px-2 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Event:
          </span>
          {["ALL", "RuleRegistered", "RelaxationApproved", "ScheduleAnchored"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`text-xs px-2.5 py-1 rounded-md font-medium transition-all ${
                filterType === type
                  ? "bg-card text-foreground shadow-xs border border-border"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {type === "ALL" ? "All Events" : type}
            </button>
          ))}
        </div>

        <div className="text-xs text-muted-foreground flex items-center gap-4">
          <span>Total Recorded Events: <strong className="text-foreground">{events.length}</strong></span>
          <span>Filtered: <strong className="text-foreground">{filteredEvents.length}</strong></span>
        </div>
      </div>

      {/* Event list */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="p-12 text-center text-muted-foreground text-sm flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-primary" />
            Querying Anvil block headers and contract logs...
          </div>
        ) : filteredEvents.length === 0 ? (
          <Card className="p-12 text-center text-muted-foreground">
            <Layers className="w-8 h-8 mx-auto mb-2 text-muted-foreground/60" />
            <p className="text-sm font-medium text-foreground">No On-Chain Events Recorded</p>
            <p className="text-xs mt-1">
              Events are emitted when rules are confirmed, relaxation options are signed, or final timetables are published.
            </p>
          </Card>
        ) : (
          filteredEvents.map((ev, i) => {
            const isExpanded = !!expandedIndices[i];
            const eventPayloadStr = JSON.stringify(ev.args, null, 2);

            return (
              <motion.div
                key={`${ev.block}-${ev.idx}-${i}`}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.15, delay: i * 0.02 }}
              >
                <Card className="hover:border-border/80 transition-all">
                  <div className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => toggleExpand(i)}
                        className="p-1 rounded hover:bg-muted text-muted-foreground transition-colors"
                        title={isExpanded ? "Collapse payload" : "Expand payload"}
                      >
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>

                      <div className="flex flex-wrap items-center gap-2">
                        {getEventBadge(ev.event)}
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border">
                          Block #{ev.block}
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">
                          LogIdx #{ev.idx}
                        </span>
                      </div>
                    </div>

                    {/* Quick preview of key args */}
                    <div className="flex items-center gap-3 text-xs">
                      {ev.args?.rule_id && (
                        <div className="flex items-center gap-1 font-mono text-xs bg-muted/60 px-2 py-0.5 rounded border border-border">
                          <span className="text-muted-foreground">Rule:</span>
                          <span className="font-semibold text-foreground">{ev.args.rule_id}</span>
                        </div>
                      )}
                      {ev.args?.rule_hash && (
                        <button
                          onClick={() => handleCopy(ev.args.rule_hash, `rule_hash_${i}`)}
                          className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted px-2 py-0.5 rounded transition-colors"
                          title="Click to copy hash"
                        >
                          <span>{ev.args.rule_hash.slice(0, 10)}...</span>
                          {copiedKey === `rule_hash_${i}` ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                      {ev.args?.schedule_hash && (
                        <button
                          onClick={() => handleCopy(ev.args.schedule_hash, `sched_hash_${i}`)}
                          className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted px-2 py-0.5 rounded transition-colors"
                          title="Click to copy schedule hash"
                        >
                          <span>{ev.args.schedule_hash.slice(0, 10)}...</span>
                          {copiedKey === `sched_hash_${i}` ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                        </button>
                      )}
                      {ev.args?.approver && (
                        <button
                          onClick={() => handleCopy(ev.args.approver, `approver_${i}`)}
                          className="flex items-center gap-1 font-mono text-[11px] text-muted-foreground hover:text-foreground bg-muted/40 hover:bg-muted px-2 py-0.5 rounded transition-colors"
                          title="Click to copy approver address"
                        >
                          <span className="text-muted-foreground">by:</span>
                          <span>{ev.args.approver.slice(0, 8)}...</span>
                          {copiedKey === `approver_${i}` ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
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
                        className="border-t border-border bg-muted/20 px-4 py-3"
                      >
                        <div className="flex items-center justify-between pb-2">
                          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                            Decoded Event Arguments
                          </span>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 px-2 text-xs gap-1"
                            onClick={() => handleCopy(eventPayloadStr, `raw_${i}`)}
                          >
                            {copiedKey === `raw_${i}` ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                            Copy Raw JSON
                          </Button>
                        </div>
                        <pre className="text-xs font-mono bg-card p-3 rounded-lg border border-border overflow-x-auto text-foreground leading-relaxed max-h-60">
                          {eventPayloadStr}
                        </pre>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </Card>
              </motion.div>
            );
          })
        )}
      </div>
    </div>
  );
}
