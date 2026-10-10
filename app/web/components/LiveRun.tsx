"use client";

import { useEffect, useRef, useState } from "react";

import { Panel, PanelHead, Pill } from "@/components/ui";
import { HAS_BACKEND, narrateRun, type NarrateResult } from "@/lib/api";
import { PACK_ACCENT } from "@/lib/format";

/** Y.3172 node letter -> the colour the terminal uses for it, so both tell the same story. */
const NODE_COLOUR: Record<string, string> = {
  SRC: "#4aa8ff",
  C: "#38bdf8",
  PP: "#2dd4a7",
  M: "#c084fc",
  P: "#f0b429",
  D: "var(--color-brand)",
  SINK: "#fb7185",
};

const WORD_COLOUR: [RegExp, string][] = [
  [/\bALLOW\b/, "var(--color-allow)"],
  [/\bBLOCK(ED)?\b/, "var(--color-fail)"],
  [/\bNEEDS_HUMAN\b|\bHELD\b|\bDEFERRED\b/, "var(--color-human)"],
  [/\bPASS\b|\bVERIFIED\b|\bEXECUTED\b/, "var(--color-pass)"],
  [/\bFAIL\b|\bBROKEN\b|\bMISMATCH\b/, "var(--color-fail)"],
];

/** One transcript line, coloured the way the terminal coloured it. */
function Line({ text }: { text: string }) {
  const tag = /^\s{2}\[(SRC|C|PP|M|P|D|SINK)\s*\]/.exec(text);
  const isStage = text.startsWith("━━━ STAGE");
  const isBanner = /^[═]+$/.test(text.trim()) || text.startsWith("  CHAKRAVYUH");
  const isTick = /^\s{2}T\+\d/.test(text);
  const isQuote = text.includes("│ ");

  if (!text.trim()) return <div className="h-3" />;

  if (isStage) {
    return (
      <div className="mt-4 mb-1 font-semibold" style={{ color: "#67e8f9" }}>
        {text}
      </div>
    );
  }
  if (isBanner) {
    return <div style={{ color: "var(--color-faint)" }}>{text}</div>;
  }
  if (isTick) {
    return (
      <div className="mt-3 font-semibold text-ink">
        {text}
      </div>
    );
  }
  if (isQuote) {
    return <div style={{ color: "#94a3b8" }}>{text}</div>;
  }

  if (tag) {
    const colour = NODE_COLOUR[tag[1]] ?? "var(--color-muted)";
    const rest = text.slice(tag[0].length);
    const hit = WORD_COLOUR.find(([re]) => re.test(rest));
    return (
      <div>
        <span style={{ color: colour, fontWeight: 600 }}>{tag[0]}</span>
        <span style={{ color: hit ? hit[1] : "var(--color-ink)" }}>{rest}</span>
      </div>
    );
  }

  const hit = WORD_COLOUR.find(([re]) => re.test(text));
  return <div style={{ color: hit ? hit[1] : "var(--color-muted)" }}>{text}</div>;
}

/**
 * The button that runs the backend.
 *
 * It does not fetch a precomputed artefact. It asks the API to execute
 * `app/scripts/narrate_run.py`, which runs the retriever, compiles the pack, simulates the
 * cyclone and then reads back the hash-chained ledger that run just wrote. The same lines
 * appear in the terminal running `make dev` as they are produced.
 */
export function LiveRun({ packs }: { packs: string[] }) {
  const [pack, setPack] = useState(packs[0] ?? "india_current");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<NarrateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const out = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (result && out.current) out.current.scrollTop = 0;
  }, [result]);

  async function go() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await narrateRun(pack));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel id="live" className="mb-6 overflow-hidden scroll-mt-28">
      <PanelHead
        kicker="Run it yourself"
        title="Execute the backend from this page"
        right={
          <span className="hidden font-mono text-[10.5px] text-faint sm:inline">
            app/scripts/narrate_run.py
          </span>
        }
      />

      <div className="border-b border-line px-5 py-4">
        <p className="max-w-3xl text-[13px] leading-relaxed text-muted">
          This button does not load a saved file. It runs the pipeline — retrieval over the
          clause store, pack compilation, the simulation, then a read-back of the
          hash-chained ledger that run wrote. Every clause is shown with its sha256, every
          proposal with the agent that made it, every verdict with the rule and clause it
          rests on. The same transcript streams into the terminal running the server.
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {packs.map((p) => (
            <button
              key={p}
              onClick={() => setPack(p)}
              disabled={busy}
              className="rounded-md border px-3 py-1.5 font-mono text-[11.5px] transition-colors disabled:opacity-50"
              style={{
                borderColor: p === pack ? (PACK_ACCENT[p] ?? "var(--color-line-bright)") : "var(--color-line)",
                color: p === pack ? (PACK_ACCENT[p] ?? "var(--color-ink)") : "var(--color-muted)",
                background:
                  p === pack
                    ? `color-mix(in srgb, ${PACK_ACCENT[p] ?? "#fff"} 12%, transparent)`
                    : "transparent",
              }}
            >
              {p}
            </button>
          ))}

          <button
            onClick={go}
            disabled={busy || !HAS_BACKEND}
            className="ml-auto rounded-lg bg-brand px-5 py-2 text-[13px] font-semibold text-ground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "running…" : "▶ Run the backend"}
          </button>
        </div>

        {!HAS_BACKEND && (
          <p className="mt-3 font-mono text-[11.5px] text-faint">
            The published site is a static export with no server, so this button is inert here.
            Clone the repo and run <span className="text-ink">make dev</span> to use it — or run{" "}
            <span className="text-ink">python app/scripts/narrate_run.py</span> directly and read
            the same transcript in your terminal.
          </p>
        )}

        {error && (
          <p className="mt-3 font-mono text-[11.5px]" style={{ color: "var(--color-fail)" }}>
            {error}
          </p>
        )}
      </div>

      {result && (
        <>
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-3">
            <Pill accent={result.ok ? "var(--color-pass)" : "var(--color-fail)"}>
              {result.ok ? "exit 0" : `exit ${result.exit_code}`}
            </Pill>
            <Pill>{result.seconds}s</Pill>
            <Pill>{result.line_count} lines</Pill>
            <span className="ml-auto truncate font-mono text-[10.5px] text-faint">
              {result.command}
            </span>
          </div>
          <div
            ref={out}
            className="max-h-[32rem] overflow-auto bg-ground px-5 py-4 font-mono text-[11.5px] leading-[1.55] whitespace-pre"
          >
            {result.lines.map((line, i) => (
              <Line key={i} text={line} />
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}
