import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { ScoreboardResult } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { BarChart3, Sparkles, CheckCircle2, AlertOctagon, Trophy } from "lucide-react";

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
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Constraint Satisfaction Scoreboard</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Empirical benchmark comparing GeCompose constraint solver against unconstrained LLM generation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="text-xs gap-1.5 py-1">
            <Sparkles size={12} className="text-primary" />
            <span>Recorded Fixture (Mock LLM Mode)</span>
          </Badge>

          <Button
            size="sm"
            onClick={() => scoreboardMutation.mutate(runs)}
            isLoading={scoreboardMutation.isPending}
            className="text-xs h-8 gap-1.5"
          >
            <BarChart3 size={13} />
            <span>Run Benchmark ({runs} runs)</span>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-emerald-200 bg-emerald-50/20 dark:border-emerald-900">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                <Trophy size={14} className="text-emerald-600" />
                GeCompose (CP-SAT Solver)
              </span>
              <Badge variant="success">0 Violations</Badge>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Mathematically checks 100% of room capacities, professor availability, double bookings, and qualifications.
          </CardContent>
        </Card>

        <Card className="border-amber-200 bg-amber-50/20 dark:border-amber-900">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                <AlertOctagon size={14} className="text-amber-600" />
                Baseline Unconstrained LLM
              </span>
              <Badge variant="warning">Frequent Violations</Badge>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground">
            Hallucinates slot double-bookings, assigns unavailable faculty, and ignores room limits on average.
          </CardContent>
        </Card>
      </div>

      {results ? (
        <Card>
          <CardHeader className="border-b border-border pb-3">
            <h3 className="text-sm font-semibold text-foreground">Benchmark Results Across Runs</h3>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground">
                    <th className="py-2.5 px-4 font-medium">Run #</th>
                    <th className="py-2.5 px-4 font-medium">GeCompose Violations</th>
                    <th className="py-2.5 px-4 font-medium">Baseline LLM Violations</th>
                    <th className="py-2.5 px-4 font-medium">Baseline Collision Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {results.rows.map((row) => (
                    <tr key={row.run} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2.5 px-4 font-bold text-foreground">Run #{row.run}</td>
                      <td className="py-2.5 px-4">
                        <Badge variant="success" className="font-mono">
                          {row.gecompose_violations}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4">
                        <Badge variant="destructive" className="font-mono">
                          {row.baseline_violations}
                        </Badge>
                      </td>
                      <td className="py-2.5 px-4 text-muted-foreground max-w-md truncate">
                        {row.baseline_details.length > 0
                          ? row.baseline_details.join("; ")
                          : "None"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="py-12 text-center text-xs text-muted-foreground">
          Click &quot;Run Benchmark&quot; to execute comparative runs and measure collision metrics.
        </Card>
      )}
    </div>
  );
}
