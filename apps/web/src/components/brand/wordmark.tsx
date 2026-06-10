import { cn } from "@/lib/utils";

type WordmarkProps = {
  className?: string;
  size?: "sm" | "md" | "lg";
  showSpark?: boolean;
};

const sizeClasses = {
  sm: "text-xl",
  md: "text-3xl",
  lg: "text-5xl",
};

export function Wordmark({
  className,
  size = "md",
  showSpark = true,
}: WordmarkProps) {
  return (
    <span className={cn("inline-flex items-baseline gap-0", sizeClasses[size], className)}>
      <span className="font-normal text-forge">idea</span>
      <span className="font-medium text-foreground">Forge</span>
      {showSpark && (
        <span
          aria-hidden
          className="ml-[3px] inline-block size-[7px] shrink-0 translate-y-[-2px] rounded-full bg-forge"
        />
      )}
    </span>
  );
}
