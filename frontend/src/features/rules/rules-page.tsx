import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Rule, RuleStatus } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Check,
  X,
  Search,
  Filter,
  Lock,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
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
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">Constraints & Rule Ledger</h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Institutional rules governing teacher availability, room requirements, pinned labs, and qualifications.
        </p>
      </div>

      {/* Filter Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-muted border border-border text-xs select-none">
          {["all", "confirmed", "draft", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3 py-1 rounded-md capitalize transition-colors ${
                selectedStatus === st
                  ? "bg-background text-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search rules..."
            className="pl-8 text-xs h-8"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Rules Table */}
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead>
                    <tr className="border-b border-border bg-muted/30 text-muted-foreground">
                      <th className="py-2.5 px-4 font-medium">ID</th>
                      <th className="py-2.5 px-4 font-medium">Type</th>
                      <th className="py-2.5 px-4 font-medium">Owner</th>
                      <th className="py-2.5 px-4 font-medium">Parameters</th>
                      <th className="py-2.5 px-4 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {isLoading ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">
                          Loading constraints ledger...
                        </td>
                      </tr>
                    ) : filteredRules.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-muted-foreground">
                          No matching constraints found.
                        </td>
                      </tr>
                    ) : (
                      filteredRules.map((rule) => {
                        const isSelected = activeRule?.id === rule.id;
                        return (
                          <tr
                            key={rule.id}
                            onClick={() => setActiveRule(rule)}
                            className={`cursor-pointer transition-colors ${
                              isSelected ? "bg-muted font-medium" : "hover:bg-muted/40"
                            }`}
                          >
                            <td className="py-2.5 px-4 font-bold text-foreground">{rule.id}</td>
                            <td className="py-2.5 px-4 text-muted-foreground capitalize">
                              {rule.type.replace("_", " ")}
                            </td>
                            <td className="py-2.5 px-4 text-foreground">{rule.owner}</td>
                            <td className="py-2.5 px-4 font-mono text-[11px] text-muted-foreground max-w-xs truncate">
                              {JSON.stringify(rule.params)}
                            </td>
                            <td className="py-2.5 px-4">
                              <Badge
                                variant={
                                  rule.status === "confirmed"
                                    ? "success"
                                    : rule.status === "draft"
                                    ? "warning"
                                    : "destructive"
                                }
                              >
                                {rule.status}
                              </Badge>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Selected Rule Inspection & Action Panel */}
        <div>
          {activeRule ? (
            <Card className="sticky top-6">
              <CardHeader className="border-b border-border pb-3">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-base text-foreground">{activeRule.id}</span>
                  <Badge
                    variant={
                      activeRule.status === "confirmed"
                        ? "success"
                        : activeRule.status === "draft"
                        ? "warning"
                        : "destructive"
                    }
                  >
                    {activeRule.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground capitalize mt-0.5">
                  {activeRule.type.replace("_", " ")}
                </p>
              </CardHeader>
              <CardContent className="pt-4 space-y-4 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-1">
                    Rule Owner
                  </span>
                  <div className="flex items-center gap-1.5 text-foreground font-medium">
                    <span>{activeRule.owner}</span>
                    {activeRule.status === "confirmed" && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Lock size={11} /> Locked on-chain
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-1">
                    Validated Parameters
                  </span>
                  <pre className="p-2.5 rounded-lg bg-muted border border-border text-[11px] font-mono whitespace-pre-wrap text-foreground">
                    {JSON.stringify(activeRule.params, null, 2)}
                  </pre>
                </div>

                {activeRule.evidence && activeRule.evidence.length > 0 && (
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-1">
                      Evidence Trail
                    </span>
                    <div className="space-y-1">
                      {activeRule.evidence.map((ev, i) => (
                        <div key={i} className="p-2 rounded bg-muted/40 border border-border text-[11px]">
                          <span className="font-medium text-foreground capitalize">{ev.kind}:</span> {ev.ref}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {activeRule.status === "draft" && (
                  <div className="pt-2 flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => confirmMutation.mutate(activeRule.id)}
                      isLoading={confirmMutation.isPending}
                      className="w-full gap-1.5"
                    >
                      <Check size={14} /> Confirm & Anchor
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => rejectMutation.mutate(activeRule.id)}
                      isLoading={rejectMutation.isPending}
                      className="text-destructive hover:bg-destructive/10"
                    >
                      <X size={14} /> Reject
                    </Button>
                  </div>
                )}

                {activeRule.status === "confirmed" && (
                  <div className="p-3 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800 text-[11px] flex items-center gap-2">
                    <ShieldCheck size={14} className="shrink-0 text-emerald-600" />
                    <span>Cryptographically anchored in local Ethereum ConsentLedger.</span>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="h-64 flex items-center justify-center text-center p-6 text-xs text-muted-foreground">
              Select a rule from the ledger to inspect parameters, on-chain status, and actions.
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
