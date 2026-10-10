import {
  AuditRecord,
  ChainEvent,
  DashboardSummary,
  DataDumpResult,
  Explanation,
  HealthReport,
  HospitalComparison,
  HospitalExplanation,
  HospitalORPlan,
  IngestSheetResult,
  LedgerVerifyResult,
  MedicalStaff,
  MedOpsOverview,
  OperatingRoom,
  PatientCase,
  PublishResult,
  ReliefCamp,
  ReliefComparison,
  ReliefExplanation,
  ReliefInventoryItem,
  ReliefOverview,
  ReliefPlan,
  ReliefVehicle,
  ReliefWarehouse,
  Roster,
  Rule,
  Schedule,
  ScoreboardResult,
  SolveResult,
  UniversalProblem,
  UniversalSolution,
  User,
  VerifyResult,
} from "@/types/api";

const rawApiUrl = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env as any).NEXT_PUBLIC_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  ""
);
export const API_ROOT = String(rawApiUrl).replace(/\/+$/, "").replace(/\/api\/v1$/, "");
const BASE_URL = `${API_ROOT}/api/v1`;

export interface ChatMessagePayload {
  role: "user" | "model" | "assistant";
  content: string;
}

export interface ChatResponsePayload {
  role: string;
  content: string;
  model: string;
}

export interface StreamChatOptions {
  messages: ChatMessagePayload[];
  system_prompt?: string;
  onChunk: (delta: string) => void;
  onDone?: (fullText: string) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const headers = new Headers(options.headers || {});

