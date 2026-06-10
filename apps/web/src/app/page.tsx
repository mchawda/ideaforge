import { DashboardClient } from "@/components/dashboard-client";
import { SiteShell } from "@/components/layout/site-shell";

export default function Home() {
  return (
    <SiteShell>
      <DashboardClient />
    </SiteShell>
  );
}
