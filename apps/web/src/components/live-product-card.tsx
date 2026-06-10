"use client";

import type { SessionState } from "@/lib/api";
import { getProductUrl, getProductUrlKind } from "@/lib/product-url";
import { StatusBadge } from "@/components/brand/status-badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type LiveProductCardProps = {
  session: SessionState;
};

export function LiveProductCard({ session }: LiveProductCardProps) {
  const productUrl = getProductUrl(session);
  const urlKind = getProductUrlKind(session);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Live product</CardTitle>
        <CardDescription>Marketing site, signup, and checkout when ready.</CardDescription>
      </CardHeader>
      <CardContent>
        {productUrl ? (
          <div className="space-y-3 rounded-xl border-hairline border-border bg-elevated/50 p-4 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge variant="live">Live</StatusBadge>
              {urlKind === "preview" && <StatusBadge variant="neutral">Preview</StatusBadge>}
              <span className="font-medium">Product URL</span>
            </div>
            <a
              href={productUrl}
              target="_blank"
              rel="noreferrer"
              className="break-all text-forge-light underline-offset-4 hover:underline"
            >
              {productUrl}
            </a>
            <a
              href={productUrl}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ size: "sm" })}
            >
              Open product →
            </a>
          </div>
        ) : session.stripe_free_payment_link ||
          session.stripe_payment_link ||
          session.aws_api_url ? (
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              UI still generating — Stripe and AWS are live.
            </p>
            {session.stripe_free_payment_link && (
              <div className="rounded-xl border-hairline border-border bg-elevated/50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <StatusBadge variant="live">Stripe</StatusBadge>
                  <span className="font-medium">Start free ($0)</span>
                </div>
                <a
                  href={session.stripe_free_payment_link}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all text-forge-light underline-offset-4 hover:underline"
                >
                  {session.stripe_free_payment_link}
                </a>
              </div>
            )}
            {session.stripe_payment_link && (
              <div className="rounded-xl border-hairline border-border bg-elevated/50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <StatusBadge variant="live">Stripe</StatusBadge>
                  <span className="font-medium">Paid checkout</span>
                </div>
                <a
                  href={session.stripe_payment_link}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all text-forge-light underline-offset-4 hover:underline"
                >
                  {session.stripe_payment_link}
                </a>
              </div>
            )}
            {session.aws_api_url && (
              <div className="rounded-xl border-hairline border-border bg-elevated/50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <StatusBadge variant="live">AWS</StatusBadge>
                  <span className="font-medium">API</span>
                </div>
                <a
                  href={session.aws_api_url}
                  target="_blank"
                  rel="noreferrer"
                  className="break-all text-forge-light underline-offset-4 hover:underline"
                >
                  {session.aws_api_url}
                </a>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">URL appears when deployment finishes.</p>
        )}
      </CardContent>
    </Card>
  );
}
