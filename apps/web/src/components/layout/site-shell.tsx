import type { ReactNode } from "react";

import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { StatusBadge } from "@/components/brand/status-badge";
import { SiteNav } from "@/components/layout/site-nav";
import { cn } from "@/lib/utils";

type SiteShellProps = {
  children: ReactNode;
  className?: string;
};

export function SiteShell({ children, className }: SiteShellProps) {
  return (
    <div className="relative min-h-full bg-background">
      <div aria-hidden className="pointer-events-none absolute inset-0 bg-forge-grid opacity-60" />
      <div className="relative flex min-h-full flex-col">
        <header className="relative z-50 border-b border-hairline border-border/80 bg-background/95 backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-[1200px] items-center justify-between px-4 md:px-12">
            <Link href="/" className="shrink-0" aria-label="IdeaForge home">
              <Logo wordmarkSize="sm" />
            </Link>
            <SiteNav />
            <StatusBadge variant="neutral">SuperAI NEXT</StatusBadge>
          </div>
        </header>
        <main className={cn("flex flex-1 flex-col", className)}>{children}</main>
      </div>
    </div>
  );
}
