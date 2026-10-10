/**
 * Where the UI reads artefacts from.
 *
 * Two modes, both real. `make dev` sets NEXT_PUBLIC_API_BASE and the page reads through the
 * backend, so a reader can ask it to re-verify the hash chains live. `next build` leaves it unset
 * and the page reads the same artefacts as static files, so the production export needs no server
 * and survives having the Wi-Fi switched off. The static path is the submission path; the API is
 * the development and demo convenience.
 */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

// Three deployments, one build. `make dev` sets API_BASE to a localhost origin; on Vercel the
// `api` service is routed onto this same domain at /api, so the relative paths below reach it
// without an origin at all; a bare `next build` has neither and the page reads the committed
// artefacts as static files. All three paths are real and tested.
//
// Note there is no service binding here, and there cannot be one. This build is `output:
// "export"`, so every request below is made by the browser, not by a function -- a binding's
// injected URL is internal and resolves only inside a running function. Reaching the API from
// the browser is what the public /api rewrite in vercel.json is for.
const SAME_ORIGIN_API = process.env.NEXT_PUBLIC_HAS_API === "1";

export const HAS_BACKEND = API_BASE.length > 0 || SAME_ORIGIN_API;

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function timelineUrl(packId: string): string {
  return HAS_BACKEND ? apiUrl(`/api/timeline/${packId}`) : `/data/timeline.${packId}.json`;
}

export interface VerifyResult {
  checked_utc: string;
  scope: string;
  chains_checked: number;
  chains_intact: number;
  results: { run_id: string; tampered_copy: boolean; verified: boolean; message: string }[];
}

/** Re-walk every hash chain on disk. Only available while the backend is running. */
export async function verifyLedgers(): Promise<VerifyResult> {
  if (!HAS_BACKEND) throw new Error("no backend");
  const res = await fetch(apiUrl("/api/verify"), { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return (await res.json()) as VerifyResult;
}

export interface NarrateResult {
  pack: string;
  ok: boolean;
  exit_code: number;
  seconds: number;
  line_count: number;
  command: string;
  lines: string[];
}

/**
 * Ask the backend to run the simulator and narrate it.
 *
 * The same lines stream into the terminal running `make dev` as they are produced; what comes
 * back here is that transcript with the escape codes stripped. Only available with the backend
 * running, because it executes the pipeline rather than reading an artefact.
 */
export async function narrateRun(pack: string, full = false): Promise<NarrateResult> {
  if (!HAS_BACKEND) throw new Error("no backend");
  const res = await fetch(apiUrl("/api/narrate"), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ pack, full }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`HTTP ${res.status}: ${detail.slice(0, 300)}`);
  }
  return (await res.json()) as NarrateResult;
}
