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
  args: Record<string, any>;
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
