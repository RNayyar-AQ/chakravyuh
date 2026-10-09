/**
 * Where the UI reads artefacts from.
 *
 * Two modes, both real. `make dev` sets NEXT_PUBLIC_API_BASE and the page reads through the
 * backend, so a judge can ask it to re-verify the hash chains live. `next build` leaves it unset
 * and the page reads the same artefacts as static files, so the production export needs no server
 * and survives having the Wi-Fi switched off. The static path is the submission path; the API is
 * the development and demo convenience.
 */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

export const HAS_BACKEND = API_BASE.length > 0;

export function timelineUrl(packId: string): string {
  return HAS_BACKEND ? `${API_BASE}/api/timeline/${packId}` : `/data/timeline.${packId}.json`;
}

export interface VerifyResult {
  checked_utc: string;
  chains_checked: number;
  chains_intact: number;
  results: { run_id: string; tampered_copy: boolean; verified: boolean; message: string }[];
}

/** Re-walk every hash chain on disk. Only available while the backend is running. */
export async function verifyLedgers(): Promise<VerifyResult> {
  if (!HAS_BACKEND) throw new Error("no backend");
  const res = await fetch(`${API_BASE}/api/verify`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return (await res.json()) as VerifyResult;
}
