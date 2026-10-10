import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Rule, RuleStatus } from "@/types/api";
import {
  Check,
  X,
  Search,
  Filter,
  Lock,
  ExternalLink,
} from "lucide-react";

const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const SLOT_WINDOWS: Record<number, string> = {
  0: "09:00 - 10:00",
  1: "10:00 - 11:00",
  2: "11:00 - 12:00",
  3: "13:00 - 14:00",
  4: "14:00 - 15:00",
  5: "15:00 - 16:00",
};

function formatSlots(slots: number[] = []): string {
  if (!slots || slots.length === 0) return "Unspecified";
  const sorted = [...slots].sort((a, b) => a - b);
  if (sorted.length === 3 && sorted[0] === 0 && sorted[2] === 2) return "Morning (09:00 - 12:00)";
  if (sorted.length === 3 && sorted[0] === 3 && sorted[2] === 5) return "Afternoon (13:00 - 16:00)";
  if (sorted.length === 6) return "Full Day (09:00 - 16:00)";
  if (sorted.length === 1) return SLOT_WINDOWS[sorted[0]] || `Slot ${sorted[0]}`;
  const start = (SLOT_WINDOWS[sorted[0]] || `Slot ${sorted[0]}`).split(" - ")[0];
  const end = (SLOT_WINDOWS[sorted[sorted.length - 1]] || `Slot ${sorted[sorted.length - 1]}`).split(" - ")[1] || "";
  return `${start} - ${end} (Slots ${sorted.join(", ")})`;
}

function formatRuleHumanSummary(rule: Rule): string {
  const p = rule.params || {};
  const dayName = typeof p.day === "number" ? (DAY_NAMES[p.day] || `Day ${p.day}`) : "All Days";
  const timeWin = p.slots ? formatSlots(p.slots) : "All Hours";

  if (rule.type === "teacher_unavailable") {
    return `${p.teacher || "Faculty"} cannot be scheduled on ${dayName} during ${timeWin}.`;
  }
  if (rule.type === "room_unavailable") {
    return `${p.room || "Room"} is offline for maintenance on ${dayName} during ${timeWin}.`;
  }
  if (rule.type === "pin_session") {
    return `Locks session ${p.session_id || "Course"} to ${dayName} during ${timeWin}.`;
  }
  if (rule.type === "only_qualified") {
    return `Session ${p.session_id || "Course"} must only be instructed by certified faculty: ${(p.teachers || []).join(", ") || "Qualified instructor"}.`;
  }
  return Object.entries(p).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" • ") || "Operational constraint.";
}

