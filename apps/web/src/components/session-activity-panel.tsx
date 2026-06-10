"use client";

import type { SessionState } from "@/lib/api";
import { SectionHeader } from "@/components/brand/section-header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type SessionActivityPanelProps = {
  session: SessionState;
};

function integrationBadge(ready: boolean) {
  return ready ? (
    <Badge variant="live">Ready</Badge>
  ) : (
    <Badge variant="outline">Pending</Badge>
  );
}

export function SessionActivityPanel({ session }: SessionActivityPanelProps) {
  return (
    <section className="space-y-4" id="brief">
      <SectionHeader title="Session activity" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Audit trail</CardTitle>
            <CardDescription>Agent decisions with rationale.</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-72 pr-4">
              <div className="space-y-3">
                {(session.audit_log ?? []).map((entry, index) => (
                  <div
                    key={`${entry.timestamp}-${index}`}
                    className="rounded-lg border-hairline border-border p-3 text-sm"
                  >
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="font-medium">{entry.agent}</span>
                      <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
                    </div>
                    <p>{entry.decision}</p>
                    <p className="mt-1 text-muted-foreground">{entry.rationale}</p>
                  </div>
                ))}
                {!session.audit_log?.length && (
                  <p className="text-sm text-muted-foreground">No agent activity yet.</p>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Integrations</CardTitle>
            <CardDescription>Sponsor stack for this session.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <div className="flex items-center justify-between rounded-lg border-hairline border-border p-3">
              <span>Exa research</span>
              <Badge variant="idea">Active</Badge>
            </div>
            <div className="flex flex-col gap-2 rounded-lg border-hairline border-border p-3">
              <div className="flex items-center justify-between">
                <span>AWS infrastructure</span>
                {integrationBadge(Boolean(session.aws_api_url))}
              </div>
              {session.aws_status === "skipped" && session.aws_skip_reason && (
                <p className="text-xs text-muted-foreground">{session.aws_skip_reason}</p>
              )}
            </div>
            <div className="flex items-center justify-between rounded-lg border-hairline border-border p-3">
              <span>Stripe monetization</span>
              {integrationBadge(
                Boolean(session.stripe_free_payment_link || session.stripe_payment_link),
              )}
            </div>
            <div className="flex items-center justify-between rounded-lg border-hairline border-border p-3">
              <span>Vercel / v0 product</span>
              {integrationBadge(Boolean(session.vercel_deployment_url))}
            </div>
            {session.aura_template && (
              <div className="rounded-lg border-hairline border-border bg-elevated/40 p-3">
                <p className="text-[11px] font-medium tracking-[0.08em] text-muted-foreground uppercase">
                  Aura portfolio
                </p>
                <p className="mt-1 font-medium">{session.aura_template.name}</p>
                <p className="mt-1 text-muted-foreground">{session.aura_template.mood}</p>
                {session.ui_builder && (
                  <p className="mt-2 text-[13px] text-forge-light">
                    Builder:{" "}
                    {session.ui_builder === "aura_html" ? "aura.build remix" : "v0"}
                  </p>
                )}
                {session.aura_template?.reference_url && (
                  <a
                    href={session.aura_template.reference_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-[13px] text-forge-light underline-offset-4 hover:underline"
                  >
                    aura.build reference →
                  </a>
                )}
              </div>
            )}
            {session.final_brief && (
              <pre className="max-h-48 overflow-auto rounded-lg border-hairline border-border bg-elevated/50 p-3 font-mono text-xs whitespace-pre-wrap">
                {session.final_brief}
              </pre>
            )}
            {session.error && !session.error.startsWith("AWS skipped:") && (
              <div className="rounded-lg border-hairline border-destructive/30 bg-destructive/5 p-3 text-destructive">
                <p className="font-medium">{session.error}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Other integrations may still have completed. Retry if v0 timed out.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}
