import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import {
  Cpu,
  Layers,
  Clock,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Server,
  Zap,
  ShieldCheck,
  ChevronRight,
  ListPlus,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { UniversalProblem, UniversalResource, UniversalTask, UniversalSolution } from "@/types/api";

// Preset Benchmark Scenarios
const PRESET_DOMAINS: Record<string, UniversalProblem> = {
  hpc: {
    problem_id: "HPC-WORKLOAD-01",
    domain: "High-Performance Cloud & Compute Cluster",
    horizon_minutes: 1440,
    resources: [
      {
        id: "NODE-A100-01",
        name: "GPU Node 01 (8x A100 SXM4)",
        kind: "space",
        capabilities: ["gpu", "tensor_cores", "nvlink", "cuda"],
        capacity: 1,
        turnaround_minutes: 15,
      },
      {
        id: "NODE-H100-01",
        name: "GPU Node 02 (8x H100 SXM5)",
        kind: "space",
        capabilities: ["gpu", "fp8_transformer", "infiniband"],
        capacity: 1,
        turnaround_minutes: 10,
      },
      {
        id: "NODE-CPU-HIGHMEM",
        name: "CPU Node 03 (128 Cores, 2TB RAM)",
        kind: "space",
        capabilities: ["high_mem", "cpu_bound"],
        capacity: 2,
        turnaround_minutes: 5,
      },
      {
        id: "STORAGE-FLASH-01",
        name: "NVMe Tier-1 Ultra Storage",
        kind: "equipment",
        capabilities: ["nvme_storage", "high_iops"],
        capacity: 4,
        turnaround_minutes: 0,
      },
    ],
    tasks: [
      {
        id: "JOB-LLM-PRETRAIN",
        name: "Gemma Fine-Tuning Checkpoint Run",
        priority: 1, // Critical
        duration_minutes: 240,
        earliest_start_minute: 0,
        deadline_minute: 360,
        required_capabilities: ["gpu", "tensor_cores"],
      },
      {
        id: "JOB-INFERENCE-BENCHMARK",
        name: "Real-time Latency Profiling",
        priority: 2,
        duration_minutes: 90,
        earliest_start_minute: 60,
        deadline_minute: 300,
        required_capabilities: ["gpu"],
      },
      {
        id: "JOB-EMBEDDINGS-GEN",
        name: "Vector Store Knowledge Ingestion",
        priority: 2,
        duration_minutes: 180,
        earliest_start_minute: 0,
        deadline_minute: 480,
        required_capabilities: ["high_mem"],
      },
      {
        id: "JOB-BACKUP-SNAPSHOT",
        name: "Cold Storage Snapshot Sync",
        priority: 4, // Low
        duration_minutes: 120,
        earliest_start_minute: 300,
        deadline_minute: 720,
        required_capabilities: ["nvme_storage"],
      },
    ],
  },
  aviation: {
    problem_id: "AIRPORT-GATE-01",
    domain: "Aviation Ramp & Gate Turnaround Operations",
    horizon_minutes: 720,
    resources: [
      {
        id: "GATE-A1",
        name: "Terminal 1 Gate A1 (Widebody Heavy)",
        kind: "space",
        capabilities: ["widebody", "jetbridge", "fuel_hydrant"],
        capacity: 1,
        turnaround_minutes: 30,
      },
      {
        id: "GATE-B3",
        name: "Terminal 2 Gate B3 (Narrowbody)",
        kind: "space",
        capabilities: ["narrowbody", "jetbridge"],
        capacity: 1,
        turnaround_minutes: 20,
      },
      {
        id: "TUG-CREW-ALPHA",
        name: "Heavy Pushback Tug & Ground Crew Alpha",
        kind: "human",
        capabilities: ["pushback", "ground_handling"],
        capacity: 1,
        turnaround_minutes: 10,
      },
    ],
    tasks: [
      {
        id: "FLIGHT-BA401",
        name: "Intercontinental Dreamliner Turnaround",
        priority: 1,
        duration_minutes: 90,
        earliest_start_minute: 30,
        deadline_minute: 180,
        required_capabilities: ["widebody"],
      },
      {
        id: "FLIGHT-LH204",
        name: "Regional Commuter Flight Turnaround",
        priority: 2,
        duration_minutes: 45,
        earliest_start_minute: 60,
        deadline_minute: 150,
        required_capabilities: ["narrowbody"],
      },
    ],
  },
};

export function UniversalSolverPage() {
  const [selectedPreset, setSelectedPreset] = useState<string>("hpc");
  const [problem, setProblem] = useState<UniversalProblem>(PRESET_DOMAINS["hpc"]);
  const [solution, setSolution] = useState<UniversalSolution | null>(null);

  // Quick Task Input Form State
  const [newTaskName, setNewTaskName] = useState("");
  const [newTaskDuration, setNewTaskDuration] = useState(60);
  const [newTaskPriority, setNewTaskPriority] = useState(2);
  const [newTaskCapability, setNewTaskCapability] = useState("");

  const solveMutation = useMutation({
    mutationFn: (prob: UniversalProblem) => api.universal.solve(prob),
    onSuccess: (data) => {
      setSolution(data);
      toast.success("Optimal resource allocation computed!", {
        description: `Solved ${data.scheduled_tasks}/${data.total_tasks} tasks in ${data.solve_time_ms}ms`,
      });
    },
    onError: (err: any) => {
      toast.error("Solver error", { description: err.message });
    },
  });

  const handleSelectPreset = (key: string) => {
    setSelectedPreset(key);
    if (PRESET_DOMAINS[key]) {
      setProblem(PRESET_DOMAINS[key]);
      setSolution(null);
    }
  };

  const handleAddTask = () => {
    if (!newTaskName.trim()) {
      toast.error("Please provide a task name");
      return;
    }
    const newTask: UniversalTask = {
      id: `TASK-${Date.now().toString().slice(-4)}`,
      name: newTaskName.trim(),
      priority: newTaskPriority,
      duration_minutes: Number(newTaskDuration) || 60,
      earliest_start_minute: 0,
      required_capabilities: newTaskCapability ? [newTaskCapability.trim()] : [],
    };
    setProblem((prev) => ({
      ...prev,
      tasks: [...prev.tasks, newTask],
    }));
    setNewTaskName("");
    setNewTaskCapability("");
    toast.success("Task added to problem definition");
  };

  const handleRemoveTask = (taskId: string) => {
    setProblem((prev) => ({
      ...prev,
      tasks: prev.tasks.filter((t) => t.id !== taskId),
    }));
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border/40 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
                Universal Constraint Solver
                <Badge variant="outline" className="border-indigo-500/30 text-indigo-400 bg-indigo-500/10 text-xs">
                  Global Multi-Resource Engine
                </Badge>
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Domain-agnostic scheduling & allocation across heterogeneous spaces, machines, personnel, and workloads
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            size="sm"
            onClick={() => solveMutation.mutate(problem)}
            disabled={solveMutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs shadow-md shadow-indigo-950/20"
          >
            <Play className="h-3.5 w-3.5 mr-1.5" />
            {solveMutation.isPending ? "Solving Problem..." : "Solve Optimization Problem"}
          </Button>
        </div>
      </div>

      {/* Preset Selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground">Select Domain Benchmark:</span>
        <div className="flex flex-wrap gap-2">
          {Object.entries({
            hpc: "Cloud & Compute Clusters",
            aviation: "Airport Gate Operations",
          }).map(([key, label]) => (
            <button
              key={key}
              onClick={() => handleSelectPreset(key)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                selectedPreset === key
                  ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/40"
                  : "bg-muted/30 text-muted-foreground border border-border/40 hover:bg-muted/50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Problem Specification & Input View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left Column: Resources & Add Task */}
        <div className="lg:col-span-1 space-y-4">
          <Card className="p-4 bg-card/60 border-border/40 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Server className="h-3.5 w-3.5 text-indigo-400" />
                Available Resources ({problem.resources.length})
              </h3>
            </div>
            <div className="space-y-2">
              {problem.resources.map((res: UniversalResource) => (
                <div key={res.id} className="p-2.5 rounded-md bg-muted/20 border border-border/30 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground">{res.name}</span>
                    <Badge variant="outline" className="text-[10px] uppercase font-mono border-border/60">
                      {res.kind}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1 pt-1">
                    {res.capabilities?.map((cap, i) => (
                      <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground font-mono">
                        {cap}
                      </span>
                    ))}
                  </div>
                  <div className="text-[10px] text-muted-foreground flex justify-between pt-0.5">
                    <span>Capacity: {res.capacity} units</span>
                    <span>Turnaround: +{res.turnaround_minutes}m</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Quick Add Task Form */}
          <Card className="p-4 bg-card/60 border-border/40 space-y-3">
            <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
              <ListPlus className="h-3.5 w-3.5 text-indigo-400" />
              Inject New Task
            </h3>
            <div className="space-y-2 text-xs">
              <div>
                <label className="text-[11px] text-muted-foreground block mb-1">Task Name</label>
                <Input
                  placeholder="e.g. Realtime Stream Processing"
                  value={newTaskName}
                  onChange={(e) => setNewTaskName(e.target.value)}
                  className="h-8 text-xs bg-muted/30"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[11px] text-muted-foreground block mb-1">Duration (min)</label>
                  <Input
                    type="number"
                    value={newTaskDuration}
                    onChange={(e) => setNewTaskDuration(Number(e.target.value))}
                    className="h-8 text-xs bg-muted/30 font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground block mb-1">Priority</label>
                  <select
                    aria-label="Priority"
                    value={newTaskPriority}
                    onChange={(e) => setNewTaskPriority(Number(e.target.value))}
                    className="h-8 w-full text-xs px-2 rounded-md bg-muted/30 border border-input text-foreground"
                  >
                    <option value={1}>1 - Critical Emergency</option>
                    <option value={2}>2 - High Priority</option>
                    <option value={3}>3 - Normal</option>
                    <option value={4}>4 - Low Background</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-[11px] text-muted-foreground block mb-1">Required Capability</label>
                <Input
                  placeholder="e.g. gpu or widebody"
                  value={newTaskCapability}
                  onChange={(e) => setNewTaskCapability(e.target.value)}
                  className="h-8 text-xs bg-muted/30 font-mono"
                />
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleAddTask}
                className="w-full text-xs border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/10 mt-1"
              >
                Add Task to Problem
              </Button>
            </div>
          </Card>
        </div>

        {/* Right 2 Columns: Task Backlog & Solution Assignments */}
        <div className="lg:col-span-2 space-y-4">
          {/* Active Tasks In Problem */}
          <Card className="p-4 bg-card/60 border-border/40 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5 text-indigo-400" />
                Problem Task Backlog ({problem.tasks.length})
              </h3>
              <span className="text-[11px] text-muted-foreground">Horizon: {problem.horizon_minutes} min (24h)</span>
            </div>

            <div className="divide-y divide-border/20 max-h-64 overflow-y-auto">
              {problem.tasks.map((task: UniversalTask) => (
                <div key={task.id} className="py-2 flex items-center justify-between text-xs hover:bg-muted/20 px-1 rounded transition-colors">
                  <div>
                    <div className="font-semibold text-foreground flex items-center gap-2">
                      {task.name}
                      <span className="text-[10px] font-mono text-muted-foreground">({task.id})</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground flex items-center gap-3 mt-0.5">
                      <span>Duration: {task.duration_minutes}m</span>
                      {task.deadline_minute && <span>Deadline: &lt;{task.deadline_minute}m</span>}
                      {task.required_capabilities && task.required_capabilities.length > 0 && (
                        <span>Needs: [{task.required_capabilities.join(", ")}]</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={`text-[10px] font-mono ${
                        task.priority === 1
                          ? "border-red-500/40 text-red-400 bg-red-500/10"
                          : task.priority === 2
                          ? "border-amber-500/40 text-amber-400 bg-amber-500/10"
                          : "border-border/60 text-muted-foreground"
                      }`}
                    >
                      P{task.priority}
                    </Badge>
                    <button
                      onClick={() => handleRemoveTask(task.id)}
                      className="text-muted-foreground hover:text-red-400 text-xs px-1"
                      title="Remove task"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Solution Output */}
          {solution ? (
            <Card className="p-4 bg-card/60 border-border/40 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/30 pb-3">
                <div>
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    Optimal Solution: {solution.solution_id}
                  </h3>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Solver Status: <span className="font-mono text-emerald-400 uppercase">{solution.solver_status}</span> • Compute Time: {solution.solve_time_ms}ms
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-emerald-500/40 text-emerald-400 bg-emerald-500/10 font-mono text-xs">
                    {Math.round(solution.overall_fulfillment_rate * 100)}% Fulfilled
                  </Badge>
                </div>
              </div>

              {/* Assignment Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead className="bg-muted/40 border-b border-border/40 text-muted-foreground">
                    <tr>
                      <th className="py-2 px-3 text-left font-medium">Time Window</th>
                      <th className="py-2 px-3 text-left font-medium">Task</th>
                      <th className="py-2 px-3 text-left font-medium">Assigned Resources</th>
                      <th className="py-2 px-3 text-left font-medium">On-Time</th>
                      <th className="py-2 px-3 text-left font-medium">Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/20">
                    {solution.assignments.map((asgn, idx) => (
                      <tr key={idx} className="hover:bg-muted/20">
                        <td className="py-2.5 px-3 font-mono font-medium text-foreground whitespace-nowrap">
                          {Math.floor(asgn.start_minute / 60).toString().padStart(2, "0")}:
                          {(asgn.start_minute % 60).toString().padStart(2, "0")} -{" "}
                          {Math.floor(asgn.end_minute / 60).toString().padStart(2, "0")}:
                          {(asgn.end_minute % 60).toString().padStart(2, "0")}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-foreground">
                          {asgn.task_name}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex flex-wrap gap-1">
                            {asgn.assigned_resource_ids.map((rid, rIdx) => (
                              <Badge key={rIdx} variant="outline" className="text-[10px] font-mono border-border/60">
                                {rid}
                              </Badge>
                            ))}
                          </div>
                        </td>
                        <td className="py-2.5 px-3">
                          {asgn.is_on_time ? (
                            <span className="text-emerald-400 font-medium">On-Time</span>
                          ) : (
                            <span className="text-amber-400 font-medium">+{asgn.delay_minutes}m delay</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-muted-foreground text-[11px] max-w-xs truncate">
                          {asgn.rationale}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {solution.unmet_task_ids && solution.unmet_task_ids.length > 0 && (
                <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30 text-xs text-amber-300">
                  <div className="font-semibold mb-1">Unmet Tasks Due to Capacity Constraints:</div>
                  <div className="flex flex-wrap gap-1">
                    {solution.unmet_task_ids.map((tid, i) => (
                      <Badge key={i} variant="outline" className="border-amber-500/40 text-amber-300 font-mono text-[10px]">
                        {tid}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ) : (
            <Card className="p-8 text-center bg-card/40 border-border/40 space-y-2">
              <Zap className="h-8 w-8 text-muted-foreground/60 mx-auto" />
              <div className="text-sm font-semibold text-foreground">No Optimization Executed</div>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Configure your domain resources and task requirements, then click "Solve Optimization Problem" to run the mathematical constraint solver.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
