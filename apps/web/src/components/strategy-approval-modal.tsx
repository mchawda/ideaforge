"use client";

import { useEffect, useRef } from "react";

import type { SessionState } from "@/lib/api";
import { StatusBadge } from "@/components/brand/status-badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

type StrategyApprovalModalProps = {
  session: SessionState;
  feedback: string;
  onFeedbackChange: (value: string) => void;
  onApprove: () => void;
  onRevise: () => void;
  loading?: boolean;
};

export function StrategyApprovalModal({
  session,
  feedback,
  onFeedbackChange,
  onApprove,
  onRevise,
  loading = false,
}: StrategyApprovalModalProps) {
  const approveRef = useRef<HTMLButtonElement>(null);
  const approval = session.pending_approval;

  useEffect(() => {
    approveRef.current?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  if (!approval) return null;

  return (
    <div
      className="fixed inset-0 z-[100] overflow-y-auto overscroll-y-contain"
      role="presentation"
    >
      <div
        className="fixed inset-0 bg-background/85 backdrop-blur-sm"
        aria-hidden
      />
      <div className="relative flex min-h-full justify-center p-4 py-8 sm:py-10">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="strategy-approval-title"
          className="flex w-full max-w-[560px] max-h-[min(90dvh,880px)] flex-col overflow-hidden rounded-2xl border-hairline border-forge/40 bg-card shadow-[0_32px_96px_-24px_rgba(0,0,0,0.9)]"
        >
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
            <div className="p-6 pb-4 sm:p-8 sm:pb-4">
              <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-2">
                  <h2 id="strategy-approval-title" className="text-lg font-medium text-foreground">
                    Review your product strategy
                  </h2>
                  <StatusBadge variant="building" pulse>
                    Awaiting your approval
                  </StatusBadge>
                </div>
              </div>

              <Separator className="mb-6" />

              <p className="text-[28px] font-medium leading-tight text-forge">
                {approval.product_name}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-full border-hairline border-border bg-elevated px-3 py-1 text-[13px] text-foreground">
                  {approval.icp}
                </span>
                {approval.price_points.map((tier) => (
                  <span
                    key={tier.name}
                    className="rounded-full border-hairline border-border bg-elevated px-3 py-1 text-[13px] text-foreground"
                  >
                    ${tier.price}/mo {tier.name}
                  </span>
                ))}
              </div>

              <div className="mt-6 space-y-3 text-sm">
                <p>
                  <span className="text-muted-foreground">Niche</span>{" "}
                  <span className="text-foreground">{approval.niche}</span>
                </p>
                <ul className="space-y-1.5">
                  {approval.features.map((feature) => (
                    <li key={feature} className="flex gap-2 text-foreground">
                      <span className="text-forge" aria-hidden>
                        ●
                      </span>
                      {feature}
                    </li>
                  ))}
                </ul>
                <p className="text-[13px] leading-relaxed italic text-muted-foreground">
                  {approval.rationale}
                </p>
              </div>

              {session.aura_template && (
                <div className="mt-4 rounded-lg border-hairline border-border bg-elevated/40 p-3 text-sm">
                  <p className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground uppercase">
                    aura.build template
                  </p>
                  <p className="mt-1 font-medium">{session.aura_template.name}</p>
                  <p className="mt-1 text-muted-foreground">{session.aura_template.mood}</p>
                  {session.aura_template.reference_url && (
                    <a
                      href={session.aura_template.reference_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-[13px] text-forge-light underline-offset-4 hover:underline"
                    >
                      Preview on aura.build →
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="shrink-0 border-t border-hairline border-border bg-card p-6 pt-4 sm:p-8 sm:pt-4">
            <div className="space-y-3">
              <Textarea
                placeholder="Feedback for revisions (optional)"
                value={feedback}
                onChange={(e) => onFeedbackChange(e.target.value)}
                rows={3}
                aria-label="Revision feedback"
              />
              <div className="flex flex-wrap gap-2">
                <Button ref={approveRef} onClick={onApprove} disabled={loading}>
                  Approve — build it →
                </Button>
                <Button variant="outline" onClick={onRevise} disabled={loading}>
                  Adjust strategy
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
