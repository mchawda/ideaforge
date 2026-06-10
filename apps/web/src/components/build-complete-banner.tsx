"use client";

import { Check, ExternalLink } from "lucide-react";
import Link from "next/link";

import type { SessionState } from "@/lib/api";
import { getProductUrl, getProductUrlKind } from "@/lib/product-url";
import { StatusBadge } from "@/components/brand/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type BuildCompleteBannerProps = {
  session: SessionState;
  onBuildAnother: () => void;
};

export function BuildCompleteBanner({ session, onBuildAnother }: BuildCompleteBannerProps) {
  const productName = session.pending_approval?.product_name ?? "Your product";
  const productUrl = getProductUrl(session);
  const urlKind = getProductUrlKind(session);
  const uiPending = session.v0_status === "pending";
  const uiFallback = session.v0_status === "fallback" || session.ui_builder === "aura_html";

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col items-center gap-6 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-live-dim">
        <Check className="size-8 text-live" strokeWidth={2} aria-hidden />
      </div>

      <div className="space-y-2">
        <h2 className="text-2xl font-medium text-foreground md:text-3xl">
          {productName} is live
        </h2>
        <p className="text-[15px] text-muted-foreground">
          {productUrl
            ? uiFallback
              ? "Deployed as a single-page HTML fallback — not a full v0 app. Rebuild for marketing + signup + dashboard."
              : urlKind === "preview"
              ? "Preview links from v0 expire quickly — if Open product fails, refresh this page or rebuild. Stripe and AWS are wired."
              : "Your product is deployed. Stripe checkout and AWS API are ready."
            : uiPending
              ? "Stripe checkout and AWS API are ready. UI still generating."
              : "Stripe checkout and AWS API are ready."}
        </p>
      </div>

      {productUrl ? (
        <div className="w-full space-y-3 rounded-2xl border border-border bg-elevated/60 p-5 text-left shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge variant="live">Live</StatusBadge>
            {uiFallback && <StatusBadge variant="neutral">HTML fallback</StatusBadge>}
            {urlKind === "preview" && <StatusBadge variant="neutral">Preview</StatusBadge>}
          </div>
          <p className="break-all text-sm text-muted-foreground">{productUrl}</p>
          <a
            href={productUrl}
            target="_blank"
            rel="noreferrer"
            className={cn(
              buttonVariants({ size: "lg" }),
              "h-12 w-full gap-2 text-base font-medium sm:w-auto sm:min-w-[220px]",
            )}
          >
            Open product
            <ExternalLink className="size-4" aria-hidden />
          </a>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Product URL will appear here when the UI finishes generating.
        </p>
      )}

      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button variant="outline" size="sm" onClick={onBuildAnother}>
          Build another
        </Button>
        {session.final_brief && (
          <Link
            href={`/?session=${session.session_id}#brief`}
            className={buttonVariants({ variant: "ghost", size: "sm" })}
          >
            View brief
          </Link>
        )}
      </div>
    </div>
  );
}
