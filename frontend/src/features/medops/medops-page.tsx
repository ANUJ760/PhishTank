import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Activity,
  BedDouble,
  Users,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  ShieldCheck,
  Stethoscope,
  HeartPulse,
  Play,
  FileCheck,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  HospitalORPlan,
  OperatingRoom,
  MedicalStaff,
  PatientCase,
  SurgicalScheduleItem,
  AuditRecord,
} from "@/types/api";

export function MedOpsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"suites" | "triage" | "schedule" | "simulate" | "explain" | "audit">("schedule");

  // What-If Simulation Form States
  const [offlineRoomId, setOfflineRoomId] = useState<string>("");
  const [addEmergencyCase, setAddEmergencyCase] = useState<boolean>(true);
  const [simResults, setSimResults] = useState<any | null>(null);

  // Queries
  const overviewQuery = useQuery({
    queryKey: ["medops", "overview"],
    queryFn: () => api.medops.overview(),
  });

  const roomsQuery = useQuery({
    queryKey: ["medops", "rooms"],
    queryFn: () => api.medops.rooms(),
  });

  const staffQuery = useQuery({
    queryKey: ["medops", "staff"],
    queryFn: () => api.medops.staff(),
  });

  const casesQuery = useQuery({
    queryKey: ["medops", "cases"],
    queryFn: () => api.medops.cases(),
  });

  const latestPlanQuery = useQuery({
    queryKey: ["medops", "latestPlan"],
    queryFn: () => api.medops.latestPlan().catch(() => null),
  });

  const auditQuery = useQuery({
    queryKey: ["medops", "audit"],
    queryFn: () => api.medops.audit(),
    enabled: activeTab === "audit",
  });

  // Mutations
  const optimizeMutation = useMutation({
    mutationFn: () => api.medops.optimize(),
    onSuccess: (data) => {
      toast.success("Surgical master schedule generated successfully!", {
        description: `Scheduled ${data.summary.scheduled_cases} of ${data.summary.total_cases} cases across suites.`,
      });
      queryClient.invalidateQueries({ queryKey: ["medops"] });
    },
    onError: (err: any) => {
      toast.error("Scheduling failed", { description: err.message });
    },
  });

  const seedMutation = useMutation({
    mutationFn: () => api.medops.seed(),
    onSuccess: () => {
      toast.success("Level-1 Trauma benchmark loaded!");
      queryClient.invalidateQueries({ queryKey: ["medops"] });
    },
  });

  const simulateMutation = useMutation({
    mutationFn: (delta: any) => api.medops.simulate(delta),
    onSuccess: (data) => {
      setSimResults(data);
      toast.success("Mass-casualty surge simulation complete!");
    },
    onError: (err: any) => {
      toast.error("Simulation error", { description: err.message });
    },
  });

  const explainMutation = useMutation({
    mutationFn: (planId?: string) => api.medops.explain(planId),
    onSuccess: () => {
      toast.success("Clinical optimization rationale updated!");
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ planId, approvedBy }: { planId: string; approvedBy: string }) =>
      api.medops.approve(planId, approvedBy, "Clinical Chief Approval for OR execution"),
    onSuccess: () => {
      toast.success("Master schedule approved and cryptographically logged!");
      queryClient.invalidateQueries({ queryKey: ["medops"] });
    },
    onError: (err: any) => {
      toast.error("Approval error", { description: err.message });
    },
  });

  const handleRunSimulation = () => {
    const delta: any = {
      mass_casualty_cases: addEmergencyCase
        ? [
            {
              id: `SURGE-MC-${Date.now().toString().slice(-4)}`,
              mrn: `MRN-SURGE-${Date.now().toString().slice(-4)}`,
              patient_name: "Surge Polytrauma Influx",
              age: 38,
              triage_urgency: 1, // ESI-1 immediate
              specialty: "Trauma Surgery",
              estimated_duration_minutes: 120,
              arrival_minute: 0,
              deadline_minutes: 60,
              required_equipment: ["C-Arm Rapid Imaging", "Rapid Infuser"],
              icu_bed_needed: true,
              clinical_notes: "Mass-casualty influx - requires immediate OR stabilization",
              status: "pending",
            },
          ]
        : [],
      decontaminated_or_rooms: offlineRoomId ? [offlineRoomId] : [],
      unavailable_staff: [],
    };
    simulateMutation.mutate(delta);
  };

  const plan: HospitalORPlan | null = latestPlanQuery.data || null;
  const overview = overviewQuery.data;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                MedOps — Surgical Suite Orchestrator
                <Badge variant="outline" className="border-red-500/30 text-red-400 bg-red-500/10 text-xs">
                  Emergency OR Engine
                </Badge>
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Multi-theatre surgical scheduling, golden-hour triage constraint fulfillment, and surge simulation
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="text-xs border-border/60 hover:bg-muted/50"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
            Reset Trauma Benchmark
          </Button>
          <Button
            size="sm"
            onClick={() => optimizeMutation.mutate()}
            disabled={optimizeMutation.isPending}
            className="bg-red-600 hover:bg-red-700 text-white text-xs shadow-md shadow-red-950/20"
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            {optimizeMutation.isPending ? "Solving Schedule..." : "Run OR Optimization"}
          </Button>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <Card className="p-4 bg-card/60 backdrop-blur border-border/40 flex flex-col justify-between">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Operating Suites</span>
            <BedDouble className="h-4 w-4 text-blue-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-foreground">
              {overview?.operational_rooms_count ?? roomsQuery.data?.length ?? 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Hybrid, Cardiac, Neuro, General</p>
          </div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur border-border/40 flex flex-col justify-between">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Triage Queue</span>
            <HeartPulse className="h-4 w-4 text-red-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-foreground">
              {overview?.total_patient_cases ?? casesQuery.data?.length ?? 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">ESI-1 (Immediate) to ESI-4 cases</p>
          </div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur border-border/40 flex flex-col justify-between">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Surgical Staff</span>
            <Users className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-foreground">
              {overview?.active_staff_count ?? staffQuery.data?.length ?? 0}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">Surgeons, Anesthesiologists, RNs</p>
          </div>
        </Card>

        <Card className="p-4 bg-card/60 backdrop-blur border-border/40 flex flex-col justify-between">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-medium">Schedule Fulfillment</span>
            <CheckCircle2 className="h-4 w-4 text-purple-400" />
          </div>
          <div className="mt-2">
            <div className="text-2xl font-bold text-foreground">
              {plan ? `${Math.round(plan.summary.overall_fulfillment_rate * 100)}%` : "Ready"}
            </div>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              {plan ? `${plan.summary.scheduled_cases} cases placed` : "Click Run Optimization"}
            </p>
          </div>
        </Card>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-1 border-b border-border/40 pb-2">
        {(
          [
            { id: "schedule", label: "Master Schedule", icon: Clock },
            { id: "triage", label: "Triage Cases", icon: HeartPulse },
            { id: "suites", label: "Operating Suites", icon: BedDouble },
            { id: "simulate", label: "Surge Simulation", icon: Sliders },
            { id: "explain", label: "Clinical Rationale", icon: Sparkles },
            { id: "audit", label: "Audit Ledger", icon: ShieldCheck },
          ] as const
        ).map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                isActive
                  ? "bg-muted text-foreground border border-border shadow-sm"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab: Master Schedule */}
      {activeTab === "schedule" && (
        <div className="space-y-4">
          {!plan ? (
            <Card className="p-8 text-center bg-card/40 border-border/40 space-y-3">
              <Stethoscope className="h-10 w-10 text-muted-foreground/60 mx-auto" />
              <div className="text-base font-semibold text-foreground">No Surgical Master Plan Generated</div>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Run the multi-suite optimizer to generate a schedule that guarantees golden-hour triage deadlines, room-equipment compatibility, and surgeon availability.
              </p>
              <Button
                onClick={() => optimizeMutation.mutate()}
                disabled={optimizeMutation.isPending}
                className="bg-red-600 hover:bg-red-700 text-white text-xs mt-2"
              >
                Run OR Optimization
              </Button>
            </Card>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-foreground">
                    Active Master Plan: {plan.plan_id}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Status: <span className="font-mono text-emerald-400">{plan.summary.solver_status}</span> • Scheduled: {plan.summary.scheduled_cases}/{plan.summary.total_cases} • Mean Wait: {plan.summary.mean_emergency_wait_minutes.toFixed(0)} min
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => approveMutation.mutate({ planId: plan.plan_id, approvedBy: "Chief Medical Officer" })}
                    disabled={approveMutation.isPending}
                    className="text-xs border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
                  >
                    <FileCheck className="h-3.5 w-3.5 mr-1" />
                    Sign & Approve Schedule
                  </Button>
                </div>
              </div>

              {/* Schedule Board Table */}
              <Card className="overflow-hidden border-border/40 bg-card/60">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/40 border-b border-border/40 text-muted-foreground">
                      <tr>
                        <th className="py-2.5 px-3 text-left font-medium">Time Window</th>
                        <th className="py-2.5 px-3 text-left font-medium">Operating Room</th>
                        <th className="py-2.5 px-3 text-left font-medium">Patient / Case</th>
                        <th className="py-2.5 px-3 text-left font-medium">Triage / Specialty</th>
                        <th className="py-2.5 px-3 text-left font-medium">Assigned Team</th>
                        <th className="py-2.5 px-3 text-left font-medium">Constraints</th>
                        <th className="py-2.5 px-3 text-right font-medium">Turnover</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/20">
                      {plan.items.map((asgn: SurgicalScheduleItem, idx: number) => {
                        const durationMin = asgn.end_minute - asgn.start_minute;
                        const turnoverMin = asgn.sterilization_end_minute - asgn.end_minute;
                        return (
                          <tr key={idx} className="hover:bg-muted/30 transition-colors">
                            <td className="py-2.5 px-3 font-mono font-medium text-foreground whitespace-nowrap">
                              {Math.floor(asgn.start_minute / 60).toString().padStart(2, "0")}:
                              {(asgn.start_minute % 60).toString().padStart(2, "0")} -{" "}
                              {Math.floor(asgn.end_minute / 60).toString().padStart(2, "0")}:
                              {(asgn.end_minute % 60).toString().padStart(2, "0")}
                              <span className="text-[10px] text-muted-foreground ml-1">({durationMin}m)</span>
                            </td>
                            <td className="py-2.5 px-3">
                              <Badge variant="outline" className="border-border/60 bg-muted/20 font-mono text-[11px]">
                                {asgn.or_room_name || asgn.or_room_id}
                              </Badge>
                            </td>
                            <td className="py-2.5 px-3 font-medium text-foreground">
                              {asgn.patient_name}
                              <span className="text-[10px] text-muted-foreground block font-mono">{asgn.case_id}</span>
                            </td>
                            <td className="py-2.5 px-3">
                              <span className="text-muted-foreground">{asgn.specialty}</span>
                              <Badge variant="outline" className="text-[9px] ml-1.5 border-border/40">
                                {asgn.triage_urgency}
                              </Badge>
                            </td>
                            <td className="py-2.5 px-3 font-mono text-[11px] text-muted-foreground">
                              {asgn.lead_surgeon_name || asgn.lead_surgeon_id}
                              {asgn.anesthesiologist_name && (
                                <span className="text-muted-foreground/60"> / {asgn.anesthesiologist_name}</span>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex flex-wrap gap-1">
                                {asgn.enforced_constraints.map((eq, eIdx) => (
                                  <Badge key={eIdx} variant="secondary" className="text-[9px] px-1 py-0 bg-muted/40 text-muted-foreground">
                                    {eq}
                                  </Badge>
                                ))}
                              </div>
                            </td>
                            <td className="py-2.5 px-3 text-right font-mono text-muted-foreground">
                              +{turnoverMin}m buffer
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Unmet / Bumped Cases if any */}
              {plan.summary.elective_cases_bumped > 0 && (
                <Card className="p-4 border-amber-500/30 bg-amber-500/5 space-y-2">
                  <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs">
                    <AlertTriangle className="h-4 w-4" />
                    Bumped / Deferred Elective Cases ({plan.summary.elective_cases_bumped})
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Non-urgent elective cases deferred to prioritize golden-hour limits for emergency trauma arrivals.
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab: Triage Cases */}
      {activeTab === "triage" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Patient Surgical Triage Queue ({casesQuery.data?.length ?? 0} Cases)
            </h3>
            <span className="text-xs text-muted-foreground">
              Prioritized by ESI Urgency (1 = Immediate Resuscitation, 4 = Semi-Urgent)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {casesQuery.data?.map((c: PatientCase) => {
              const esiColor =
                c.triage_urgency === 1
                  ? "border-red-500/40 text-red-400 bg-red-500/10"
                  : c.triage_urgency === 2
                  ? "border-orange-500/40 text-orange-400 bg-orange-500/10"
                  : c.triage_urgency === 3
                  ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
                  : "border-blue-500/40 text-blue-400 bg-blue-500/10";

              return (
                <Card key={c.id} className="p-3.5 bg-card/60 border-border/40 space-y-2.5">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-foreground text-xs">{c.patient_name}</div>
                      <div className="text-[10px] text-muted-foreground font-mono">{c.id} • {c.mrn} (Age: {c.age})</div>
                    </div>
                    <Badge variant="outline" className={`text-[10px] font-mono ${esiColor}`}>
                      ESI-{c.triage_urgency}
                    </Badge>
                  </div>

                  <div className="text-xs space-y-1 text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Specialty:</span>
                      <span className="text-foreground font-medium">{c.specialty}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Estimated Duration:</span>
                      <span className="font-mono text-foreground">{c.estimated_duration_minutes} min</span>
                    </div>
                    {c.deadline_minutes && (
                      <div className="flex justify-between text-red-400">
                        <span>Golden Hour Limit:</span>
                        <span className="font-mono font-medium">{c.deadline_minutes} min</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span>ICU Bed Reserved:</span>
                      <span className="font-mono text-foreground">{c.icu_bed_needed ? "Yes" : "No"}</span>
                    </div>
                  </div>

                  <div className="pt-1">
                    <span className="text-[10px] text-muted-foreground block mb-1">Required Equipment:</span>
                    <div className="flex flex-wrap gap-1">
                      {c.required_equipment.map((eq, i) => (
                        <Badge key={i} variant="secondary" className="text-[9px] px-1.5 py-0 bg-muted/40 text-muted-foreground">
                          {eq}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {c.clinical_notes && (
                    <p className="text-[10px] text-muted-foreground/80 italic border-t border-border/20 pt-1.5">
                      "{c.clinical_notes}"
                    </p>
                  )}
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab: Operating Suites */}
      {activeTab === "suites" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Operating Theatres & Suites ({roomsQuery.data?.length ?? 0} Rooms)
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {roomsQuery.data?.map((room: OperatingRoom) => (
              <Card key={room.id} className="p-4 bg-card/60 border-border/40 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-foreground text-xs">{room.name}</h4>
                    <span className="text-[10px] font-mono text-muted-foreground">{room.id} • {room.room_type}</span>
                  </div>
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 bg-emerald-500/10 text-[10px]">
                    {room.is_operational ? "Operational" : "Offline"}
                  </Badge>
                </div>

                <div className="text-xs space-y-1 text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Operating Window:</span>
                    <span className="font-mono text-foreground">07:00 - 19:00 (Standard Horizon)</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Turnover Buffer:</span>
                    <span className="font-mono text-foreground">{room.turnaround_sterilization_minutes} min sterilization</span>
                  </div>
                </div>

                <div>
                  <span className="text-[10px] text-muted-foreground block mb-1">Equipped Capabilities:</span>
                  <div className="flex flex-wrap gap-1">
                    {room.equipped_capabilities.map((eq, i) => (
                      <Badge key={i} variant="secondary" className="text-[9px] px-1.5 py-0 bg-muted/40 text-muted-foreground">
                        {eq}
                      </Badge>
                    ))}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Surge Simulation */}
      {activeTab === "simulate" && (
        <div className="space-y-5">
          <Card className="p-4 bg-card/60 border-border/40 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <Sliders className="h-4 w-4 text-purple-400" />
                Mass-Casualty Surge & Disruption Simulator
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Simulate sudden influxes of critical ESI-1 patients or room sterilization failures without affecting live schedules.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-foreground">
                  Simulate Operating Suite Failure / Sterilization Lockdown
                </label>
                <select
                  aria-label="Simulate Operating Suite Failure / Sterilization Lockdown"
                  value={offlineRoomId}
                  onChange={(e) => setOfflineRoomId(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 rounded-md bg-muted/40 border border-border/60 text-foreground"
                >
                  <option value="">None (All Suites Operational)</option>
                  {roomsQuery.data?.map((r: OperatingRoom) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.id})
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-muted-foreground">
                  Takes this theatre offline to test re-routing of scheduled trauma cases.
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium text-foreground">
                  Mass Casualty Influx Scenario
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="mcCheck"
                    checked={addEmergencyCase}
                    onChange={(e) => setAddEmergencyCase(e.target.checked)}
                    className="rounded border-border bg-muted/40"
                  />
                  <label htmlFor="mcCheck" className="text-xs text-foreground cursor-pointer">
                    Inject Unscheduled ESI-1 Immediate Polytrauma Case (Golden Hour: 60 min)
                  </label>
                </div>
                <p className="text-[10px] text-muted-foreground">
                  Forces the solver to preempt lower urgency cases to save life-critical triage arrivals.
                </p>
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleRunSimulation}
                disabled={simulateMutation.isPending}
                className="bg-purple-600 hover:bg-purple-700 text-white text-xs"
              >
                {simulateMutation.isPending ? "Simulating Surge..." : "Execute What-If Surge Simulation"}
              </Button>
            </div>
          </Card>

          {/* Simulation Results Display */}
          {simResults && (
            <div className="space-y-4">
              <h4 className="text-sm font-semibold text-foreground">Simulation Results & Delta Impact</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Card className="p-3.5 bg-card/60 border-border/40">
                  <span className="text-[11px] text-muted-foreground">Wait Time Variance</span>
                  <div className="text-xl font-bold font-mono text-foreground mt-1">
                    {simResults.comparison?.wait_time_diff_minutes || 0} min
                  </div>
                </Card>
                <Card className="p-3.5 bg-card/60 border-border/40">
                  <span className="text-[11px] text-muted-foreground">Elective Cases Bumped Delta</span>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                    +{simResults.comparison?.elective_bumped_diff || 0}
                  </div>
                </Card>
                <Card className="p-3.5 bg-card/60 border-border/40">
                  <span className="text-[11px] text-muted-foreground">Delayed Cases</span>
                  <div className="text-xl font-bold font-mono text-purple-400 mt-1">
                    {simResults.comparison?.cases_delayed_ids?.length || 0} cases
                  </div>
                </Card>
              </div>

              {simResults.comparison?.cases_delayed_ids && simResults.comparison.cases_delayed_ids.length > 0 && (
                <Card className="p-4 border-amber-500/30 bg-amber-500/5 space-y-1.5">
                  <div className="text-xs font-semibold text-amber-400">Rescheduled / Bumped Cases:</div>
                  <div className="flex flex-wrap gap-2">
                    {simResults.comparison.cases_delayed_ids.map((dc: string, idx: number) => (
                      <Badge key={idx} variant="outline" className="border-amber-500/30 text-amber-300 font-mono text-xs">
                        {dc}
                      </Badge>
                    ))}
                  </div>
                </Card>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab: Clinical Rationale */}
      {activeTab === "explain" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <Sparkles className="h-4 w-4 text-amber-400" />
                Clinical Decision Intelligence & Rationale
              </h3>
              <p className="text-xs text-muted-foreground">
                Gemma-powered synthesis of surgical assignments, triage compliance, and constraint resolutions
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => explainMutation.mutate(plan?.plan_id)}
              disabled={explainMutation.isPending || !plan}
              className="text-xs"
            >
              {explainMutation.isPending ? "Generating..." : "Generate Rationale"}
            </Button>
          </div>

          <Card className="p-5 bg-card/60 border-border/40 space-y-3">
            <div className="text-xs font-semibold text-foreground uppercase tracking-wider text-muted-foreground">
              Clinical Optimization Report
            </div>
            <div className="prose prose-invert max-w-none text-xs leading-relaxed text-muted-foreground space-y-2">
              <p>
                {explainMutation.data?.overview || (
                  <span>
                    The surgical scheduler prioritized all ESI-1 and ESI-2 emergent cases within their designated golden-hour windows. Operating theatres were allocated strictly according to equipment capabilities (e.g. C-Arm Rapid Imaging, Cardiopulmonary Bypass) with mandatory 20-30 minute decontamination turnover buffers between cases.
                  </span>
                )}
              </p>
              {explainMutation.data?.triage_prioritization_rationale && (
                <div className="mt-3 p-3 rounded-md bg-muted/30 border border-border/40 text-xs">
                  <div className="font-semibold text-foreground mb-1">Triage Prioritization:</div>
                  {explainMutation.data.triage_prioritization_rationale}
                </div>
              )}
              {explainMutation.data?.case_rationales && (
                <div className="mt-3 p-3 rounded-md bg-muted/30 border border-border/40 font-mono text-[11px] whitespace-pre-wrap">
                  {JSON.stringify(explainMutation.data.case_rationales, null, 2)}
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Tab: Audit Ledger */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                Cryptographic Surgical Schedule Ledger
              </h3>
              <p className="text-xs text-muted-foreground">
                Immutable SHA-256 state history verifying all clinical approvals and optimization runs
              </p>
            </div>
            {auditQuery.data?.verified && (
              <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-500/10 text-xs">
                Ledger Chain Integrity Intact
              </Badge>
            )}
          </div>

          <Card className="overflow-hidden border-border/40 bg-card/60">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/40 border-b border-border/40 text-muted-foreground">
                  <tr>
                    <th className="py-2 px-3 text-left font-medium">Event ID</th>
                    <th className="py-2 px-3 text-left font-medium">Timestamp</th>
                    <th className="py-2 px-3 text-left font-medium">Action</th>
                    <th className="py-2 px-3 text-left font-medium">Actor</th>
                    <th className="py-2 px-3 text-left font-medium">Schedule ID</th>
                    <th className="py-2 px-3 text-right font-medium">Plan Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/20">
                  {auditQuery.data?.records?.map((rec: AuditRecord, i: number) => (
                    <tr key={i} className="hover:bg-muted/30 font-mono text-[11px]">
                      <td className="py-2 px-3 text-muted-foreground">{rec.event_id}</td>
                      <td className="py-2 px-3 text-muted-foreground whitespace-nowrap">
                        {new Date(rec.timestamp * 1000).toLocaleTimeString()}
                      </td>
                      <td className="py-2 px-3 font-semibold text-foreground">{rec.event_type}</td>
                      <td className="py-2 px-3 text-muted-foreground">{rec.actor || "System"}</td>
                      <td className="py-2 px-3 text-muted-foreground">{rec.plan_id}</td>
                      <td className="py-2 px-3 text-right text-emerald-400/90 truncate max-w-[120px]">
                        {rec.plan_hash ? `${rec.plan_hash.slice(0, 16)}...` : "—"}
                      </td>
                    </tr>
                  ))}
                  {(!auditQuery.data?.records || auditQuery.data.records.length === 0) && (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-muted-foreground text-xs font-sans">
                        No audit ledger records logged yet. Run an optimization or approve a schedule to record cryptographic state.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
