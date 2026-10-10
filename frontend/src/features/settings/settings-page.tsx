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
  CheckCircle2,
  AlertCircle,
  Shield,
  UserCheck,
} from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
      key: "postgres",
      name: "PostgreSQL Database",
      icon: Database,
      desc: "Stores user sessions, verified rules, roster data, and published schedule hashes.",
    },
    {
      key: "anvil",
      name: "Anvil Local EVM Node",
      icon: Server,
      desc: "Local Ethereum execution node on chain ID 31337 for fast, deterministic contract testing.",
    },
    {
      key: "contract",
      name: "ConsentLedger Contract",
      icon: Layers,
      desc: "Deploys on-chain rule hashes, multi-party relaxation approvals, and timetable anchor receipts.",
    },
    {
      key: "docker",
      name: "Docker Sandbox",
      icon: Container,
      desc: "Safely executes generated Python spreadsheet parsers in an isolated container without network access.",
    },
    {
      key: "llama-server",
      name: "Gemma / Llama Server",
      icon: Cpu,
      desc: "Local GGUF LLM inference for multilingual intake and natural language conflict explanations.",
    },
  ];

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
          <Settings className="w-6 h-6 text-primary" />
          System Settings & Diagnostics
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Monitor connected infrastructure, verify operational safety boundaries, and manage the active demo workspace.
        </p>
      </div>

      {/* Account Info Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-primary" />
            Active Session & Identity
          </CardTitle>
          <CardDescription>
            Your authenticated server-side session credentials and operational permission level.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 rounded-lg border border-border bg-muted/30">
              <span className="text-muted-foreground block mb-1">Display Name</span>
              <span className="font-semibold text-foreground text-sm">{user?.name || "Anonymous User"}</span>
            </div>
            <div className="p-3 rounded-lg border border-border bg-muted/30">
              <span className="text-muted-foreground block mb-1">Email Address</span>
              <span className="font-mono text-foreground text-sm">{user?.email || "—"}</span>
            </div>
            <div className="p-3 rounded-lg border border-border bg-muted/30">
              <span className="text-muted-foreground block mb-1">Role / Permissions</span>
              <div className="mt-1">
                <Badge variant={user?.role === "coordinator" ? "default" : "secondary"}>
                  {user?.role ? user.role.toUpperCase() : "AUTHENTICATED"}
                </Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Infrastructure Health Diagnostics */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              Infrastructure Diagnostics
            </h2>
            <p className="text-xs text-muted-foreground">
              Live heartbeat checks against local containerized dependencies and nodes.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetchHealth()}
            disabled={healthLoading || isRefetching}
            className="gap-2 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
            Run Diagnostics
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {services.map((srv) => {
            const Icon = srv.icon;
            const item = health?.items?.[srv.key];
            const isOk = item?.ok ?? false;
            const detail = item?.detail ?? (healthLoading ? "Checking status..." : "Unavailable");

            return (
              <Card key={srv.key} className="relative overflow-hidden">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${isOk ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-foreground">{srv.name}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">{srv.desc}</p>
                      </div>
                    </div>
                    {isOk ? (
                      <Badge variant="outline" className="text-emerald-500 border-emerald-500/30 bg-emerald-500/10 shrink-0 gap-1 text-[11px]">
                        <CheckCircle2 className="w-3 h-3" /> Operational
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-amber-500 border-amber-500/30 bg-amber-500/10 shrink-0 gap-1 text-[11px]">
                        <AlertCircle className="w-3 h-3" /> Fallback Mode
                      </Badge>
                    )}
                  </div>

                  <div className="mt-3 pt-3 border-t border-border/60">
                    <div className="text-xs font-mono text-muted-foreground bg-muted/40 p-2 rounded border border-border/40 truncate">
                      {detail}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Demo Workspace Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-primary" />
            Demo Workspace Management
          </CardTitle>
          <CardDescription>
            Re-seed the baseline university timetable, faculty constraints, and conflict core, or reset workspace tables.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-3.5 rounded-lg border border-border bg-muted/20 text-xs text-muted-foreground leading-relaxed">
            <strong>Seed action:</strong> Populates the standard reference test case with R1 (Dean: CS101 Monday morning), R2 (Dept Head: CS102 Monday morning), and R3 (Prof. Rao: Room 101 Monday morning only), enabling immediate conflict isolation and relaxation testing.
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              onClick={handleSeed}
              disabled={isSeeding || isResetting}
              className="gap-2"
            >
              <Sparkles className="w-4 h-4" />
              {isSeeding ? "Seeding..." : "Seed Baseline Demo State"}
            </Button>

            <Button
              variant="outline"
              onClick={handleReset}
              disabled={isSeeding || isResetting}
              className="gap-2 text-destructive hover:bg-destructive/10"
            >
              <RotateCcw className="w-4 h-4" />
              {isResetting ? "Resetting..." : "Reset Workspace State"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
