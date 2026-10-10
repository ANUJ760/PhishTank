export type UserRole = "coordinator" | "reviewer" | "viewer" | "admin";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

export type RuleType = "teacher_unavailable" | "room_unavailable" | "pin_session" | "only_qualified";
export type RuleStatus = "draft" | "confirmed" | "rejected";

export interface Evidence {
  kind: "audio" | "image" | "sheet" | "text";
  ref: string;
}

export interface Rule {
  id: string;
  type: RuleType;
  owner: string;
  params: Record<string, any>;
  status: RuleStatus;
  evidence: Evidence[];
}

export interface SessionEntity {
  id: string;
  teachers: string[];
  size: number;
  course: string;
}

export interface RoomEntity {
  name: string;
  capacity: number;
}

export interface Roster {
  sessions: SessionEntity[];
  teachers: string[];
  rooms: RoomEntity[];
}

export interface Placement {
  session_id: string;
  teacher: string;
  room: string;
  day: number;
  slot: number;
}

export interface Schedule {
  version: number;
  placements: Placement[];
}

export interface Conflict {
  rule_ids: string[];
  owners: string[];
}

export interface RelaxOption {
  id: string;
  rule_id: string;
  new_params: Record<string, any>;
  description: string;
  approver: string;
  verified: boolean;
  option_hash: string;
}

export interface Explanation {
  summary: string;
  options: RelaxOption[];
}

export type SolveStatus = "feasible" | "infeasible" | "unknown" | "error";

export interface SolveResult {
  status: SolveStatus;
  schedule: Schedule | null;
  conflict: Conflict | null;
  moved: string[];
  solve_ms: number;
  message: string;
}

export interface IngestSheetResult {
  rules: Rule[];
  cache_hit: boolean;
  attempts: number;
  tokens_used: number;
  seconds: number;
}

export interface DataDumpFileSummary {
  filename: string;
  file_type: string;
  size_bytes: number;
  status: string;
  preview: string;
}

export interface DataDumpResult {
  summary: string;
  instructions_executed: string;
  rules: Rule[];
  entities: Array<{ name: string; kind: string; details?: string }>;
  insights: string[];
  warnings: string[];
  processed_files: DataDumpFileSummary[];
}

export interface PublishResult {
  hash: string;
  tx_hash: string;
  version: number;
  json_bytes_b64: string;
  csv_bytes_b64: string;
  ics_bytes_b64: string;
}

export interface VerifyResult {
  match: boolean;
  recomputed_hash: string;
  anchored: boolean;
  error: string | null;
}

export interface ScoreboardRow {
  run: number;
  baseline_violations: number;
  baseline_details: string[];
  gecompose_violations: number;
}

export interface ScoreboardResult {
  rows: ScoreboardRow[];
}

export interface ChainEvent {
  event: string;
  block: number;
  idx: number;
  seq?: number;
  timestamp?: string;
  entity_id?: string;
  actor?: string;
  payload?: Record<string, any>;
  args: Record<string, any>;
  prev_hash?: string;
  entry_hash?: string;
}

export type LedgerEvent = ChainEvent;

export interface LedgerVerifyResult {
  valid: boolean;
  total_entries: number;
  checked_entries?: number;
  latest_hash?: string;
  failed_at_seq?: number;
  reason?: string;
  message: string;
}

export interface HealthItem {
  ok: boolean;
  detail: string;
}

export interface HealthReport {
  items: Record<string, HealthItem>;
}

export interface DashboardSummary {
  confirmed_rules_count: number;
  draft_rules_count: number;
  conflict_active: boolean;
  conflict_rule_ids: string[];
  scheduled_sessions_count: number;
  published_version: number | null;
  latest_schedule_hash: string | null;
  system_healthy: boolean;
}

// =========================================================================
// ReliefOps Types
// =========================================================================

export interface ReliefCamp {
  id: string;
  incident_id: string;
  name: string;
  location: string;
  population: number;
  vulnerable_population: number;
  storage_capacity_m3: number;
  max_weight_capacity_kg: number;
  access_status: "open" | "restricted_road" | "air_only" | "boat_only" | string;
  contact_person: string;
}

