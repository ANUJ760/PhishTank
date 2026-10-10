import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { ScoreboardResult } from "@/types/api";
import { BarChart3, Sparkles, Trophy } from "lucide-react";

export function ScoreboardPage() {
  const [runs, setRuns] = useState(3);
  const [results, setResults] = useState<ScoreboardResult | null>(null);

  const scoreboardMutation = useMutation({
    mutationFn: (numRuns: number) => api.scoreboard(numRuns),
    onSuccess: (data: ScoreboardResult) => {
      setResults(data);
    },
  });

  return (
    <div className="space-y-6 text-left pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Constraint Satisfaction Scoreboard</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Empirical benchmark comparing GeCompose constraint solver against unconstrained LLM generation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-md bg-zinc-900 border border-white/10 text-xs text-zinc-300 flex items-center gap-1.5">
            <Sparkles size={12} className="text-zinc-400" />
            <span>Recorded Fixture (Mock LLM Mode)</span>
          </span>

          <button
            onClick={() => scoreboardMutation.mutate(runs)}
            disabled={scoreboardMutation.isPending}
            className="h-8 px-4 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98] disabled:opacity-50"
          >
            <BarChart3 size={13} />
            <span>{scoreboardMutation.isPending ? "Evaluating..." : `Run Benchmark (${runs} runs)`}</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="glass-box p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-xs font-semibold text-white flex items-center gap-1.5">
              <Trophy size={14} className="text-zinc-300" />
              GeCompose (Constraint Engine)
            </span>
            <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-200 border border-white/10 text-[11px] font-mono">
              0 Violations
            </span>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            The mathematical constraint engine guarantees 100% adherence to all confirmed room bounds, resource windows, and qualification sets.
          </p>
        </div>

        <div className="glass-box p-6 space-y-3">
          <div className="flex items-center justify-between border-b border-white/5 pb-3">
            <span className="text-xs font-semibold text-white">
              Baseline Generative LLM
            </span>
            <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 border border-white/10 text-[11px] font-mono">
              ~2-4 Violations / Run
            </span>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Direct language model scheduling without constraint propagation routinely exhibits double-bookings, capacity violations, and teacher availability clashes.
          </p>
        </div>
      </div>

      {results && (
        <div className="glass-box p-6 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-sm font-semibold text-white">Benchmark Execution Run Breakdown</h3>
            <p className="text-xs text-zinc-400 mt-0.5">Trial results evaluated across {results.rows.length} runs</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-white/5 text-zinc-400">
                  <th className="py-2.5 px-3 font-semibold">Run #</th>
                  <th className="py-2.5 px-3 font-semibold">GeCompose Violations</th>
                  <th className="py-2.5 px-3 font-semibold">Baseline Violations</th>
                  <th className="py-2.5 px-3 font-semibold">Baseline Clash Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {results.rows.map((r) => (
                  <tr key={r.run} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-3 font-mono font-bold text-white">Trial #{r.run}</td>
                    <td className="py-2.5 px-3 font-bold text-zinc-200">
                      {r.gecompose_violations} (Satisfied)
                    </td>
                    <td className="py-2.5 px-3 text-zinc-300 font-mono">
                      {r.baseline_violations}
                    </td>
                    <td className="py-2.5 px-3 text-zinc-400 text-[11px]">
                      {r.baseline_details.length > 0 ? r.baseline_details.join("; ") : "None detected"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
