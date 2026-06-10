"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { SectionHeader } from "@/components/brand/section-header";
import { StatusBadge, sessionStatusVariant } from "@/components/brand/status-badge";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { listSessions, type SessionSummary } from "@/lib/api";

const SESSION_KEY = "ideaforge-session-id";

const STATUS_LABELS: Record<string, string> = {
  complete: "Live",
  complete_with_warnings: "Live — UI pending",
  awaiting_approval: "Awaiting approval",
  researching: "Researching",
  error: "Error",
  rejected: "Rejected",
  generating_ui: "Building UI",
};

function formatWhen(iso?: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function statusLabel(summary: SessionSummary) {
  if (summary.v0_status === "pending") {
    if (summary.status === "generating_ui") return "Building UI (background)";
    return "Building UI — come back later";
  }
  if (summary.status === "complete_with_warnings") {
    if (!summary.final_url && summary.v0_status === "skipped") {
      return "Incomplete";
    }
    if (summary.v0_status === "pending") {
      return "Live — UI pending";
    }
    if (summary.v0_status === "error") {
      return "UI failed";
    }
  }
  return STATUS_LABELS[summary.status] ?? summary.status;
}

export function BuildsLibrary() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [builds, setBuilds] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await listSessions();
        if (!cancelled) setBuilds(data);
      } catch (err) {
        if (!cancelled) {
          toast.error(err instanceof Error ? err.message : "Could not load history");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    const timer = setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const sessionId = searchParams.get("session");
    if (!sessionId) return;
    window.localStorage.setItem(SESSION_KEY, sessionId);
    router.replace(`/?session=${sessionId}`);
  }, [searchParams, router]);

  function openProduct(url: string | null | undefined) {
    if (!url) return;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  function openDetails(sessionId: string) {
    window.localStorage.setItem(SESSION_KEY, sessionId);
    router.push(`/?session=${sessionId}`);
  }

  return (
    <div className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-8 px-4 py-10 md:px-12 md:py-14">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <SectionHeader title="History" />
          <p className="max-w-xl text-sm text-muted-foreground">
            Every forge is saved persistently. Builds continue in the background if you leave —
            reopen Details to watch progress or wait for the UI step to finish (~10–20 min).
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            window.localStorage.removeItem(SESSION_KEY);
            router.push("/?fresh=1");
          }}
          className={buttonVariants({ size: "sm" })}
        >
          New build
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading history…</p>
      ) : builds.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No forges yet</CardTitle>
            <CardDescription>Start your first forge from the Build page.</CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4">
          {builds.map((build) => (
            <Card key={build.session_id} className="transition-colors hover:border-forge/30">
              <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-foreground">
                      {build.product_name || "Untitled product"}
                    </p>
                    <StatusBadge variant={sessionStatusVariant(build.status)}>
                      {statusLabel(build)}
                    </StatusBadge>
                  </div>
                  <p className="truncate text-sm text-muted-foreground">
                    {build.user_input || build.session_id}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Updated {formatWhen(build.updated_at)}
                    {build.started_at ? ` · Started ${formatWhen(build.started_at)}` : ""}
                  </p>
                  {build.final_url && (
                    <a
                      href={build.final_url}
                      target="_blank"
                      rel="noreferrer"
                      className="block truncate text-xs text-forge-light underline-offset-4 hover:underline"
                    >
                      {build.final_url}
                    </a>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {build.session_id.slice(0, 8)}
                  </Badge>
                  {build.final_url ? (
                    <button
                      type="button"
                      onClick={() => openProduct(build.final_url)}
                      className={buttonVariants({ size: "sm" })}
                    >
                      Open
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => openDetails(build.session_id)}
                      className={buttonVariants({ size: "sm" })}
                    >
                      Open
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => openDetails(build.session_id)}
                    className={buttonVariants({ variant: "outline", size: "sm" })}
                  >
                    Details
                  </button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
