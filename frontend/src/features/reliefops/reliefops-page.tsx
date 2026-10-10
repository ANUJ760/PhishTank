import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  LifeBuoy,
  Warehouse,
  Truck,
  Sparkles,
  CheckCircle2,
  TrendingUp,
  RotateCcw,
  Sliders,
  FileCheck,
  ShieldCheck,
  AlertTriangle,
  Play,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function ReliefOpsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"camps" | "warehouses" | "simulate" | "explain" | "audit">("camps");

  // What-If Simulation Form States
  const [waterDonation, setWaterDonation] = useState<number>(3000);
  const [disablePortWh, setDisablePortWh] = useState<boolean>(false);
  const [simResults, setSimResults] = useState<any | null>(null);

  // Queries
  const overviewQuery = useQuery({
    queryKey: ["reliefops", "overview"],
    queryFn: () => api.reliefops.overview(),
  });

  const campsQuery = useQuery({
    queryKey: ["reliefops", "camps"],
    queryFn: () => api.reliefops.camps(),
  });

  const inventoryQuery = useQuery({
    queryKey: ["reliefops", "inventory"],
    queryFn: () => api.reliefops.inventory(),
  });

  const latestPlanQuery = useQuery({
    queryKey: ["reliefops", "latestPlan"],
    queryFn: () => api.reliefops.latestPlan().catch(() => null),
  });

  const auditQuery = useQuery({
    queryKey: ["reliefops", "audit"],
    queryFn: () => api.reliefops.audit(),
    enabled: activeTab === "audit",
  });

  // Mutations
  const optimizeMutation = useMutation({
    mutationFn: () => api.reliefops.optimize("Emergency Convoy Allocation"),
    onSuccess: (plan) => {
      toast.success(`Allocation plan generated (${(plan.summary.overall_fulfillment_rate * 100).toFixed(1)}% fulfillment)`);
      queryClient.invalidateQueries({ queryKey: ["reliefops"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Optimization failed");
    },
  });

  const simulateMutation = useMutation({
    mutationFn: async () => {
      const delta: any = {
        extra_inventory: waterDonation > 0 ? { WATER_LITERS: waterDonation } : {},
        disabled_warehouses: disablePortWh ? ["WH-PORT"] : [],
      };
      return api.reliefops.simulate(delta, "Counterfactual Supply Run");
    },
    onSuccess: (data) => {
      setSimResults(data);
      toast.success("What-if simulation completed");
      queryClient.invalidateQueries({ queryKey: ["reliefops"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Simulation failed");
    },
  });

  const explainMutation = useMutation({
    mutationFn: () => api.reliefops.explain(),
    onSuccess: () => {
      toast.success("AI rationale updated");
    },
  });

  const approveMutation = useMutation({
    mutationFn: (planId: string) =>
      api.reliefops.approve(planId, "Disaster Logistics Commander", "Authorized for multimodal transport convoys"),
    onSuccess: () => {
      toast.success("Plan approved and cryptographically anchored in audit ledger");
      queryClient.invalidateQueries({ queryKey: ["reliefops"] });
    },
    onError: (err: any) => {
      toast.error(err.message || "Approval failed");
    },
  });

  const seedMutation = useMutation({
    mutationFn: () => api.reliefops.seed(),
    onSuccess: () => {
      toast.success("Coastal Cyclone benchmark scenario seeded");
      queryClient.invalidateQueries({ queryKey: ["reliefops"] });
    },
  });

  const overview = overviewQuery.data;
  const plan = latestPlanQuery.data;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-white/[0.08] pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-md bg-white text-zinc-950 flex items-center justify-center font-bold text-xs shadow-sm">
              <LifeBuoy size={16} />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                Disaster Relief Logistics Engine
                <Badge variant="outline" className="text-[10px] uppercase tracking-wider bg-white/[0.04]">
                  Active Emergency Ops
                </Badge>
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Priority-aware supply distribution across relief camps under transport and inventory constraints.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="text-xs h-8 gap-1.5"
          >
            <RotateCcw size={13} className={seedMutation.isPending ? "animate-spin" : ""} />
            <span>Seed Scenario</span>
          </Button>

          <Button
            size="sm"
            onClick={() => optimizeMutation.mutate()}
            disabled={optimizeMutation.isPending}
            className="text-xs h-8 gap-1.5 bg-white text-zinc-950 hover:bg-zinc-200"
          >
            <Play size={13} className={optimizeMutation.isPending ? "animate-spin" : ""} />
            <span>{optimizeMutation.isPending ? "Optimizing..." : "Calculate Allocation"}</span>
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <Card className="p-4 bg-white/[0.03] border-white/[0.08]">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Population at Risk</span>
            <LifeBuoy size={14} className="text-zinc-500" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? overview.total_population.toLocaleString() : "..."}
          </div>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            {overview ? `${overview.total_vulnerable_population} high-vulnerability (children, elderly)` : "Loading..."}
          </div>
        </Card>

        <Card className="p-4 bg-white/[0.03] border-white/[0.08]">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Relief Camps</span>
            <Warehouse size={14} className="text-zinc-500" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? overview.camps_count : "..."}
          </div>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            Air-only & boat-only corridors monitored
          </div>
        </Card>

        <Card className="p-4 bg-white/[0.03] border-white/[0.08]">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Critical Supplies in Hubs</span>
            <Truck size={14} className="text-zinc-500" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {overview ? overview.total_items_in_stock.toLocaleString() : "..."}
          </div>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            Across 2 logistics warehouses
          </div>
        </Card>

        <Card className="p-4 bg-white/[0.03] border-white/[0.08]">
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span>Supply Fulfillment Rate</span>
            <TrendingUp size={14} className="text-zinc-500" />
          </div>
          <div className="text-2xl font-bold text-white mt-1">
            {plan ? `${(plan.summary.overall_fulfillment_rate * 100).toFixed(1)}%` : "Pending"}
          </div>
          <div className="text-[11px] text-zinc-500 mt-0.5">
            {plan ? `${(plan.summary.critical_fulfillment_rate * 100).toFixed(1)}% life-critical met` : "Run optimizer"}
          </div>
        </Card>
      </div>

      {/* Tabs Bar */}
      <div className="flex items-center gap-1 border-b border-white/[0.08] pb-2 text-xs">
        <button
          onClick={() => setActiveTab("camps")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === "camps" ? "bg-white/[0.1] text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          Camp Allocations
        </button>
        <button
          onClick={() => setActiveTab("warehouses")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === "warehouses" ? "bg-white/[0.1] text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          Warehouses & Fleet
        </button>
        <button
          onClick={() => setActiveTab("simulate")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === "simulate" ? "bg-white/[0.1] text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          What-If Simulation
        </button>
        <button
          onClick={() => {
            setActiveTab("explain");
            if (!explainMutation.data) explainMutation.mutate();
          }}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === "explain" ? "bg-white/[0.1] text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          AI Decision Rationale
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-3 py-1.5 rounded-md font-medium transition-colors ${
            activeTab === "audit" ? "bg-white/[0.1] text-white" : "text-zinc-400 hover:text-white"
          }`}
        >
          Cryptographic Audit Ledger
        </button>
      </div>

      {/* Tab 1: Camp Allocations */}
      {activeTab === "camps" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Active Camp Supply Allocations</h3>
            {plan && !plan.approved && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => approveMutation.mutate(plan.plan_id)}
                disabled={approveMutation.isPending}
                className="text-xs h-7 gap-1"
              >
                <CheckCircle2 size={12} />
                <span>Authorize & Approve Plan</span>
              </Button>
            )}
            {plan && plan.approved && (
              <Badge variant="outline" className="text-emerald-400 border-emerald-500/20 bg-emerald-500/10 text-xs">
                Plan Authorized by {plan.approved_by}
              </Badge>
            )}
          </div>

          <div className="overflow-x-auto rounded-lg border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-white/[0.08] bg-white/[0.03] text-zinc-400 font-medium">
                <tr>
                  <th className="p-3">Relief Camp</th>
                  <th className="p-3">Access Route</th>
                  <th className="p-3">Resource Item</th>
                  <th className="p-3">Requested</th>
                  <th className="p-3">Allocated</th>
                  <th className="p-3">Unmet</th>
                  <th className="p-3">Fulfillment</th>
                  <th className="p-3">Priority Rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05] text-zinc-300">
                {plan ? (
                  plan.allocations.map((a, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02]">
                      <td className="p-3 font-medium text-white">{a.camp_name}</td>
                      <td className="p-3">
                        <Badge
                          variant="outline"
                          className={
                            a.shipment_details?.access_mode === "air_only"
                              ? "text-sky-400 border-sky-400/20"
                              : a.shipment_details?.access_mode === "boat_only"
                              ? "text-cyan-400 border-cyan-400/20"
                              : "text-zinc-400"
                          }
                        >
                          {a.shipment_details?.access_mode || "open"}
                        </Badge>
                      </td>
                      <td className="p-3">{a.resource_name}</td>
                      <td className="p-3">{a.requested_quantity}</td>
                      <td className="p-3 font-semibold text-emerald-400">{a.allocated_quantity}</td>
                      <td className="p-3 text-rose-400">{a.unmet_quantity}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-16 bg-white/[0.08] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-400"
                              style={{ width: `${Math.min(100, a.fulfillment_ratio * 100)}%` }}
                            />
                          </div>
                          <span>{(a.fulfillment_ratio * 100).toFixed(0)}%</span>
                        </div>
                      </td>
                      <td className="p-3 text-[11px] text-zinc-400 max-w-xs truncate" title={a.allocation_rationale}>
                        {a.allocation_rationale}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="p-6 text-center text-zinc-500">
                      No active plan generated. Click "Calculate Allocation" above to run the optimizer.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Warehouses & Fleet */}
      {activeTab === "warehouses" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-4 bg-white/[0.03] border-white/[0.08] space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Warehouse size={15} />
              Operational Supply Hubs
            </h3>
            <div className="space-y-2 text-xs">
              <div className="p-3 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <div>
                  <div className="font-medium text-white">Central Logistics Staging Base</div>
                  <div className="text-zinc-400 text-[11px]">Depot Capacity: 600 m³ &bull; Air Base Staging</div>
                </div>
                <Badge variant="outline" className="text-emerald-400 border-emerald-500/20">Operational</Badge>
              </div>
              <div className="p-3 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <div>
                  <div className="font-medium text-white">Harbor Forward Relief Depot</div>
                  <div className="text-zinc-400 text-[11px]">Depot Capacity: 350 m³ &bull; Coastal Pier 3</div>
                </div>
                <Badge variant="outline" className="text-emerald-400 border-emerald-500/20">Operational</Badge>
              </div>
            </div>
          </Card>

          <Card className="p-4 bg-white/[0.03] border-white/[0.08] space-y-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Truck size={15} />
              Multimodal Transport Fleet
            </h3>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <span>Heavy Logistics Truck (12,000 kg payload)</span>
                <Badge variant="outline" className="text-zinc-300">Open Roads</Badge>
              </div>
              <div className="p-2.5 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <span>4x4 High-Clearance Truck (4,500 kg payload)</span>
                <Badge variant="outline" className="text-zinc-300">Restricted Roads</Badge>
              </div>
              <div className="p-2.5 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <span>Amphibious Rescue Boat (4,000 kg payload)</span>
                <Badge variant="outline" className="text-cyan-400 border-cyan-400/20">Boat Only</Badge>
              </div>
              <div className="p-2.5 rounded-md bg-white/[0.02] border border-white/[0.06] flex justify-between items-center">
                <span>Relief Aviation Helicopter (2,200 kg payload)</span>
                <Badge variant="outline" className="text-sky-400 border-sky-400/20">Air Only</Badge>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Tab 3: What-If Simulation */}
      {activeTab === "simulate" && (
        <div className="space-y-4">
          <Card className="p-5 bg-white/[0.03] border-white/[0.08] space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Sliders size={15} />
                Counterfactual What-If Simulation
              </h3>
              <p className="text-xs text-zinc-400 mt-1">
                Evaluate supply changes without mutating live disaster inventory.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs text-zinc-300 font-medium">Extra Water Donation Influx (Liters)</label>
                <input
                  type="number"
                  value={waterDonation}
                  onChange={(e) => setWaterDonation(Number(e.target.value))}
                  className="w-full bg-white/[0.04] border border-white/[0.1] rounded-md px-3 py-1.5 text-xs text-white"
                  placeholder="e.g. 3000"
                />
              </div>

              <div className="flex items-center gap-3 pt-6">
                <input
                  type="checkbox"
                  id="disableWh"
                  checked={disablePortWh}
                  onChange={(e) => setDisablePortWh(e.target.checked)}
                  className="rounded border-white/20 bg-zinc-900"
                />
                <label htmlFor="disableWh" className="text-xs text-zinc-300">
                  Simulate Harbor Depot Failure / Cutoff
                </label>
              </div>
            </div>

            <Button
              size="sm"
              onClick={() => simulateMutation.mutate()}
              disabled={simulateMutation.isPending}
              className="text-xs gap-1.5 bg-white text-zinc-950 hover:bg-zinc-200"
            >
              <Play size={13} className={simulateMutation.isPending ? "animate-spin" : ""} />
              <span>Run Counterfactual Simulation</span>
            </Button>
          </Card>

          {simResults && (
            <Card className="p-4 bg-emerald-500/[0.03] border-emerald-500/20 space-y-3">
              <h4 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                Simulation Comparison Output
              </h4>
              <p className="text-xs text-zinc-200">{simResults.comparison.summary_text}</p>
              <div className="flex items-center gap-4 text-xs text-zinc-400 pt-1">
                <span>
                  Fulfillment Diff:{" "}
                  <strong className="text-white">
                    {(simResults.comparison.fulfillment_diff * 100).toFixed(1)}%
                  </strong>
                </span>
                <span>
                  Benefiting Camps:{" "}
                  <strong className="text-white">{simResults.comparison.camps_improved.join(", ") || "None"}</strong>
                </span>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Tab 4: AI Decision Rationale */}
      {activeTab === "explain" && (
        <Card className="p-5 bg-white/[0.03] border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sparkles size={15} className="text-zinc-400" />
              Transparent Operational Explanations
            </h3>
            <Button
              variant="outline"
              size="sm"
              onClick={() => explainMutation.mutate()}
              disabled={explainMutation.isPending}
              className="text-xs h-7 gap-1"
            >
              <RotateCcw size={11} className={explainMutation.isPending ? "animate-spin" : ""} />
              <span>Regenerate Rationale</span>
            </Button>
          </div>

          {explainMutation.data ? (
            <div className="space-y-4 text-xs">
              <div className="p-3.5 rounded-md bg-white/[0.02] border border-white/[0.06] text-zinc-300">
                <div className="font-semibold text-white mb-1">Executive Summary</div>
                <p>{explainMutation.data.overview}</p>
              </div>

              <div className="space-y-2">
                <div className="font-semibold text-white">Critical Shortages & Bottlenecks</div>
                <div className="flex flex-wrap gap-2">
                  {explainMutation.data.bottleneck_resources.map((b: string) => (
                    <Badge key={b} variant="outline" className="text-rose-400 border-rose-400/20">
                      {b}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="p-3.5 rounded-md bg-white/[0.02] border border-white/[0.06] text-zinc-300 space-y-1">
                <div className="font-semibold text-white">Trade-Off Analysis</div>
                <p>{explainMutation.data.trade_off_rationale}</p>
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-white">Logistics Commander Recommendations</div>
                <ul className="list-disc list-inside space-y-1 text-zinc-400">
                  {explainMutation.data.recommendations_for_command.map((r: string, idx: number) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-zinc-500">
              Generating operations explanation...
            </div>
          )}
        </Card>
      )}

      {/* Tab 5: Cryptographic Audit Ledger */}
      {activeTab === "audit" && (
        <Card className="p-5 bg-white/[0.03] border-white/[0.08] space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-400" />
                Cryptographic Traceability Ledger
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Deterministic SHA-256 event chaining for plan verification and commander authorizations.
              </p>
            </div>
            {auditQuery.data?.verified && (
              <Badge variant="outline" className="text-emerald-400 border-emerald-500/20 bg-emerald-500/10 text-xs">
                Chain Intact & Verified
              </Badge>
            )}
          </div>

          <div className="overflow-x-auto rounded-lg border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-white/[0.08] bg-white/[0.03] text-zinc-400">
                <tr>
                  <th className="p-2.5">Event ID</th>
                  <th className="p-2.5">Action</th>
                  <th className="p-2.5">Plan ID</th>
                  <th className="p-2.5">Author</th>
                  <th className="p-2.5">Canonical SHA-256 Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.05] text-zinc-300">
                {auditQuery.data?.records.map((r) => (
                  <tr key={r.event_id} className="hover:bg-white/[0.02]">
                    <td className="p-2.5 font-mono text-[11px] text-zinc-400">{r.event_id}</td>
                    <td className="p-2.5 font-medium text-white">{r.event_type}</td>
                    <td className="p-2.5 font-mono text-[11px] text-zinc-400">{r.plan_id}</td>
                    <td className="p-2.5">{r.actor}</td>
                    <td className="p-2.5 font-mono text-[10px] text-zinc-400 truncate max-w-xs">{r.plan_hash}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
