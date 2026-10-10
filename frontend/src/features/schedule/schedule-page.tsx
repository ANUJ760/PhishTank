import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import { Placement, Rule, SolveResult } from "@/types/api";
import {
  Zap,
  HelpCircle,
  Calendar,
  Layers,
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
    <div className="space-y-6 text-left pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Timetable Schedule Grid</h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Synchronous constraint optimization grid across standard weekly academic slots.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={minimalChange}
              onChange={(e) => setMinimalChange(e.target.checked)}
              className="rounded bg-zinc-900 border-white/10 text-white focus:ring-0 h-3.5 w-3.5"
            />
            <span>Minimal Change Mode</span>
          </label>

          <button
            onClick={() => solveMutation.mutate(minimalChange)}
            disabled={solveMutation.isPending}
            className="h-8 px-4 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all flex items-center gap-1.5 shadow-sm active:scale-[0.98] disabled:opacity-50"
          >
            <Zap size={13} className="text-zinc-950" />
            <span>{solveMutation.isPending ? "Solving..." : "Solve (CP-SAT)"}</span>
          </button>

          <Link to="/app/publish">
            <button className="h-8 px-4 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white font-medium text-xs transition-all flex items-center gap-1">
              <span>Publish</span>
              <ArrowRight size={12} />
            </button>
          </Link>
        </div>
      </div>

      {/* Solver Feedback Banner (Clean dark glass, NO green/red boxes) */}
      {lastSolveResult && (
        <div className="p-3.5 rounded-lg border border-white/10 bg-zinc-900/80 backdrop-blur-xl text-xs flex items-center justify-between text-zinc-300">
          <div className="flex items-center gap-2.5">
            <span className="h-2 w-2 rounded-full bg-zinc-400" />
            <span>
              <strong>Status: {lastSolveResult.status.toUpperCase()}</strong> &bull; Solved in{" "}
              {lastSolveResult.solve_ms} ms &bull; {lastSolveResult.moved.length} session(s) moved
            </span>
          </div>
          {lastSolveResult.status === "infeasible" && (
            <Link to="/app/conflicts">
              <button className="h-6 px-3 rounded-md bg-white text-zinc-950 font-medium text-[11px] hover:bg-zinc-200 transition-all">
                Open Conflict Studio
              </button>
            </Link>
          )}
        </div>
      )}

      {/* Interactive Grid and Cell Inspector in Glass Boxes */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Schedule Table (3 Cols) */}
        <div className="lg:col-span-3 glass-box p-6 space-y-4">
          <div className="flex flex-row items-center justify-between border-b border-white/5 pb-3">
            <div className="flex items-center gap-2">
              <Calendar size={15} className="text-zinc-400" />
              <h3 className="text-white text-sm font-semibold">
                Schedule Grid {schedule?.version ? `(Version ${schedule.version})` : ""}
              </h3>
            </div>
            <span className="text-[11px] text-zinc-500">Click any assigned cell to inspect constraints</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/5 text-zinc-400">
                  <th className="py-2.5 px-3 font-semibold text-zinc-400 w-20 text-center">Time</th>
                  {days.map((day) => (
                    <th key={day} className="py-2.5 px-3 font-semibold text-zinc-300 text-center">
                      {day}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {slotTimes.map((time, slotIdx) => (
                  <tr key={time} className="h-20">
                    <td className="py-2 px-3 text-center font-mono text-[11px] text-zinc-400 bg-white/[0.01] border-r border-white/5 font-medium">
                      {time}
                    </td>
                    {days.map((_, dayIdx) => {
                      const placement = grid[`${dayIdx}-${slotIdx}`];
                      const isSelected = selectedSession && placement?.session_id === selectedSession;
                      return (
                        <td
                          key={dayIdx}
                          onClick={() => placement && setSelectedSession(placement.session_id)}
                          className={`p-2 border-r border-white/5 last:border-r-0 align-top transition-colors ${
                            placement
                              ? isSelected
                                ? "bg-white/[0.08]"
                                : "hover:bg-white/[0.03] cursor-pointer"
                              : "bg-transparent"
                          }`}
                        >
                          {placement ? (
                            <div className="h-full rounded-md border border-white/10 bg-[#16161c]/90 p-2.5 shadow-sm flex flex-col justify-between hover:border-white/20 transition-all">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-white text-xs">{placement.session_id}</span>
                                <span className="text-[10px] text-zinc-400 font-mono">{placement.room}</span>
                              </div>
                              <div className="text-[11px] text-zinc-400 mt-1 truncate">
                                {placement.teacher}
                              </div>
                            </div>
                          ) : (
                            <div className="h-full rounded-md border border-dashed border-white/5 flex items-center justify-center text-zinc-600 text-[10px]">
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
        </div>

        {/* Cell Constraint Inspector (Right Col) */}
        <div className="glass-box p-6 space-y-4">
          <div className="border-b border-white/5 pb-3">
            <h3 className="text-white text-sm font-semibold flex items-center gap-1.5">
              <HelpCircle size={14} className="text-zinc-400" />
              Constraint Inspector
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Rules locking the selected timetable cell
            </p>
          </div>

          {selectedSession ? (
            <div className="space-y-4">
              <div className="p-3 rounded-md bg-white/[0.02] border border-white/10">
                <span className="text-[10px] text-zinc-400 uppercase tracking-wider block">Inspecting Session</span>
                <span className="text-sm font-bold text-white font-mono mt-0.5 block">{selectedSession}</span>
              </div>

              <div className="space-y-2">
                <span className="text-xs font-semibold text-zinc-300">Active Rules Driving Placement:</span>
                {isWhyLoading ? (
                  <p className="text-xs text-zinc-500">Querying registry rules...</p>
                ) : whyRules.length === 0 ? (
                  <p className="text-xs text-zinc-500">No explicit hard constraints pinned this specific session.</p>
                ) : (
                  whyRules.map((rule) => (
                    <div key={rule.id} className="p-2.5 rounded-md border border-white/5 bg-white/[0.02] text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-zinc-200">{rule.id}</span>
                        <span className="px-2 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-[10px]">
                          {rule.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-400">Owner: {rule.owner}</p>
                      {rule.evidence && (
                        <p className="text-[10px] text-zinc-400 italic bg-white/[0.02] p-1.5 rounded-lg border border-white/5">
                          &quot;{rule.evidence}&quot;
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-zinc-500">
              Select any session cell on the grid to inspect the underlying verified constraints.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
