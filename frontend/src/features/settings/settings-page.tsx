import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings,
  Activity,
  Database,
  Server,
  Layers,
  Container,
  Cpu,
  RefreshCw,
  RotateCcw,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [isResetting, setIsResetting] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  const {
    data: health,
    isLoading: healthLoading,
    refetch: refetchHealth,
    isRefetching,
  } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10000,
  });

  const handleSeed = async () => {
    setIsSeeding(true);
    try {
      const res = await api.demo.seed();
      toast.success(res.message || "Demo data seeded successfully");
      queryClient.invalidateQueries();
    } catch (err: any) {
      toast.error(err.message || "Failed to seed demo data");
    } finally {
      setIsSeeding(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Are you sure you want to reset the demo state? All draft and pending records will be cleared.")) {
      return;
    }
    setIsResetting(true);
    try {
      const res = await api.demo.reset();
      toast.success(res.message || "Demo state reset successfully");
      queryClient.invalidateQueries();
    } catch (err: any) {
      toast.error(err.message || "Failed to reset demo state");
    } finally {
      setIsResetting(false);
    }
  };

  const services = [
    {
      key: "database",
      name: "Database (PostgreSQL / SQLite)",
      icon: Database,
      desc: "Stores user sessions, verified constraints, master schedules, and audit records.",
    },
    {
      key: "ollama",
      name: "Ollama / Gemma Service",
      icon: Cpu,
      desc: "Local inference engine hosting Gemma 4B and 12B multimodal models.",
    },
    {
      key: "intake_model",
      name: "Gemma 4B Intake Model",
      icon: Server,
      desc: "Fast multilingual extraction for voice, photos, and dispatch reports.",
    },
    {
      key: "reason_model",
      name: "Gemma 12B Reasoning Engine",
      icon: Layers,
      desc: "Deep clinical, logistical, and mathematical conflict explanation engine.",
    },
    {
      key: "sandbox",
      name: "Execution Sandbox",
      icon: Container,
      desc: "Safely executes generated Python spreadsheet parsers in an isolated environment.",
    },
  ];

  return (
    <div className="space-y-8 max-w-5xl text-left pb-12">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-zinc-300" />
          System Settings & Diagnostics
        </h2>
        <p className="text-xs text-zinc-400 mt-1">
          Monitor connected infrastructure, verify operational safety boundaries, and manage the active demo workspace.
        </p>
      </div>

      {/* Account Info Card */}
      <div className="glass-box p-6 space-y-4">
        <div className="border-b border-white/5 pb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-zinc-300" />
            Active Session & Identity
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Your authenticated server-side session credentials and operational permission level.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-md border border-white/5 bg-white/[0.02]">
            <span className="text-zinc-500 block mb-1">Display Name</span>
            <span className="font-semibold text-white text-sm">{user?.name || "Anonymous User"}</span>
          </div>
          <div className="p-3.5 rounded-md border border-white/5 bg-white/[0.02]">
            <span className="text-zinc-500 block mb-1">Email Address</span>
            <span className="font-mono text-zinc-200 text-sm">{user?.email || "—"}</span>
          </div>
          <div className="p-3.5 rounded-md border border-white/5 bg-white/[0.02]">
            <span className="text-zinc-500 block mb-1">Role / Permissions</span>
            <div className="mt-1">
              <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 text-xs font-mono font-medium">
                {user?.role ? user.role.toUpperCase() : "AUTHENTICATED"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Infrastructure Health Diagnostics */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-zinc-300" />
              Infrastructure Diagnostics
            </h3>
            <p className="text-xs text-zinc-400">
              Live heartbeat checks against local cluster dependencies.
            </p>
          </div>
          <button
            onClick={() => refetchHealth()}
            disabled={healthLoading || isRefetching}
            className="h-8 px-4 rounded-md bg-zinc-900 border border-white/10 text-zinc-300 hover:text-white font-medium text-xs transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            <span>Run Diagnostics</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {services.map((srv) => {
            const Icon = srv.icon;
            const item = health?.items?.[srv.key];
            const isOk = item?.ok ?? false;
            const detail = item?.detail ?? (healthLoading ? "Checking status..." : "Unavailable");

            return (
              <div key={srv.key} className="glass-box p-5 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-white/[0.03] text-zinc-300 border border-white/5">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-white">{srv.name}</h4>
                      <p className="text-[11px] text-zinc-400 mt-0.5">{srv.desc}</p>
                    </div>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-md bg-zinc-800 text-zinc-300 border border-white/5 text-[10px] font-mono shrink-0">
                    {isOk ? "ONLINE" : "ATTN"}
                  </span>
                </div>

                <div className="pt-2 border-t border-white/5">
                  <div className="text-[11px] font-mono text-zinc-400 bg-black p-2 rounded-md border border-white/5 truncate">
                    {detail}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Demo Workspace Actions */}
      <div className="glass-box p-6 space-y-4">
        <div className="border-b border-white/5 pb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-zinc-300" />
            Demo Workspace Management
          </h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            Re-seed the baseline university timetable, faculty constraints, and conflict core, or reset workspace tables.
          </p>
        </div>

        <div className="p-3.5 rounded-md border border-white/5 bg-white/[0.02] text-xs text-zinc-400 leading-relaxed">
          <strong className="text-white">Seed action:</strong> Populates the standard reference test case with R1 (Dean: CS101 Monday morning), R2 (Dept Head: CS102 Monday morning), and R3 (Prof. Rao: Room 101 Monday morning only), enabling immediate conflict isolation and relaxation testing.
        </div>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button
            onClick={handleSeed}
            disabled={isSeeding || isResetting}
            className="h-8 px-5 rounded-md bg-white text-zinc-950 font-medium text-xs hover:bg-zinc-200 transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isSeeding ? "Seeding..." : "Seed Baseline Demo State"}</span>
          </button>

          <button
            onClick={handleReset}
            disabled={isSeeding || isResetting}
            className="h-8 px-5 rounded-md bg-zinc-900 border border-white/10 text-zinc-400 hover:text-white font-medium text-xs transition-all active:scale-[0.98] disabled:opacity-50 flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>{isResetting ? "Resetting..." : "Reset Workspace State"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
