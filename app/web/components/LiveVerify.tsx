"use client";

import { useState } from "react";

import { Dot, Pill } from "@/components/ui";
import { HAS_BACKEND, type VerifyResult, verifyLedgers } from "@/lib/api";

/**
 * The verification results elsewhere on this page were computed when the site was built. This
 * recomputes them from the chains on disk, now, on request — which is a different and stronger
 * claim. Without a backend it says so plainly rather than pretending to be live.
 */
export function LiveVerify() {
  const [state, setState] = useState<"idle" | "running">("idle");
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [error, setError] = useState("");

  async function run() {
    setState("running");
    setError("");
    try {
      setResult(await verifyLedgers());
    } catch (e) {
      setError((e as Error).message);
      setResult(null);
    } finally {
      setState("idle");
    }
  }

  if (!HAS_BACKEND) {
    return (
      <div className="border-t border-line px-5 py-4">
        <div className="flex flex-wrap items-center gap-2.5">
          <Dot accent="var(--color-faint)" />
          <span className="text-[12.5px] text-muted">
            This is the static build, so the results above were computed at build time.
          </span>
          <Pill>
            <code>make dev</code> adds a live re-check
          </Pill>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-line px-5 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={run}
          disabled={state === "running"}
          className="rounded-lg border border-line-bright px-4 py-2 text-[12.5px] font-medium text-ink transition-colors hover:bg-panel-2 disabled:opacity-50"
        >
          {state === "running" ? "walking the chains…" : "Re-verify every chain now"}
        </button>
        <span className="text-[12px] text-muted">
          Recomputes each entry&apos;s hash from the one before it, live, against the files on
          disk.
        </span>
      </div>

      {error && (
        <p className="mt-3 text-[12.5px] text-fail">
          Backend unreachable: {error}. Start it with <code className="font-mono">make dev</code>.
        </p>
      )}

      {result && (
        <div className="mt-4">
          <div className="flex flex-wrap items-center gap-2">
            <Pill
              accent={
                result.chains_intact === result.results.filter((r) => !r.tampered_copy).length
                  ? "var(--color-pass)"
                  : "var(--color-fail)"
              }
            >
              {result.chains_intact} of {result.chains_checked} chains intact
            </Pill>
            <span className="font-mono text-[10.5px] text-faint">
              at {result.checked_utc} · {result.scope}
            </span>
          </div>
          <div className="mt-2.5 grid gap-1">
            {result.results.map((r) => (
              <div key={r.run_id} className="flex items-start gap-2 font-mono text-[10.5px]">
                <span style={{ color: r.verified ? "var(--color-pass)" : "var(--color-fail)" }}>
                  {r.verified ? "✓" : "✕"}
                </span>
                <span className="text-muted">{r.run_id}</span>
                {r.tampered_copy && <span className="text-faint">(deliberately edited copy)</span>}
                {!r.verified && <span className="text-faint">— {r.message}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
