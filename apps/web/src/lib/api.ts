const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type AuditEntry = {
  agent: string;
  decision: string;
  rationale: string;
  sources: string[];
  timestamp: string;
};

export type TimeEstimate = {
  complexity: string;
  total_minutes: number;
  summary: string;
  rationale?: string;
  fast_mode?: boolean;
  phases?: Record<string, { minutes: number; label: string }>;
  models?: Record<string, string>;
};

export type SessionSummary = {
  session_id: string;
  product_name: string | null;
  status: string;
  v0_status?: string | null;
  final_url?: string | null;
  started_at?: string | null;
  updated_at?: string | null;
  user_input?: string | null;
};

export type SessionState = {
  session_id: string;
  status: string;
  current_step?: string;
  started_at?: string;
  last_heartbeat?: string;
  completed_at?: string;
  progress_log?: Array<{ message: string; timestamp: string }>;
  human_approved?: boolean;
  complexity?: string;
  time_estimate?: TimeEstimate;
  v0_status?: "pending" | "ready" | "skipped" | "error" | "fallback";
  background_build?: boolean;
  user_input: string;
  input_mode: "ideabrowser" | "idea";
  ideabrowser_url?: string;
  pending_approval?: {
    product_name: string;
    niche: string;
    icp: string;
    features: string[];
    price_points: Array<{ name: string; price: number }>;
    rationale: string;
  };
  audit_log?: AuditEntry[];
  final_url?: string;
  final_brief?: string;
  stripe_payment_link?: string;
  stripe_free_payment_link?: string;
  aws_api_url?: string;
  aws_status?: "ready" | "skipped";
  aws_skip_reason?: string;
  vercel_deployment_url?: string;
  v0_preview_url?: string;
  error?: string;
  resumable?: boolean;
  aura_template?: {
    id: string;
    name: string;
    source: string;
    mood?: string;
    layout?: string;
    reference_url?: string;
  };
  ui_builder?: "v0" | "aura_html";
};

export async function startSession(payload: {
  user_input: string;
  input_mode: "ideabrowser" | "idea";
  ideabrowser_url?: string;
}): Promise<{ session_id: string; status: string }> {
  const response = await fetch(`${API_URL}/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to start session");
  return response.json();
}

async function loadHistorySnapshot(): Promise<SessionSummary[]> {
  const response = await fetch("/history-snapshot.json", { cache: "no-store" });
  if (!response.ok) return [];
  const data = (await response.json()) as { sessions: SessionSummary[] };
  return data.sessions ?? [];
}

async function loadSessionSnapshot(sessionId: string): Promise<SessionState | null> {
  const response = await fetch(`/session-states/${sessionId}.json`, {
    cache: "no-store",
  });
  if (!response.ok) return null;
  return response.json();
}

export async function listSessions(): Promise<SessionSummary[]> {
  try {
    const response = await fetch(`${API_URL}/sessions`, { cache: "no-store" });
    if (response.ok) {
      const data = (await response.json()) as { sessions: SessionSummary[] };
      const live = data.sessions ?? [];
      if (live.length > 0) return live;
    }
  } catch {
    /* API unreachable (e.g. Vercel without tunnel) — use bundled snapshot */
  }
  return loadHistorySnapshot();
}

/** Thrown when a session is definitively absent (API reachable but 404, no snapshot). */
export class SessionNotFoundError extends Error {
  constructor(sessionId: string) {
    super(`Session ${sessionId} not found`);
    this.name = "SessionNotFoundError";
  }
}

export async function getSession(sessionId: string): Promise<SessionState> {
  let apiReachable = false;
  try {
    const response = await fetch(`${API_URL}/session/${sessionId}`, {
      cache: "no-store",
    });
    apiReachable = true;
    if (response.ok) return response.json();
    /* reachable but not ok (e.g. 404) — fall through to snapshot */
  } catch {
    /* API unreachable — fall through to bundled snapshot */
  }
  const snapshot = await loadSessionSnapshot(sessionId);
  if (snapshot) return snapshot;
  // API answered and has no such session, and no snapshot exists → it's gone.
  if (apiReachable) throw new SessionNotFoundError(sessionId);
  // API unreachable and no snapshot → transient/connectivity failure.
  throw new Error("Failed to fetch session");
}

export async function resumeSession(
  sessionId: string,
): Promise<{ session_id: string; status: string }> {
  const response = await fetch(`${API_URL}/session/${sessionId}/resume`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Failed to resume session");
  return response.json();
}

export async function approveSession(
  sessionId: string,
  approved: boolean,
  feedback = "",
): Promise<{ session_id: string; status: string }> {
  const response = await fetch(`${API_URL}/session/${sessionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved, feedback }),
  });
  if (!response.ok) throw new Error("Failed to submit approval");
  return response.json();
}
