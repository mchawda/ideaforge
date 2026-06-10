import { Suspense } from "react";

import { BuildsLibrary } from "@/components/builds-library";
import { SiteShell } from "@/components/layout/site-shell";

export default function HistoryPage() {
  return (
    <SiteShell>
      <Suspense fallback={null}>
        <BuildsLibrary />
      </Suspense>
    </SiteShell>
  );
}