export interface ReliefResource {
  id: string;
  name: string;
  unit: string;
  category: string;
  unit_weight_kg: number;
  unit_volume_m3: number;
  priority_weight: number;
}

export interface ReliefWarehouse {
  id: string;
  name: string;
  location: string;
  is_operational: boolean;
  total_capacity_m3: number;
}

export interface ReliefInventoryItem {
  id: string;
  warehouse_id: string;
  resource_id: string;
  quantity_available: number;
  quantity_reserved: number;
}

export interface ReliefVehicle {
  id: string;
  name: string;
  vehicle_type: string;
  max_weight_kg: number;
  max_volume_m3: number;
  is_available: boolean;
  supported_access: string[];
}

export interface ReliefAllocationItem {
  camp_id: string;
  camp_name: string;
  resource_id: string;
  resource_name: string;
  requested_quantity: number;
  allocated_quantity: number;
  unmet_quantity: number;
  fulfillment_ratio: number;
  priority_classification: string;
  allocation_rationale: string;
  relevant_constraints: string[];
  shipment_details: Record<string, any>;
}

export interface ReliefPlanSummary {
  scenario_id: string;
  name: string;
  solver_status: string;
  solve_time_ms: number;
  total_requested: Record<string, number>;
  total_available: Record<string, number>;
  total_allocated: Record<string, number>;
  total_unmet: Record<string, number>;
  overall_fulfillment_rate: number;
  critical_fulfillment_rate: number;
  fairness_index: number;
  weighted_unmet_demand: number;
  validation_passed: boolean;
  validation_violations: string[];
  unresolved_shortages: any[];
}

export interface ReliefPlan {
  plan_id: string;
  incident_id: string;
  version: number;
  summary: ReliefPlanSummary;
  allocations: ReliefAllocationItem[];
  approved: boolean;
  approved_by: string | null;
  plan_hash: string;
}

export interface ReliefOverview {
  incident: any;
  camps_count: number;
  total_population: number;
  total_vulnerable_population: number;
  warehouses_count: number;
  vehicles_count: number;
  resources_count: number;
  pending_requests_count: number;
  total_items_in_stock: number;
  has_allocation_plan: boolean;
  latest_plan_id: string | null;
  latest_plan_approved: boolean;
  overall_fulfillment_rate: number;
}

export interface ReliefComparison {
  baseline_scenario_id: string;
  simulation_scenario_id: string;
  fulfillment_diff: number;
  allocated_diff: Record<string, number>;
  camps_improved: string[];
  camps_degraded: string[];
  summary_text: string;
}

export interface ReliefExplanation {
  plan_id: string;
  scenario_id: string;
  overview: string;
  key_findings: string[];
  critical_needs_assessment: string;
  bottleneck_resources: string[];
  trade_off_rationale: string;
  recommendations_for_command: string[];
  camp_explanations: Record<string, string>;
}

export interface AuditRecord {
  event_id: string;
  event_type: string;
  plan_id: string;
  timestamp: number;
  actor: string;
  plan_hash: string;
  prev_hash: string;
  notes: string;
  metadata: Record<string, any>;
}

// =========================================================================
// MedOps Types
// =========================================================================

export interface OperatingRoom {
  id: string;
  name: string;
  room_type: string;
  equipped_capabilities: string[];
  is_operational: boolean;
  turnaround_sterilization_minutes: number;
}

export interface MedicalStaff {
  id: string;
  name: string;
  role: "lead_surgeon" | "anesthesiologist" | "scrub_nurse" | string;
  specialties: string[];
  is_on_duty: boolean;
  max_consecutive_minutes: number;
}

export interface PatientCase {
  id: string;
  mrn: string;
  patient_name: string;
  age: number;
  triage_urgency: number; // 1 to 4
  specialty: string;
  estimated_duration_minutes: number;
  arrival_minute: number;
  deadline_minutes: number | null;
  required_equipment: string[];
  icu_bed_needed: boolean;
  clinical_notes: string;
  status: string;
}

