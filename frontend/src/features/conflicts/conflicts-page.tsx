import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Conflict, Explanation, RelaxOption } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertTriangle,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  Flame,
  CheckCircle2,
  Users,
  Lock,
} from "lucide-react";

export function ConflictsPage() {
  const queryClient = useQueryClient();
  const [conflict, setConflict] = useState<Conflict | null>(null);
  const [explanation, setExplanation] = useState<Explanation | null>(null);
  const [isInjecting, setIsInjecting] = useState(false);

  // Check current solve state
  const { data: solveData, refetch: reSolve } = useQuery({
    queryKey: ["solve-check"],
    queryFn: async () => {
      const res = await api.solve(true);
      if (res.status === "infeasible" && res.conflict) {
        setConflict(res.conflict);
      } else {
        setConflict(null);
      }
      return res;
    },
  });

  const explainMutation = useMutation({
    mutationFn: (c: Conflict) => api.conflicts.explain(c),
    onSuccess: (exp: Explanation) => {
      setExplanation(exp);
    },
  });

  const handleInjectR3 = async () => {
    setIsInjecting(true);
    try {
      // Ingest R3: Prof. Rao unavailable Mon 0-2
      const text = "Prof. Rao is unavailable on Monday morning between 09:00 and 12:00.";
      const rules = await api.intake.text(text);
      if (rules.length > 0) {
        await api.rules.confirm(rules[0].id);
      }
      queryClient.invalidateQueries();
      const res = await reSolve();
      if (res.data?.status === "infeasible" && res.data.conflict) {
        setConflict(res.data.conflict);
      }
    } finally {
      setIsInjecting(false);
    }
  };

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Conflict Studio</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Identify mathematically impossible constraint intersections, isolate minimal conflict cores, and explore verified relaxations.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleInjectR3}
          isLoading={isInjecting}
          className="gap-1.5 text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50 border-rose-200"
        >
          <Flame size={13} />
          <span>Inject Demo Clash (Rule R3)</span>
        </Button>
      </div>

      {conflict ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Conflict Core Breakdown */}
          <div className="space-y-6">
            <Card className="border-rose-200 dark:border-rose-900 bg-rose-50/20">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={16} className="text-rose-600" />
                  <CardTitle className="text-rose-900 dark:text-rose-200 text-sm font-semibold">
                    Minimal Infeasible Core
                  </CardTitle>
                </div>
                <p className="text-xs text-rose-700 dark:text-rose-300">
                  CP-SAT proved that no weekly timetable can satisfy these constraints simultaneously.
                </p>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-1">
                    Conflicting Rule IDs
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {conflict.rule_ids.map((id) => (
                      <Badge key={id} variant="destructive" className="font-mono text-xs">
                        {id}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-1">
                    Involved Rule Owners
                  </span>
                  <div className="flex items-center gap-1.5 text-foreground font-medium">
                    <Users size={14} className="text-muted-foreground" />
                    <span>{Array.from(new Set(conflict.owners)).join(", ")}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <Button
                    size="sm"
                    onClick={() => explainMutation.mutate(conflict)}
                    isLoading={explainMutation.isPending}
                    className="w-full gap-1.5 text-xs"
                  >
                    <Sparkles size={13} />
                    <span>Explain & Propose Verified Options</span>
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <h3 className="text-xs font-semibold text-foreground">Why Multi-Party Consent?</h3>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p>
                  No individual coordinator or AI model has unilateral authority to override Prof. Rao&apos;s unavailability or the Dean&apos;s qualification policy.
                </p>
                <p>
                  Every proposed relaxation must be approved on-chain by the verified rule owner before it can be applied to the schedule.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Right 2 Cols: Proposed Relaxations */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader className="border-b border-border pb-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    <ShieldCheck size={15} className="text-primary" />
                    Solver-Verified Relaxation Options
                  </h3>
                  {explanation && (
                    <Badge variant="success">{explanation.options.length} Verified Options</Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground">
                  Options verified by CP-SAT to guarantee a feasible schedule once approved.
                </p>
              </CardHeader>
              <CardContent className="pt-5 space-y-4">
                {explanation ? (
                  <>
                    <div className="p-3 rounded-lg bg-muted border border-border text-xs text-muted-foreground">
                      <strong className="text-foreground block mb-1">AI Explanation Summary:</strong>
                      {explanation.summary}
                    </div>

                    <div className="space-y-3">
                      {explanation.options.map((opt) => (
                        <div
                          key={opt.id}
                          className="p-4 rounded-xl border border-border bg-card hover:border-primary/40 transition-colors space-y-2.5 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-foreground text-sm">{opt.id}</span>
                              <span className="text-muted-foreground">
                                Modifies rule <strong className="text-foreground">{opt.rule_id}</strong>
                              </span>
                            </div>
                            <Badge variant="success">Feasibility Verified</Badge>
                          </div>

                          <p className="text-xs text-foreground font-medium">{opt.description}</p>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1">
                            <div className="p-2 rounded bg-muted border border-border">
                              <span className="text-muted-foreground block text-[10px]">Required Approver:</span>
                              <span className="font-semibold text-foreground">{opt.approver}</span>
                            </div>
                            <div className="p-2 rounded bg-muted border border-border font-mono truncate">
                              <span className="text-muted-foreground block text-[10px]">Option Digest:</span>
                              <span className="text-foreground">{opt.option_hash}</span>
                            </div>
                          </div>

                          <div className="pt-2 flex justify-end">
                            <Link to="/app/approvals">
                              <Button size="sm" className="gap-1 text-xs h-8">
                                <span>Sign & Approve in Ledger</span>
                                <ArrowRight size={13} />
                              </Button>
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="py-16 text-center text-xs text-muted-foreground space-y-2">
                    <Sparkles size={24} className="mx-auto text-muted-foreground/40 mb-2" />
                    <p>Click &quot;Explain & Propose Verified Options&quot; to synthesize mathematical relaxations.</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      ) : (
        <Card className="p-12 text-center text-xs text-muted-foreground space-y-3">
          <CheckCircle2 size={32} className="mx-auto text-emerald-500 mb-2" />
          <h3 className="text-base font-semibold text-foreground">Rule Base is Fully Feasible</h3>
          <p className="max-w-md mx-auto">
            The current active constraints can be completely satisfied without collisions. Click &quot;Inject Demo Clash&quot; above to simulate the R1-R2-R3 conflict scenario.
          </p>
        </Card>
      )}
    </div>
  );
}
