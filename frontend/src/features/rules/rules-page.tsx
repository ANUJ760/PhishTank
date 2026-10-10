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
        <div className="flex items-center gap-1.5 p-1 rounded-full bg-zinc-900 border border-white/10 text-xs select-none">
          {["all", "confirmed", "draft", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3.5 py-1 rounded-full capitalize transition-all text-xs ${
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
            className="w-full pl-9 pr-3 h-8 rounded-full bg-zinc-900 border border-white/10 text-xs text-white placeholder:text-zinc-500 focus:outline-none focus:border-white/20"
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
                          <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[10px] font-mono">
                            {rule.type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-zinc-300">{rule.owner}</td>
                        <td className="py-3 px-3">
                          <span className="px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[10px] capitalize">
                            {rule.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                            {rule.status === "draft" && (
                              <>
                                <button
                                  onClick={() => confirmMutation.mutate(rule.id)}
                                  className="h-6 px-2.5 rounded-full bg-white text-zinc-950 font-medium text-[11px] hover:bg-zinc-200 transition-all flex items-center gap-1"
                                  title="Confirm and register on ConsentLedger"
                                >
                                  <Check size={11} />
                                  <span>Confirm</span>
                                </button>
                                <button
                                  onClick={() => rejectMutation.mutate(rule.id)}
                                  className="h-6 px-2.5 rounded-full bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white text-[11px] transition-all flex items-center gap-1"
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
              Inspect provenance, natural evidence, and on-chain hash
            </p>
          </div>

          {activeRule ? (
            <div className="space-y-4 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/10">
                <span className="font-mono text-sm font-bold text-white">{activeRule.id}</span>
                <span className="px-2.5 py-0.5 rounded-full bg-zinc-800 text-zinc-300 text-[11px]">
                  {activeRule.status.toUpperCase()}
                </span>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-zinc-400 font-medium">Owner Identity</span>
                <div className="p-2.5 rounded-xl bg-white/[0.02] border border-white/5 text-zinc-200 font-medium">
                  {activeRule.owner}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-zinc-400 font-medium">Extracted Natural Evidence</span>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 text-zinc-300 italic text-[11px] leading-relaxed">
                  &quot;{Array.isArray(activeRule.evidence) ? activeRule.evidence.map((e: any) => e.ref || e.kind || JSON.stringify(e)).join(", ") : String(activeRule.evidence || "No natural evidence recorded")}&quot;
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] text-zinc-400 font-medium">Parsed Parameters (JSON)</span>
                <pre className="p-3 rounded-xl bg-black border border-white/10 text-zinc-300 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(activeRule.params, null, 2)}
                </pre>
              </div>

              {activeRule.status === "draft" && (
                <div className="pt-2 flex items-center gap-2">
                  <button
                    onClick={() => confirmMutation.mutate(activeRule.id)}
                    className="flex-1 h-8 rounded-full bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center justify-center gap-1.5"
                  >
                    <Check size={13} />
                    <span>Confirm Rule On-Chain</span>
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(activeRule.id)}
                    className="h-8 px-4 rounded-full bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white text-xs transition-all"
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
