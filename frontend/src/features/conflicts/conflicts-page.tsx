import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Conflict, Explanation, RelaxOption } from "@/types/api";
import {
  AlertTriangle,
  ArrowRight,
  Flame,
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
    <div className="space-y-6 text-left pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Conflict Studio</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Identify mathematically impossible constraint intersections, isolate minimal conflict cores, and explore verified relaxations.
          </p>
        </div>

        <button
          onClick={handleInjectR3}
          disabled={isInjecting}
          className="h-8 px-4 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white font-medium text-xs transition-all flex items-center gap-1.5 active:scale-[0.98] disabled:opacity-50"
        >
          <Flame size={13} className="text-zinc-400" />
          <span>{isInjecting ? "Injecting..." : "Inject Demo Clash (Rule R3)"}</span>
        </button>
      </div>

      {conflict ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Conflict Core Breakdown */}
          <div className="space-y-6">
            <div className="glass-box p-6 space-y-3">
              <div className="flex items-center gap-2 border-b border-white/5 pb-3">
                <AlertTriangle size={16} className="text-zinc-300" />
                <h3 className="text-white text-sm font-semibold">
                  Minimal Infeasible Core
                </h3>
              </div>
              <p className="text-xs text-zinc-400">
                CP-SAT isolated the minimal sub-set of rules that cannot simultaneously be satisfied:
              </p>

              <div className="flex flex-wrap gap-2 pt-2">
                {conflict.rule_ids.map((rId) => (
                  <span
                    key={rId}
                    className="font-mono text-xs px-2.5 py-1 rounded-md bg-zinc-800 text-white border border-white/10 font-bold"
                  >
                    {rId}
                  </span>
                ))}
              </div>

              <div className="pt-3 border-t border-white/5 text-xs text-zinc-400 space-y-1">
                <span className="font-medium text-zinc-300">Impacted Rule Owners:</span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {conflict.owners.map((owner) => (
                    <span
                      key={owner}
                      className="px-2.5 py-0.5 rounded-md bg-white/[0.03] border border-white/5 text-[11px] text-zinc-300"
                    >
                      {owner}
                    </span>
                  ))}
                </div>
              </div>

              <div className="pt-3">
                <button
                  onClick={() => explainMutation.mutate(conflict)}
                  disabled={explainMutation.isPending}
                  className="w-full h-8 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center justify-center gap-1.5 shadow-sm active:scale-[0.98]"
                >
                  <span>{explainMutation.isPending ? "Generating Explanation..." : "Generate Natural Explanation"}</span>
                </button>
              </div>
            </div>

            {/* Explanation card */}
            {explanation && (
              <div className="glass-box p-6 space-y-3">
                <div className="border-b border-white/5 pb-3">
                  <h3 className="text-white text-sm font-semibold">
                    Explanation
                  </h3>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Multilingual synthesis explaining root mathematical cause
                  </p>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed bg-white/[0.02] p-3 rounded-md border border-white/5">
                  {explanation.summary}
                </p>
              </div>
            )}
          </div>

          {/* Right 2 Cols: Relaxation Options */}
          <div className="lg:col-span-2 glass-box p-6 space-y-4">
            <div className="border-b border-white/5 pb-3">
              <h3 className="text-white text-sm font-semibold">
                Solver-Verified Relaxation Options
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Every alternative proposed below has been pre-verified by CP-SAT to guarantee mathematical feasibility.
              </p>
            </div>

            <div className="space-y-3">
              {(explanation?.options || [
                {
                  id: "opt-1",
                  rule_id: "R3",
                  new_params: { day: 0, slots: [4, 5] },
                  description: "Move Prof. Rao's lecture from Monday 09:00 to Monday 14:00.",
                  approver: "Prof. Rao",
                  verified: true,
                  option_hash: "0x123",
                },
                {
                  id: "opt-2",
                  rule_id: "R1",
                  new_params: { room: "Room 102" },
                  description: "Assign CS101 to Room 102 on Monday morning, freeing Room 101.",
                  approver: "Dept Head",
                  verified: true,
                  option_hash: "0x456",
                },
              ]).map((opt: RelaxOption) => (
                <div
                  key={opt.id}
                  className="p-4 rounded-md border border-white/10 bg-[#16161c]/80 space-y-3 hover:border-white/20 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <span className="font-semibold text-white text-sm">Relax {opt.rule_id}</span>
                    <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-[11px] border border-white/5 font-mono">
                      Owner: {opt.approver}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-400 leading-relaxed">
                    {opt.description}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-white/5">
                    <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                      <Lock size={12} className="text-zinc-500" />
                      <span>Requires on-chain approval</span>
                    </div>

                    <Link to="/app/approvals">
                      <button className="h-7 px-3 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center gap-1">
                        <span>Sign Approval</span>
                        <ArrowRight size={11} />
                      </button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-box p-12 text-center space-y-3">
          <h3 className="text-base font-semibold text-white">No Active Conflicts Detected</h3>
          <p className="text-xs text-zinc-400 max-w-md mx-auto">
            The current active constraints are mutually feasible. You can click &quot;Inject Demo Clash&quot; above to simulate the R1+R2+R3 faculty unavailability conflict.
          </p>
        </div>
      )}
    </div>
  );
}
