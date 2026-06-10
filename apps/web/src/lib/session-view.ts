import type { SessionState } from "@/lib/api";
import { getProductUrl } from "@/lib/product-url";

const TERMINAL_STATUSES = new Set([
  "complete",
  "complete_with_warnings",
  "error",
  "rejected",
]);

export function isTerminal(status: string, v0Status?: string) {
  if (v0Status === "pending") return false;
  return TERMINAL_STATUSES.has(status);
}

export function isTerminalSuccess(status: string, v0Status?: string) {
  if (v0Status === "pending") return false;
  if (status === "complete") return true;
  if (status === "complete_with_warnings") return v0Status !== "pending";
  return false;
}

export function isBackgroundBuild(session: SessionState) {
  // A background build only exists after the operator approves the strategy and
  // the long-running deploy/UI step is still working. Never show it for a failed
  // run or a session still waiting on (or before) approval.
  if (!session.human_approved) return false;
  if (isTerminalError(session.status)) return false;
  if (session.background_build) return true;
  if (session.v0_status === "pending") return true;
  return isActiveBuild(session);
}

export function isTerminalError(status: string) {
  return status === "error" || status === "rejected";
}

export function isAwaitingApproval(session: SessionState) {
  return session.status === "awaiting_approval" && Boolean(session.pending_approval);
}

export function isActiveBuild(session: SessionState) {
  return !isTerminal(session.status, session.v0_status);
}

export function showPipeline(session: SessionState | null) {
  return Boolean(session);
}

export function showLiveProduct(session: SessionState | null) {
  if (!session) return false;
  return Boolean(
    getProductUrl(session) ||
      session.stripe_free_payment_link ||
      session.stripe_payment_link ||
      session.aws_api_url ||
      isTerminalSuccess(session.status, session.v0_status),
  );
}

export function showSessionActivity(session: SessionState | null) {
  if (!session) return false;
  const hasAudit = (session.audit_log?.length ?? 0) > 0;
  const pastCheckpoint =
    session.human_approved ||
    !["queued", "researching", "researched", "awaiting_approval"].includes(session.status);
  return hasAudit || pastCheckpoint || isTerminal(session.status, session.v0_status);
}

export function showApprovedStrategy(session: SessionState | null) {
  if (!session?.pending_approval || session.status === "awaiting_approval") return false;
  return Boolean(session.human_approved && isTerminal(session.status, session.v0_status));
}

export function showCompleteBanner(session: SessionState | null) {
  if (!session) return false;
  return isTerminalSuccess(session.status, session.v0_status);
}

export function showHero(session: SessionState | null) {
  return !session;
}
