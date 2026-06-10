import type { SessionState } from "@/lib/api";

/** Best URL to open the built product (production, preview, or legacy fields). */
export function getProductUrl(session: SessionState): string | undefined {
  const candidates = [
    session.final_url,
    session.vercel_deployment_url,
    session.v0_preview_url,
  ]
    .map((value) => value?.trim())
    .filter(Boolean) as string[];

  // Prefer permanent Vercel URLs over ephemeral v0 preview tokens.
  const permanent = candidates.find(
    (url) => !url.includes("vusercontent.net"),
  );
  return permanent ?? candidates[0];
}

export function isPreviewProductUrl(url: string): boolean {
  return url.includes("vusercontent.net");
}

export function getProductUrlKind(
  session: SessionState,
): "production" | "preview" | undefined {
  const url = getProductUrl(session);
  if (!url) return undefined;
  if (session.v0_preview_url && url === session.v0_preview_url.trim()) return "preview";
  if (isPreviewProductUrl(url)) return "preview";
  return "production";
}
