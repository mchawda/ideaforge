import { cn } from "@/lib/utils";

import { Wordmark } from "@/components/brand/wordmark";

type LogoProps = {
  className?: string;
  wordmarkSize?: "sm" | "md" | "lg";
};

/** IdeaForge logo — wordmark with orange spark dot. */
export function Logo({ className, wordmarkSize = "sm" }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center", className)}>
      <Wordmark size={wordmarkSize} showSpark />
    </span>
  );
}
