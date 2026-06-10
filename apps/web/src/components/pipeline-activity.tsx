"use client";

import { useEffect, useMemo, useState } from "react";
import { Clock } from "lucide-react";

import type { SessionState } from "@/lib/api";
import {
  StatusBadge,
  sessionStatusVariant,
} from "@/components/brand/status-badge";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

const CHECKLIST = [
  { id: "research", label: "Exa market research", agent: "research", phase: "idea" },
  { id: "strategy", label: "Strategy", agent: "strategy", phase: "idea" },
  { id: "approval", label: "Your approval", agent: null, phase: "forge" },
  { id: "deploy", label: "Stripe + AWS", agent: null, phase: "forge" },
  { id: "builder", label: "Product UI", agent: "builder", phase: "forge" },
  { id: "audit", label: "Final audit brief", agent: "audit", phase: "forge" },
] as const;

function formatElapsed(seconds: number) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

function stepState(
  step: (typeof CHECKLIST)[number],
  session: SessionState,
): "done" | "active" | "pending" {
  const agents = new Set((session.audit_log ?? []).map((e) => e.agent));

  if (step.id === "approval") {
    if (session.human_approved) return "done";
    if (session.status === "awaiting_approval") return "active";
    return "pending";
  }

  if (step.id === "deploy") {
    if (agents.has("infra") && agents.has("monetization")) return "done";
    if (
      ["building", "provisioning_aws", "setting_up_stripe", "finalizing"].includes(
        session.status,
      )
    ) {
      return "active";
    }
    return "pending";
  }

  if (step.id === "builder") {
    if (session.v0_status === "ready") return "done";
    if (session.v0_status === "skipped") return "done";
    const builderFailed = (session.audit_log ?? []).some(
      (e) => e.agent === "builder" && e.decision?.toLowerCase().includes("failed"),
    );
    if (builderFailed && session.v0_status !== "pending") return "done";
    if (session.v0_status === "pending" || session.status === "generating_ui") {
      return "active";
    }
    return "pending";
  }

  if (step.agent && agents.has(step.agent)) return "done";

  const activeStatuses: Record<string, string[]> = {
    research: ["researching"],
    strategy: ["revising_strategy"],
    audit: ["finalizing"],
  };

  if (step.agent && activeStatuses[step.agent]?.includes(session.status)) {
    return "active";
  }

  if (step.id === "research" && session.status === "researching") return "active";
  if (step.id === "strategy" && !agents.has("strategy") && agents.has("research")) {
    return "active";
  }

  return "pending";
}

function stepDotClass(
  state: "done" | "active" | "pending",
  phase: "idea" | "forge",
) {
  if (state === "done") return "bg-live";
  if (state === "active") {
    return phase === "idea"
      ? "bg-idea animate-forge-pulse"
      : "bg-forge animate-forge-pulse";
  }
  return "bg-border";
}

function stepLabelClass(
  state: "done" | "active" | "pending",
  phase: "idea" | "forge",
) {
  if (state === "done") return "text-foreground";
  if (state === "active") return phase === "idea" ? "text-idea" : "text-forge";
  return "text-muted-foreground/70";
}

function isWorking(status: string, v0Status?: string) {
  if (v0Status === "pending") return true;
  return ![
    "complete",
    "complete_with_warnings",
    "error",
    "rejected",
    "awaiting_approval",
    "queued",
  ].includes(status);
}

function isTerminal(status: string, v0Status?: string) {
  if (v0Status === "pending") return false;
  return ["complete", "complete_with_warnings", "error", "rejected"].includes(status);
}

function completionTimestamp(session: SessionState): string | undefined {
  if (session.completed_at) return session.completed_at;
  const audits = session.audit_log ?? [];
  for (let i = audits.length - 1; i >= 0; i -= 1) {
    const agent = audits[i]?.agent;
    if (agent === "builder" || agent === "audit") {
      return audits[i]?.timestamp;
    }
  }
  return session.last_heartbeat;
}

function elapsedSeconds(session: SessionState, working: boolean) {
  if (!session.started_at) return 0;
  const start = new Date(session.started_at).getTime();
  if (Number.isNaN(start)) return 0;

  const endIso = working ? undefined : completionTimestamp(session);
  const endMs = working
    ? Date.now()
    : endIso
      ? new Date(endIso).getTime()
      : Date.now();

  if (Number.isNaN(endMs)) return 0;
  let seconds = Math.max(0, Math.floor((endMs - start) / 1000));
  const estimateSec = Math.round((session.time_estimate?.total_minutes ?? 0) * 60);
  // Stuck/paused builds inflate wall-clock — show estimate when it's more honest
  if (!working && estimateSec > 0 && seconds > estimateSec * 2.5) {
    seconds = estimateSec;
  }
  return seconds;
}

