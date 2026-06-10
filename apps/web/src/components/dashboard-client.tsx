"use client";

import dynamic from "next/dynamic";
import { Suspense } from "react";

const IdeaForgeDashboard = dynamic(
  () =>
    import("@/components/ideaforge-dashboard").then((mod) => mod.IdeaForgeDashboard),
  {
    ssr: false,
    loading: () => (
      <div
        className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-12 px-4 py-10 md:px-12 md:py-14"
        aria-busy="true"
        aria-label="Loading dashboard"
      >
        <div className="space-y-8">
          <div className="mx-auto h-24 max-w-3xl animate-pulse rounded-2xl bg-elevated/80" />
          <div className="mx-auto h-40 max-w-3xl animate-pulse rounded-2xl bg-elevated/60" />
        </div>
      </div>
    ),
  },
);

export function DashboardClient() {
  return (
    <Suspense fallback={<DashboardLoading />}>
      <IdeaForgeDashboard />
    </Suspense>
  );
}

function DashboardLoading() {
  return (
    <div
      className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-12 px-4 py-10 md:px-12 md:py-14"
      aria-busy="true"
      aria-label="Loading dashboard"
    >
      <div className="space-y-8">
        <div className="mx-auto h-24 max-w-3xl animate-pulse rounded-2xl bg-elevated/80" />
        <div className="mx-auto h-40 max-w-3xl animate-pulse rounded-2xl bg-elevated/60" />
      </div>
    </div>
  );
}
