"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  approveSession,
  getSession,
  resumeSession,
  SessionNotFoundError,
  startSession,
  type SessionState,
} from "@/lib/api";
import {
  isAwaitingApproval,
  isTerminal,
  isTerminalError,
  showApprovedStrategy,
  showCompleteBanner,
  showHero,
  showLiveProduct,
  showPipeline,
  showSessionActivity,
} from "@/lib/session-view";
import { BackgroundBuildNotice } from "@/components/background-build-notice";
import { BuildCompleteBanner } from "@/components/build-complete-banner";
import { CommandBar } from "@/components/brand/command-bar";
import { HeroHeadline } from "@/components/brand/hero-headline";
import { SectionHeader } from "@/components/brand/section-header";
import { LiveProductCard } from "@/components/live-product-card";
import { PipelineActivity } from "@/components/pipeline-activity";
import { SessionActivityPanel } from "@/components/session-activity-panel";
import { StrategyApprovalModal } from "@/components/strategy-approval-modal";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const STEPS = [
  "queued",
  "researching",
  "researched",
  "awaiting_approval",
  "building",
  "generating_ui",
  "ui_generated",
  "provisioning_aws",
  "infra_ready",
  "setting_up_stripe",
  "monetized",
  "finalizing",
  "complete",
  "complete_with_warnings",
];

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  researching: "Researching",
  researched: "Research complete",
  awaiting_approval: "Awaiting approval",
  building: "Building",
  generating_ui: "Generating UI",
  ui_generated: "UI ready",
  ui_skipped: "UI skipped",
  provisioning_aws: "Deploying AWS",
  infra_ready: "AWS ready",
  setting_up_stripe: "Setting up Stripe",
  monetized: "Stripe ready",
  finalizing: "Writing audit brief",
  complete: "Live",
  complete_with_warnings: "Live — v0 pending",
  error: "Error",
  rejected: "Rejected",
};

const SESSION_KEY = "ideaforge-session-id";