  // Attach token from localStorage if present
  if (typeof window !== "undefined") {
    const savedToken = localStorage.getItem("gc_token");
    if (savedToken && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${savedToken}`);
    }
  }

  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    credentials: "include",
    ...options,
    headers,
  });

  if (res.status === 204) {
    return {} as T;
  }

  let data: any = null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const message = (data && typeof data === "object" && data.detail) || res.statusText || `Request failed (${res.status})`;
    throw new ApiError(res.status, message, data);
  }

  return data as T;
}

export const api = {
  // Auth
  auth: {
    me: () => request<User>("/auth/me"),
    signIn: async (email: string, password: string) => {
      const user = await request<User>("/auth/sign-in", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (user.token && typeof window !== "undefined") {
        localStorage.setItem("gc_token", user.token);
      }
      return user;
    },
    signUp: async (name: string, email: string, password: string) => {
      const user = await request<User>("/auth/sign-up", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      if (user.token && typeof window !== "undefined") {
        localStorage.setItem("gc_token", user.token);
      }
      return user;
    },
    signOut: async () => {
      try {
        await request<void>("/auth/sign-out", {
          method: "POST",
        });
      } finally {
        if (typeof window !== "undefined") {
          localStorage.removeItem("gc_token");
        }
      }
    },
    forgotPassword: (email: string) =>
      request<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, new_password: string) =>
      request<void>("/auth/reset-password", {
        method: "POST",
        body: JSON.stringify({ token, new_password }),
      }),
  },

  // Health & Summary
  health: () => request<HealthReport>("/health"),
  dashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),

  // Roster & Rules
  roster: () => request<Roster>("/roster"),
  rules: {
    list: (status?: string) => request<Rule[]>(`/rules${status ? `?status=${status}` : ""}`),
    edit: (id: string, params?: Record<string, any>, owner?: string) =>
      request<Rule>(`/rules/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ params, owner }),
      }),
    confirm: (id: string) =>
      request<Rule>(`/rules/${id}/confirm`, {
        method: "POST",
      }),
    reject: (id: string) =>
      request<Rule>(`/rules/${id}/reject`, {
        method: "POST",
      }),
  },

  // Intake
  intake: {
    text: (text: string) =>
      request<Rule[]>("/intake/text", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    audio: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request<Rule[]>("/intake/audio", {
        method: "POST",
        body: fd,
      });
    },
    image: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request<Rule[]>("/intake/image", {
        method: "POST",
        body: fd,
      });
    },
    sheet: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request<IngestSheetResult>("/intake/sheet", {
        method: "POST",
        body: fd,
      });
    },
    dump: (files: File[], instructions: string, notes: string = "") => {
      const fd = new FormData();
      for (const f of files) {
        fd.append("files", f);
      }
      fd.append("instructions", instructions);
      fd.append("notes", notes);
      return request<DataDumpResult>("/intake/dump", {
        method: "POST",
        body: fd,
      });
    },
  },

  // Scheduling
  solve: (minimal_change: boolean = true) =>
    request<SolveResult>("/solve", {
      method: "POST",
      body: JSON.stringify({ minimal_change }),
    }),
  schedules: {
    latest: () => request<Schedule>("/schedules/latest"),
    pending: () => request<Schedule>("/schedules/pending"),
    whyCell: (sessionId: string) => request<Rule[]>(`/schedule/why/${sessionId}`),
  },

  // Conflict Resolution
  conflicts: {
    explain: (conflict: any) =>
      request<Explanation>("/conflicts/explain", {
        method: "POST",
        body: JSON.stringify({ conflict }),
      }),
    approve: (optionId: string, as_user: string) =>
      request<{ ok: boolean; tx_hash?: string; error?: string }>(`/options/${optionId}/approve`, {
        method: "POST",
        body: JSON.stringify({ as_user }),
      }),
    apply: (optionId: string) =>
      request<Rule>(`/options/${optionId}/apply`, {
        method: "POST",
      }),
  },

  // Publish & Verify
  publish: () =>
    request<PublishResult>("/publish", {
      method: "POST",
    }),
  verify: (file?: File, rawJson?: string) => {
    if (file) {
      const fd = new FormData();
      fd.append("file", file);
      return request<VerifyResult>("/verify", {
        method: "POST",
        body: fd,
      });
    }
    return request<VerifyResult>(`/verify?raw_json=${encodeURIComponent(rawJson || "")}`, {
      method: "POST",
    });
  },

  // Scoreboard & Ledger
  scoreboard: (runs: number = 5) =>
    request<ScoreboardResult>("/scoreboard", {
      method: "POST",
      body: JSON.stringify({ runs }),
    }),
  chainEvents: () => request<{ events: ChainEvent[] }>("/ledger/events"),
  ledger: {
    events: (event?: string, limit?: number) => {
      const q = new URLSearchParams();
      if (event) q.set("event", event);
      if (limit) q.set("limit", String(limit));
      const qs = q.toString();
      return request<{ events: ChainEvent[] }>(`/ledger/events${qs ? `?${qs}` : ""}`);
    },
    verify: () => request<LedgerVerifyResult>("/ledger/verify"),
  },

  // ReliefOps Disaster Operations
  reliefops: {
    overview: () => request<ReliefOverview>("/reliefops/overview"),
    camps: () => request<ReliefCamp[]>("/reliefops/camps"),
    inventory: () => request<ReliefInventoryItem[]>("/reliefops/inventory"),
    warehouses: () => request<ReliefWarehouse[]>("/reliefops/warehouses"),
    vehicles: () => request<ReliefVehicle[]>("/reliefops/vehicles"),
    requests: () => request<any[]>("/reliefops/requests"),
    optimize: (scenario_name: string = "Optimal Supply Allocation") =>
      request<ReliefPlan>("/reliefops/optimize", {
        method: "POST",
        body: JSON.stringify({ scenario_name }),
      }),
    latestPlan: () => request<ReliefPlan>("/reliefops/plan/latest"),
    getPlan: (id: string) => request<ReliefPlan>(`/reliefops/plan/${id}`),
    simulate: (delta: any, scenario_name?: string) =>
      request<{ simulation_plan: ReliefPlan; comparison: ReliefComparison }>("/reliefops/simulate", {
        method: "POST",
        body: JSON.stringify({ delta, scenario_name }),
      }),
    explain: (plan_id?: string) =>
      request<ReliefExplanation>("/reliefops/explain", {
        method: "POST",
        body: JSON.stringify({ plan_id }),
      }),
    approve: (plan_id: string, approved_by: string, notes?: string) =>
      request<AuditRecord>("/reliefops/approve", {
        method: "POST",
        body: JSON.stringify({ plan_id, approved_by, notes }),
      }),
    audit: () => request<{ verified: boolean; message: string; records: AuditRecord[] }>("/reliefops/audit"),
    seed: () => request<{ ok: boolean; message: string }>("/reliefops/demo/seed", { method: "POST" }),
  },

  // MedOps Hospital Emergency Surgical Theatres
  medops: {
    overview: () => request<MedOpsOverview>("/medops/overview"),
    rooms: () => request<OperatingRoom[]>("/medops/rooms"),
    staff: () => request<MedicalStaff[]>("/medops/staff"),
    cases: () => request<PatientCase[]>("/medops/cases"),
    optimize: (plan_id?: string) =>
      request<HospitalORPlan>("/medops/optimize", {
        method: "POST",
        body: JSON.stringify({ plan_id }),
      }),
    latestPlan: () => request<HospitalORPlan>("/medops/plan/latest"),
    getPlan: (id: string) => request<HospitalORPlan>(`/medops/plan/${id}`),
    simulate: (delta: any) =>
      request<{ simulation_plan: HospitalORPlan; comparison: HospitalComparison }>("/medops/simulate", {
        method: "POST",
        body: JSON.stringify({ delta }),
      }),
    explain: (plan_id?: string) =>
      request<HospitalExplanation>("/medops/explain", {
        method: "POST",
        body: JSON.stringify({ plan_id }),
      }),
    approve: (plan_id: string, approved_by: string, notes?: string) =>
      request<AuditRecord>("/medops/approve", {
        method: "POST",
        body: JSON.stringify({ plan_id, approved_by, notes }),
      }),
    audit: () => request<{ verified: boolean; message: string; records: AuditRecord[] }>("/medops/audit"),
    seed: () => request<{ ok: boolean; message: string }>("/medops/demo/seed", { method: "POST" }),
  },

  // Universal Global Constraint Solver
  universal: {
    solve: (problem: UniversalProblem) =>
      request<UniversalSolution>("/universal/solve", {
        method: "POST",
        body: JSON.stringify({ problem }),
      }),
  },

  // Demo management
  demo: {
    seed: () => request<{ ok: boolean; message: string }>("/demo/seed", { method: "POST" }),
    reset: () => request<{ ok: boolean; message: string }>("/demo/reset", { method: "POST" }),
  },

  // Gemma 4 via Gemini API Chat Client
  chat: {
    send: async (
      messages: ChatMessagePayload[],
      system_prompt?: string
    ): Promise<ChatResponsePayload> => {
      const url = `${API_ROOT}/api/chat`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ messages, stream: false, system_prompt }),
      });
      if (!res.ok) {
        let errData: any = null;
        try {
          errData = await res.json();
        } catch {
          // ignore non-json error responses
        }
        const msg =
          (errData && (errData.detail || errData.error || errData.message)) ||
          res.statusText ||
          `Chat request failed (${res.status})`;
        throw new ApiError(res.status, msg, errData);
      }
      return res.json();
    },

    stream: async ({
      messages,
      system_prompt,
      onChunk,
      onDone,
      onError,
      signal,
    }: StreamChatOptions): Promise<string> => {
      const url = `${API_ROOT}/api/chat`;
      let accumulatedText = "";
      try {
        const res = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ messages, stream: true, system_prompt }),
          signal,
        });

        if (!res.ok) {
          let errData: any = null;
          try {
            errData = await res.json();
          } catch {
            // ignore non-json error responses
          }
          const msg =
            (errData && (errData.detail || errData.error || errData.message)) ||
            res.statusText ||
            `Streaming failed (${res.status})`;
          const err = new ApiError(res.status, msg, errData);
          if (onError) onError(err);
          throw err;
        }

        if (!res.body) {
          throw new Error("Streaming is not supported in this browser environment.");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith(":")) continue;

            if (trimmed.startsWith("data: ")) {
              const dataStr = trimmed.slice(6).trim();
              if (dataStr === "[DONE]") {
                continue;
              }
              try {
                const parsed = JSON.parse(dataStr);
                if (parsed.delta) {
                  accumulatedText += parsed.delta;
                  onChunk(parsed.delta);
                } else if (parsed.error) {
                  const err = new Error(parsed.detail || parsed.error);
                  if (onError) onError(err);
                  throw err;
                }
              } catch {
                // Ignore SSE framing json parse errors
              }
            } else if (trimmed.startsWith("event: error")) {
              // Handled by inner JSON data error chunk
            }
          }
        }

        if (onDone) onDone(accumulatedText);
        return accumulatedText;
      } catch (err: any) {
        if (err.name === "AbortError") {
          return accumulatedText;
        }
        if (onError) onError(err);
        throw err;
      }
    },
  },
};