export function RulesPage() {
  const queryClient = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeRule, setActiveRule] = useState<Rule | null>(null);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["rules", selectedStatus],
    queryFn: () => api.rules.list(selectedStatus === "all" ? undefined : selectedStatus),
  });

  const confirmMutation = useMutation({
    mutationFn: (ruleId: string) => api.rules.confirm(ruleId),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      setActiveRule(updated);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (ruleId: string) => api.rules.reject(ruleId),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["rules"] });
      setActiveRule(updated);
    },
  });

  const filteredRules = rules.filter((r) => {
    const q = searchQuery.toLowerCase();
    return (
      r.id.toLowerCase().includes(q) ||
      r.owner.toLowerCase().includes(q) ||
      r.type.toLowerCase().includes(q) ||
      JSON.stringify(r.params).toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 text-left pb-12">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white">Constraints & Rule Ledger</h2>
        <p className="text-xs text-zinc-400 mt-0.5">
          Institutional rules governing teacher availability, room requirements, pinned labs, and qualifications.
        </p>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 rounded-md bg-zinc-900 border border-white/10 text-xs select-none">
          {["all", "confirmed", "draft", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3.5 py-1 rounded-md capitalize transition-all text-xs ${
                selectedStatus === st
                  ? "bg-white text-zinc-950 font-medium shadow-xs"
                  : "text-zinc-400 hover:text-white"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rules..."
            className="w-full pl-9 pr-3 h-8 rounded-md bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rules Table */}
        <div className="lg:col-span-2 glass-box p-6 space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-white/5 text-zinc-400">
                  <th className="py-2.5 px-3 font-semibold">Rule ID</th>
                  <th className="py-2.5 px-3 font-semibold">Type</th>
                  <th className="py-2.5 px-3 font-semibold">Owner</th>
                  <th className="py-2.5 px-3 font-semibold">Status</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-500">
                      Loading rules ledger...
                    </td>
                  </tr>
                ) : filteredRules.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-zinc-500">
                      No rules found for selected filter.
                    </td>
                  </tr>
                ) : (
                  filteredRules.map((rule) => {
                    const isSelected = activeRule?.id === rule.id;
                    return (
                      <tr
                        key={rule.id}
                        onClick={() => setActiveRule(rule)}
                        className={`hover:bg-white/[0.02] cursor-pointer transition-colors ${
                          isSelected ? "bg-white/[0.06]" : ""
                        }`}
                      >
                        <td className="py-3 px-3 font-mono font-bold text-white">{rule.id}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-[10px] font-mono">
                            {rule.type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-zinc-300">{rule.owner}</td>
                        <td className="py-3 px-3">
                          <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-[10px] capitalize">
                            {rule.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                            {rule.status === "draft" && (
                              <>
                                <button
                                  onClick={() => confirmMutation.mutate(rule.id)}
                                  className="h-6 px-2.5 rounded-md bg-white text-zinc-950 font-medium text-[11px] hover:bg-zinc-200 transition-all flex items-center gap-1"
                                  title="Confirm and register on ConsentLedger"
                                >
                                  <Check size={11} />
                                  <span>Confirm</span>
                                </button>
                                <button
                                  onClick={() => rejectMutation.mutate(rule.id)}
                                  className="h-6 px-2.5 rounded-md bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white text-[11px] transition-all flex items-center gap-1"
                                  title="Reject rule"
                                >
                                  <X size={11} />
                                </button>
                              </>
                            )}
                            {rule.status === "confirmed" && (
                              <span className="text-[11px] text-zinc-400 font-mono flex items-center gap-1">
                                <Lock size={11} /> Anchored
                              </span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Rule Review Detail Panel */}
        <div className="glass-box p-6 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-white text-sm font-semibold">Rule Detail & Evidence</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Inspect provenance, natural evidence, and cryptographic hash
            </p>
          </div>

          {activeRule ? (
            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between p-3 rounded-md bg-white/[0.02] border border-white/10">
                <span className="font-mono text-sm font-bold text-white">{activeRule.id}</span>
                <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-[11px]">
                  {activeRule.status.toUpperCase()}
                </span>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-zinc-400 font-medium">Owner Identity</span>
                <div className="p-2.5 rounded-md bg-white/[0.02] border border-white/5 text-zinc-200 font-medium">
                  {activeRule.owner}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-zinc-400 font-medium">Extracted Natural Evidence</span>
                <div className="p-3 rounded-md bg-white/[0.02] border border-white/5 text-zinc-300 italic text-[11px] leading-relaxed">
                  &quot;{Array.isArray(activeRule.evidence) ? activeRule.evidence.map((e: any) => e.ref || e.kind || "Evidence record").join(", ") : String(activeRule.evidence || "No natural evidence recorded")}&quot;
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[11px] text-zinc-400 font-medium">Constraint Parameters</span>
                <div className="p-3.5 rounded-lg bg-zinc-900 border border-white/10 space-y-3">
                  <div className="text-xs font-semibold text-white leading-relaxed">
                    {formatRuleHumanSummary(activeRule)}
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/5 text-[11px]">
                    {activeRule.params.teacher && (
                      <div className="p-2 rounded bg-black/50 border border-white/5">
                        <span className="text-zinc-500 block text-[10px]">Faculty</span>
                        <span className="font-semibold text-zinc-200">{activeRule.params.teacher}</span>
                      </div>
                    )}
                    {activeRule.params.room && (
                      <div className="p-2 rounded bg-black/50 border border-white/5">
                        <span className="text-zinc-500 block text-[10px]">Facility</span>
                        <span className="font-semibold text-zinc-200">{activeRule.params.room}</span>
                      </div>
                    )}
                    {activeRule.params.session_id && (
                      <div className="p-2 rounded bg-black/50 border border-white/5">
                        <span className="text-zinc-500 block text-[10px]">Session</span>
                        <span className="font-semibold text-zinc-200">{activeRule.params.session_id}</span>
                      </div>
                    )}
                    {typeof activeRule.params.day === "number" && (
                      <div className="p-2 rounded bg-black/50 border border-white/5">
                        <span className="text-zinc-500 block text-[10px]">Day</span>
                        <span className="font-semibold text-zinc-200">{DAY_NAMES[activeRule.params.day] || `Day ${activeRule.params.day}`}</span>
                      </div>
                    )}
                    {activeRule.params.slots && (
                      <div className="p-2 rounded bg-black/50 border border-white/5 col-span-2">
                        <span className="text-zinc-500 block text-[10px]">Time Window</span>
                        <span className="font-semibold text-zinc-200">{formatSlots(activeRule.params.slots)}</span>
                      </div>
                    )}
                    {activeRule.params.teachers && (
                      <div className="p-2 rounded bg-black/50 border border-white/5 col-span-2">
                        <span className="text-zinc-500 block text-[10px]">Certified Faculty</span>
                        <span className="font-semibold text-zinc-200">{activeRule.params.teachers.join(", ")}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {activeRule.status === "draft" && (
                <div className="pt-2 flex items-center gap-2">
                  <button
                    onClick={() => confirmMutation.mutate(activeRule.id)}
                    className="flex-1 h-8 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center justify-center gap-1.5"
                  >
                    <Check size={13} />
                    <span>Confirm Rule in Ledger</span>
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(activeRule.id)}
                    className="h-8 px-4 rounded-md bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white text-xs transition-all"
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-xs text-zinc-500">
              Select any rule from the ledger to inspect its natural language provenance and parameters.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
