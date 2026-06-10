import { StatusBadge } from "@/components/brand/status-badge";

export function HeroHeadline() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 text-center">
      <StatusBadge variant="building">Autonomous founder agent</StatusBadge>
      <h1 className="text-4xl font-medium tracking-tight text-foreground md:text-5xl md:leading-[1.15]">
        From idea{" "}
        <span className="text-muted-foreground">to live product in minutes.</span>
      </h1>
      <p className="max-w-xl text-[15px] text-muted-foreground">
        Browse on IdeaBrowser. Build on IdeaForge.
      </p>
    </div>
  );
}
