import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type StatusBadgeVariant = "live" | "building" | "researching" | "error" | "neutral";

const variantStyles: Record<StatusBadgeVariant, string> = {
  live: "bg-live-dim text-live",
  building: "bg-forge-dim text-forge",
  researching: "bg-idea-dim text-idea",
  error: "bg-destructive/10 text-destructive",
  neutral: "border-hairline border-border bg-elevated text-muted-foreground",
};

type StatusBadgeProps = {
  variant: StatusBadgeVariant;
  children: ReactNode;
  pulse?: boolean;
  className?: string;
};

export function StatusBadge({
  variant,
  children,
  pulse = false,
  className,
}: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-[3px] text-[11px] font-medium tracking-normal",
        variantStyles[variant],
        className,
      )}
    >
      {variant === "live" && (
        <span className="size-1.5 shrink-0 rounded-full bg-live" aria-hidden />
      )}
      {pulse && variant === "building" && (
        <span
          className="size-1.5 shrink-0 rounded-full bg-forge animate-forge-pulse"
          aria-hidden
        />
      )}
      {children}
    </span>
  );
}

export function sessionStatusVariant(status: string): StatusBadgeVariant {
  if (status === "error" || status === "rejected") return "error";
  if (["complete", "complete_with_warnings", "monetized"].includes(status)) {
    return "live";
  }
  if (
    ["researching", "researched", "revising_strategy"].includes(status)
  ) {
    return "researching";
  }
  if (status === "queued") return "neutral";
  return "building";
}