export interface SurgicalScheduleItem {
  case_id: string;
  patient_mrn: string;
  patient_name: string;
  triage_urgency: string;
  specialty: string;
  or_room_id: string;
  or_room_name: string;
  start_minute: number;
  end_minute: number;
  sterilization_end_minute: number;
  lead_surgeon_id: string;
  lead_surgeon_name: string;
  anesthesiologist_id: string;
  anesthesiologist_name: string;
  scrub_nurse_id: string;
  delay_minutes: number;
  deadline_breached: boolean;
  icu_reserved: boolean;
  clinical_rationale: string;
  enforced_constraints: string[];
}

export interface HospitalORSummary {
  plan_id: string;
  hospital_name: string;
  solver_status: string;
  solve_time_ms: number;
  total_cases: number;
  scheduled_cases: number;
  emergency_cases_handled: number;
  elective_cases_bumped: number;
  overall_fulfillment_rate: number;
  resuscitation_l1_fulfillment: number;
  emergent_l2_fulfillment: number;
  mean_emergency_wait_minutes: number;
  peak_or_utilization_rate: number;
  icu_bed_usage: number;
  icu_bed_capacity: number;
  validation_passed: boolean;
  validation_violations: string[];
}

export interface HospitalORPlan {
  plan_id: string;
  hospital_id: string;
  version: number;
  summary: HospitalORSummary;
  items: SurgicalScheduleItem[];
  approved: boolean;
  approved_by: string | null;
  plan_hash: string;
}

export interface MedOpsOverview {
  hospital_id: string;
  hospital_name: string;
  operating_rooms_count: number;
  operational_rooms_count: number;
  medical_staff_count: number;
  active_staff_count: number;
  total_patient_cases: number;
  emergency_cases_count: number;
  elective_cases_count: number;
  icu_bed_capacity: number;
  has_master_plan: boolean;
  latest_plan_id: string | null;
  latest_plan_approved: boolean;
  resuscitation_fulfillment_rate: number;
  overall_fulfillment_rate: number;
}

export interface HospitalComparison {
  baseline_plan_id: string;
  simulation_plan_id: string;
  wait_time_diff_minutes: number;
  elective_bumped_diff: number;
  resuscitation_rate_diff: number;
  cases_delayed_ids: string[];
  cases_advanced_ids: string[];
  summary_text: string;
}

export interface HospitalExplanation {
  plan_id: string;
  hospital_name: string;
  overview: string;
  triage_prioritization_rationale: string;
  bumped_elective_cases_analysis: string;
  identified_bottlenecks: string[];
  clinical_recommendations: string[];
  case_rationales: Record<string, string>;
}

// =========================================================================
// Universal Solver Types
// =========================================================================

export interface UniversalResource {
  id: string;
  name: string;
  kind: "space" | "human" | "equipment" | "inventory";
  capabilities?: string[];
  capacity?: number;
  turnaround_minutes?: number;
}

export interface UniversalTask {
  id: string;
  name: string;
  priority?: number;
  duration_minutes: number;
  earliest_start_minute?: number;
  deadline_minute?: number | null;
  required_capabilities?: string[];
  precedence_task_ids?: string[];
}

export interface UniversalProblem {
  problem_id: string;
  domain: string;
  horizon_minutes?: number;
  resources: UniversalResource[];
  tasks: UniversalTask[];
}

export interface UniversalAssignment {
  task_id: string;
  task_name: string;
  priority: string;
  assigned_resource_ids: string[];
  start_minute: number;
  end_minute: number;
  turnaround_end_minute: number;
  delay_minutes: number;
  is_on_time: boolean;
  rationale: string;
}

export interface UniversalSolution {
  solution_id: string;
  problem_id: string;
  domain: string;
  solver_status: string;
  solve_time_ms: number;
  total_tasks: number;
  scheduled_tasks: number;
  unmet_tasks: number;
  overall_fulfillment_rate: number;
  critical_fulfillment_rate: number;
  assignments: UniversalAssignment[];
  unmet_task_ids: string[];
}