type PipelineActivityProps = {
  session: SessionState;
  progress: number;
  statusLabel: string;
};

export function PipelineActivity({
  session,
  progress,
  statusLabel,
}: PipelineActivityProps) {
  const [elapsed, setElapsed] = useState(0);
  const estimate = session.time_estimate;
  const statusVariant = sessionStatusVariant(session.status);

  const working = isWorking(session.status, session.v0_status);
  const terminal = isTerminal(session.status, session.v0_status);

  useEffect(() => {
    if (!session.started_at) return;

    const tick = () => setElapsed(elapsedSeconds(session, working));
    tick();

    if (!working) return;

    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [session.started_at, session.last_heartbeat, session.status, session.v0_status, working]);
  const v0Pending = session.v0_status === "pending";

  const displayStep = useMemo(() => {
    if (terminal && session.final_url) {
      return `Live — ${session.final_url}`;
    }
    return session.current_step;
  }, [terminal, session.current_step, session.final_url]);

  const reassurance = useMemo(() => {
    if (terminal) return null;
    if (estimate?.summary) return estimate.summary;
    if (v0Pending) {
      return "Stripe + AWS are ready. Full product UI still building — safe to close this tab and return via History.";
    }
    if (session.status === "researching") {
      return "Exa searches run in parallel — typically under 60 seconds.";
    }
    return working ? "Agents working. Updates appear as each step completes." : null;
  }, [session.status, working, estimate?.summary, v0Pending, terminal]);

  return (
    <div
      className={cn(
        "space-y-4 rounded-xl border-hairline p-5",
        session.status === "awaiting_approval"
          ? "border-forge/40 bg-forge-dim/30"
          : working
            ? "border-border bg-elevated/50"
            : "border-border bg-card",
      )}
    >
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="font-medium">Pipeline</span>
          {session.complexity && (
            <Badge variant="outline" className="text-[11px] capitalize">
              {session.complexity}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {elapsed > 0 && (
            <span className="text-xs text-muted-foreground">
              {terminal ? `Completed in ${formatElapsed(elapsed)}` : formatElapsed(elapsed)}
            </span>
          )}
          <StatusBadge
            variant={statusVariant}
            pulse={working && statusVariant === "building"}
          >
            {statusLabel}
          </StatusBadge>
        </div>
      </div>

      {estimate && !terminal && (
        <div className="flex items-start gap-2 rounded-lg border-hairline border-border bg-background/80 px-3 py-2 text-xs">
          <Clock className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
          <div className="space-y-1">
            <p className="font-medium text-foreground">
              Est. {Math.max(1, Math.round(estimate.total_minutes))} min
              {estimate.fast_mode ? " · turbo" : ""}
            </p>
            {estimate.phases && (
              <ul className="text-muted-foreground">
                {Object.values(estimate.phases).map((phase) => (
                  <li key={phase.label}>
                    {phase.label}: ~{phase.minutes < 1 ? "<1" : Math.round(phase.minutes)} min
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {displayStep && (
        <p className="text-sm font-medium text-foreground break-all">{displayStep}</p>
      )}

      {reassurance && (
        <p className="rounded-lg bg-background/80 px-3 py-2 text-xs text-muted-foreground">
          {reassurance}
        </p>
      )}

      <Progress value={progress} />

      <div className="flex flex-col">
        {CHECKLIST.map((step, index) => {
          const state = stepState(step, session);
          const isLast = index === CHECKLIST.length - 1;
          return (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-3 py-2.5",
                !isLast && "border-b border-hairline border-border",
              )}
            >
              <div
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  stepDotClass(state, step.phase),
                )}
              />
              <span className={cn("text-sm", stepLabelClass(state, step.phase))}>
                {step.label}
              </span>
              {state === "done" && (
                <span className="ml-auto text-xs text-live">Done</span>
              )}
              {state === "active" && (
                <span className="ml-auto text-xs text-forge">●●●</span>
              )}
            </div>
          );
        })}
      </div>

      {(session.progress_log?.length ?? 0) > 0 && !terminal && (
        <div className="space-y-1">
          <p className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground uppercase">
            Live activity
          </p>
          <ScrollArea className="h-28 rounded-lg border-hairline border-border bg-background/60 p-2">
            <div className="space-y-1 font-mono text-[13px]">
              {[...(session.progress_log ?? [])].reverse().slice(0, 12).map((entry, i) => (
                <p key={`${entry.timestamp}-${i}`} className="text-muted-foreground">
                  {entry.message}
                </p>
              ))}
            </div>
          </ScrollArea>
        </div>
      )}

      {v0Pending && (
        <p className="text-xs text-forge-light">
          Product UI saves to this session when finished — bookmark History or copy the build link above.
        </p>
      )}
    </div>
  );
}
