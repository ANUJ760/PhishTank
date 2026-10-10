import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Placement, Rule, SolveResult } from "@/types/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Zap,
  HelpCircle,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  Sparkles,
  ArrowRight,
  Info,
} from "lucide-react";

export function SchedulePage() {
  const queryClient = useQueryClient();
  const [minimalChange, setMinimalChange] = useState(true);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const { data: schedule, isLoading: isScheduleLoading } = useQuery({
    queryKey: ["latest-schedule"],
    queryFn: async () => {
      try {
        return await api.schedules.latest();
      } catch {
        // try pending if latest not yet published
        try {
          return await api.schedules.pending();
        } catch {
          return null;
        }
      }
    },
  });

  const { data: whyRules = [], isLoading: isWhyLoading } = useQuery({
    queryKey: ["why-cell", selectedSession],
    queryFn: () => (selectedSession ? api.schedules.whyCell(selectedSession) : []),
    enabled: !!selectedSession,
  });

  const solveMutation = useMutation({
    mutationFn: (minChange: boolean) => api.solve(minChange),
    onSuccess: (res: SolveResult) => {
      queryClient.invalidateQueries({ queryKey: ["latest-schedule"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      if (res.status === "feasible" && res.schedule?.placements?.[0]) {
        setSelectedSession(res.schedule.placements[0].session_id);
      }
    },
  });

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const slotTimes = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00"];

  // Index placements: [day][slot] -> Placement
  const grid: Record<string, Placement> = {};
  if (schedule?.placements) {
    for (const p of schedule.placements) {
      grid[`${p.day}-${p.slot}`] = p;
    }
  }

  const lastSolveResult = solveMutation.data;

  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Timetable Schedule Grid</h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Synchronous constraint optimization grid across standard weekly academic slots.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={minimalChange}
              onChange={(e) => setMinimalChange(e.target.checked)}
              className="rounded border-border text-primary focus:ring-primary h-3.5 w-3.5"
            />
            <span>Minimal Change Mode</span>
          </label>

          <Button
            size="sm"
            onClick={() => solveMutation.mutate(minimalChange)}
            isLoading={solveMutation.isPending}
            className="gap-1.5 text-xs h-8"
          >
            <Zap size={13} className="text-amber-400" />
            <span>Solve (CP-SAT)</span>
          </Button>

          <Link to="/app/publish">
            <Button variant="outline" size="sm" className="text-xs h-8 gap-1">
              <span>Publish</span>
              <ArrowRight size={13} />
            </Button>
          </Link>
        </div>
      </div>

      {/* Solver Feedback Banner */}
      {lastSolveResult && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
            lastSolveResult.status === "feasible"
              ? "bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800"
              : lastSolveResult.status === "infeasible"
              ? "bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-800"
              : "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {lastSolveResult.status === "feasible" ? (
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle size={16} className="text-rose-600 shrink-0" />
            )}
            <span>
              <strong>Status: {lastSolveResult.status.toUpperCase()}</strong> &bull; Solved in{" "}
              {lastSolveResult.solve_ms} ms &bull; {lastSolveResult.moved.length} session(s) moved
            </span>
          </div>
          {lastSolveResult.status === "infeasible" && (
            <Link to="/app/conflicts">
              <Button size="sm" variant="destructive" className="h-6 text-[11px] px-2">
                Open Conflict Studio
              </Button>
            </Link>
          )}
        </div>
      )}

      {/* Interactive Grid and Cell Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Schedule Table (3 Cols) */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div className="flex items-center gap-2">
                <Calendar size={15} className="text-primary" />
                <CardTitle className="text-foreground text-sm font-semibold">
                  Schedule Grid {schedule?.version ? `(Version ${schedule.version})` : ""}
                </CardTitle>
              </div>
              <span className="text-[11px] text-muted-foreground">Click any assigned cell to inspect constraints</span>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr className="border-y border-border bg-muted/40">
                      <th className="py-2.5 px-3 font-semibold text-muted-foreground w-20 text-center">Time</th>
                      {days.map((day) => (
                        <th key={day} className="py-2.5 px-3 font-semibold text-foreground text-center">
                          {day}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {slotTimes.map((time, slotIdx) => (
                      <tr key={time} className="h-20">
                        <td className="py-2 px-3 text-center font-mono text-[11px] text-muted-foreground bg-muted/20 border-r border-border font-medium">
                          {time}
                        </td>
                        {days.map((_, dayIdx) => {
                          const placement = grid[`${dayIdx}-${slotIdx}`];
                          const isSelected = selectedSession && placement?.session_id === selectedSession;
                          return (
                            <td
                              key={dayIdx}
                              onClick={() => placement && setSelectedSession(placement.session_id)}
                              className={`p-2 border-r border-border last:border-r-0 align-top transition-colors ${
                                placement
                                  ? isSelected
                                    ? "bg-primary/10 border-primary"
                                    : "hover:bg-muted/50 cursor-pointer"
                                  : "bg-background"
                              }`}
                            >
                              {placement ? (
                                <div className="h-full rounded-md border border-border bg-card p-2 shadow-xs flex flex-col justify-between">
                                  <div className="flex items-center justify-between">
                                    <span className="font-bold text-foreground text-xs">{placement.session_id}</span>
                                    <span className="text-[10px] text-muted-foreground font-mono">{placement.room}</span>
                                  </div>
                                  <div className="text-[11px] text-muted-foreground mt-1 truncate">
                                    👤 {placement.teacher}
                                  </div>
                                </div>
                              ) : (
                                <div className="h-full rounded-md border border-dashed border-border/40 flex items-center justify-center text-muted-foreground/30 text-[10px]">
                                  Free
                                </div>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Cell Constraint Inspector (Right Col) */}
        <div>
          <Card className="sticky top-6">
            <CardHeader className="border-b border-border pb-3">
              <div className="flex items-center gap-1.5">
                <HelpCircle size={15} className="text-primary" />
                <h3 className="text-sm font-semibold text-foreground">Why This Slot?</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                Formal constraint explanations for cell placement.
              </p>
            </CardHeader>
            <CardContent className="pt-4 space-y-4 text-xs">
              {selectedSession ? (
                <>
                  <div className="p-3 rounded-lg bg-muted border border-border">
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block">
                      Active Session
                    </span>
                    <span className="font-bold text-base text-foreground">{selectedSession}</span>
                  </div>

                  <div>
                    <span className="text-[10px] uppercase font-semibold text-muted-foreground block mb-2">
                      Constraining Rules ({whyRules.length})
                    </span>
                    {isWhyLoading ? (
                      <div className="text-muted-foreground py-4 text-center">Evaluating active rules...</div>
                    ) : whyRules.length > 0 ? (
                      <div className="space-y-2">
                        {whyRules.map((rule) => (
                          <div key={rule.id} className="p-2.5 rounded-lg border border-border bg-card space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-foreground">{rule.id}</span>
                              <Badge variant="outline" className="text-[10px] capitalize">
                                {rule.type.replace("_", " ")}
                              </Badge>
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              Owner: <span className="text-foreground">{rule.owner}</span>
                            </div>
                            <pre className="text-[10px] font-mono bg-muted p-1 rounded border border-border truncate">
                              {JSON.stringify(rule.params)}
                            </pre>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 rounded-lg bg-muted/40 text-muted-foreground text-[11px] flex items-start gap-2">
                        <Info size={14} className="shrink-0 mt-0.5 text-primary" />
                        <span>
                          Assigned to satisfy global room capacity and prevent double-booking collisions.
                        </span>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-muted-foreground">
                  Select any assigned timetable block on the grid to inspect its governing constraints.
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