/** True when a string is a usable web URL (scheme or bare domain), not a typed idea. */
function looksLikeUrl(value: string) {
  const v = value.trim();
  if (!v || /\s/.test(v)) return false;
  if (/^https?:\/\//i.test(v)) return true;
  return /^[a-z0-9-]+(\.[a-z0-9-]+)+(\/\S*)?$/i.test(v);
}

function headingFor(session: SessionState) {
  if (session.pending_approval?.product_name) return session.pending_approval.product_name;
  if (isTerminalError(session.status)) {
    return session.status === "rejected" ? "Strategy not approved" : "Build needs attention";
  }
  return "Building";
}

function progressFor(status: string) {
  const index = STEPS.indexOf(status);
  if (index < 0) return status === "error" ? 15 : 5;
  return Math.round(((index + 1) / STEPS.length) * 100);
}

export function IdeaForgeDashboard() {
  const searchParams = useSearchParams();
  const sessionFromUrl = searchParams.get("session");

  const [mode, setMode] = useState<"ideabrowser" | "idea">("ideabrowser");
  const [ideaUrl, setIdeaUrl] = useState("");
  const [ideaText, setIdeaText] = useState("");
  const [feedback, setFeedback] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (searchParams.get("fresh") === "1") {
      window.localStorage.removeItem(SESSION_KEY);
      window.history.replaceState({}, "", "/");
      return;
    }

    const saved = sessionFromUrl || window.localStorage.getItem(SESSION_KEY);
    if (saved) {
      setSessionId(saved);
      window.localStorage.setItem(SESSION_KEY, saved);
    }
  }, [sessionFromUrl, searchParams]);

  function handleCloseSession() {
    setSession(null);
    setSessionId(null);
    window.localStorage.removeItem(SESSION_KEY);
    window.history.replaceState({}, "", "/");
    toast.message("Build continues in the background. Reopen from History anytime.");
  }

  function handleBuildAnother() {
    handleCloseSession();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  useEffect(() => {
    if (!sessionId) return;
    const activeSessionId = sessionId;
    window.localStorage.setItem(SESSION_KEY, activeSessionId);

    function forgetStaleSession() {
      window.localStorage.removeItem(SESSION_KEY);
      window.history.replaceState({}, "", "/");
      setSession(null);
      setSessionId(null);
    }

    async function refresh() {
      const next = await getSession(activeSessionId);
      setSession(next);
      return next;
    }

    refresh().catch((err) => {
      if (err instanceof SessionNotFoundError) {
        forgetStaleSession();
        toast.message("That build is no longer available — starting fresh.");
        return;
      }
      toast.error(
        err instanceof Error ? err.message : "Could not load build — is the API running?",
      );
    });

    const timer = setInterval(async () => {
      try {
        const next = await refresh();
        if (isTerminal(next.status, next.v0_status)) clearInterval(timer);
      } catch (err) {
        clearInterval(timer);
        if (err instanceof SessionNotFoundError) forgetStaleSession();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [sessionId]);

  const progress = useMemo(
    () => progressFor(session?.status ?? "queued"),
    [session?.status],
  );

  const awaitingApproval = session ? isAwaitingApproval(session) : false;

  async function handleBuild() {
    let effectiveMode: "ideabrowser" | "idea" = mode;
    let userInput = "";
    let ideabrowserUrl: string | undefined;

    if (mode === "ideabrowser") {
      const raw = ideaUrl.trim();
      if (!raw) {
        toast.error("Paste an IdeaBrowser URL — or switch to “Your idea”.");
        return;
      }
      if (looksLikeUrl(raw)) {
        userInput = raw;
        ideabrowserUrl = raw;
      } else {
        // Operator typed an idea into the URL field — build it as an idea instead of failing.
        effectiveMode = "idea";
        userInput = raw;
        setMode("idea");
        setIdeaText(raw);
        setIdeaUrl("");
        toast.message("That's not a URL — building it as an idea instead.");
      }
    } else {
      userInput = ideaText.trim();
      if (!userInput) {
        toast.error("Describe your idea — or paste an IdeaBrowser URL.");
        return;
      }
    }

    setLoading(true);
    try {
      const started = await startSession({
        user_input: userInput,
        input_mode: effectiveMode,
        ideabrowser_url: effectiveMode === "ideabrowser" ? ideabrowserUrl : undefined,
      });
      setSessionId(started.session_id);
      setSession({ ...started, user_input: userInput, input_mode: effectiveMode } as SessionState);
      toast.message("Build started — research and strategy usually finish in a few minutes.");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Start failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResume() {
    if (!sessionId) return;
    setLoading(true);
    try {
      await resumeSession(sessionId);
      toast.message("Resuming from last checkpoint.");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Resume failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleApproval(approved: boolean) {
    if (!sessionId) return;
    setLoading(true);
    try {
      await approveSession(sessionId, approved, feedback);
      toast.message(
        approved
          ? "Approved — full product UI builds in the background (10–20 min). Safe to leave and check History later."
          : "Revising strategy.",
      );
      setFeedback("");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Approval failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div
        className={cn(
          "mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-12 px-4 py-10 md:px-12 md:py-14",
          awaitingApproval && "pointer-events-none select-none opacity-40",
        )}
        aria-hidden={awaitingApproval}
      >
        <section className="space-y-8">
          {showHero(session) && <HeroHeadline />}
          {session && showCompleteBanner(session) && (
            <BuildCompleteBanner session={session} onBuildAnother={handleBuildAnother} />
          )}
          {session && !showHero(session) && !showCompleteBanner(session) && (
            <div className="mx-auto max-w-3xl text-center">
              <p className="text-2xl font-medium text-foreground md:text-3xl">
                {headingFor(session)}
              </p>
              <p
                className={cn(
                  "mt-1 text-[15px] text-muted-foreground",
                  isTerminalError(session.status) && "text-destructive",
                )}
              >
                {isTerminalError(session.status) && session.error
                  ? session.error
                  : STATUS_LABELS[session.status] ?? session.status}
              </p>
            </div>
          )}
          {(!session || !showCompleteBanner(session)) && (
            <div className="mx-auto w-full max-w-3xl">
              <CommandBar
                mode={mode}
                onModeChange={setMode}
                ideaUrl={ideaUrl}
                onIdeaUrlChange={setIdeaUrl}
                ideaText={ideaText}
                onIdeaTextChange={setIdeaText}
                onSubmit={handleBuild}
                loading={loading}
              />
            </div>
          )}
        </section>

        {session && showPipeline(session) && (
          <section className="space-y-4">
            <BackgroundBuildNotice session={session} />
            <SectionHeader
              title="Pipeline"
              action={
                <div className="flex flex-wrap items-center gap-2">
                  {session.resumable && (
                    <Button variant="outline" size="sm" onClick={handleResume} disabled={loading}>
                      Resume build
                    </Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={handleCloseSession}>
                    Close
                  </Button>
                  <Link
                    href="/history"
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    History
                  </Link>
                </div>
              }
            />
            <PipelineActivity
              session={session}
              progress={progress}
              statusLabel={STATUS_LABELS[session.status] ?? session.status}
            />
          </section>
        )}

        {session && showApprovedStrategy(session) && session.pending_approval && (
          <section className="space-y-4">
            <SectionHeader title="Approved strategy" />
            <Card>
              <CardHeader>
                <CardTitle>{session.pending_approval.product_name}</CardTitle>
                <CardDescription>Strategy you approved for this build.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  <span className="text-muted-foreground">Niche</span>{" "}
                  {session.pending_approval.niche}
                </p>
                <p>
                  <span className="text-muted-foreground">ICP</span>{" "}
                  {session.pending_approval.icp}
                </p>
                <p>
                  <span className="text-muted-foreground">Features</span>{" "}
                  {session.pending_approval.features.join(", ")}
                </p>
                <Separator />
                <p className="text-muted-foreground">{session.pending_approval.rationale}</p>
              </CardContent>
            </Card>
          </section>
        )}

        {session && showLiveProduct(session) && (
          <section className="space-y-4">
            <SectionHeader title="Live product" />
            <LiveProductCard session={session} />
          </section>
        )}

        {session && showSessionActivity(session) && <SessionActivityPanel session={session} />}
      </div>

      {session && awaitingApproval && (
        <StrategyApprovalModal
          session={session}
          feedback={feedback}
          onFeedbackChange={setFeedback}
          onApprove={() => handleApproval(true)}
          onRevise={() => handleApproval(false)}
          loading={loading}
        />
      )}
    </>
  );
}
