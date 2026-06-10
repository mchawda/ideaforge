"use client";

import { Clock, History, Link2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import type { SessionState } from "@/lib/api";
import { isBackgroundBuild } from "@/lib/session-view";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type BackgroundBuildNoticeProps = {
  session: SessionState;
  className?: string;
};

export function BackgroundBuildNotice({ session, className }: BackgroundBuildNoticeProps) {
  if (!isBackgroundBuild(session)) return null;

  const v0Minutes = Math.max(
    10,
    Math.round(session.time_estimate?.phases?.v0?.minutes ?? 12),
  );
  const sessionUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/?session=${session.session_id}`
      : `/?session=${session.session_id}`;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(sessionUrl);
      toast.message("Build link copied — reopen anytime.");
    } catch {
      toast.error("Could not copy link.");
    }
  }

  return (
    <div
      className={cn(
        "rounded-2xl border border-forge/35 bg-forge-dim/40 p-5 text-left shadow-sm",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-forge/20">
          <Clock className="size-5 text-forge" aria-hidden />
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <p className="text-base font-medium text-foreground">
            Building in the background — come back later
          </p>
          <p className="text-sm text-muted-foreground">
            Full product UI typically takes{" "}
            <span className="font-medium text-foreground">{v0Minutes}–20 minutes</span>.
            Stripe and AWS may already be ready. You can{" "}
            <span className="font-medium text-foreground">close this tab</span> — the build
            continues on the server and progress is saved automatically.
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            <Link
              href={`/history?session=${session.session_id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <History className="mr-1.5 size-3.5" aria-hidden />
              Open in History
            </Link>
            <Button type="button" variant="outline" size="sm" onClick={copyLink}>
              <Link2 className="mr-1.5 size-3.5" aria-hidden />
              Copy build link
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
