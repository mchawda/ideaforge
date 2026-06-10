import { cn } from "@/lib/utils";

type LogoMarkProps = {
  className?: string;
  size?: number;
};

/** IdeaForge icon — forge anvil + spark (matches public/logo-mark.svg). */
export function LogoMark({ className, size = 32 }: LogoMarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      fill="none"
      width={size}
      height={size}
      className={cn("shrink-0", className)}
      role="img"
      aria-label="IdeaForge"
    >
      <rect width="64" height="64" rx="14" fill="#141414" />
      <path d="M18 40h28l-4 8H22l-4-8Z" fill="#f97316" />
      <path
        d="M22 40 30 18h4l8 22"
        stroke="#f97316"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M26 28h12"
        stroke="#fb923c"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <circle cx="46" cy="18" r="5" fill="#f97316" />
      <circle cx="48" cy="16" r="2" fill="#fde68a" opacity="0.9" />
    </svg>
  );
}
