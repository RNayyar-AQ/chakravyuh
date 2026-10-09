"use client";

import { useMemo, useState } from "react";

import { Panel, Pill } from "@/components/ui";
import { PACK_SHORT } from "@/lib/format";
import type { GapRow } from "@/lib/types";

const TYPE_ACCENT: Record<string, string> = {
  policy: "#f0b429",
  coordination: "#4aa8ff",
  execution: "#fb7185",
  standards: "#c084fc",
};

/** Confidence is COMPUTED from clause provenance upstream. The UI only displays it. */
const CONFIDENCE_NOTE: Record<string, string> = {
  certain: "every cited clause carries the instrument's own words",
  likely: "at least one cited clause is still a model-written summary",
  unverified: "the primary text behind this finding has not been obtained",
};

function ids(s: string): string[] {
  return (s || "").split(/\s+/).filter(Boolean);
}

export function GapExplorer({ rows }: { rows: GapRow[] }) {
  const [type, setType] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const types = useMemo(
    () => [...new Set(rows.map((r) => r.gap_type).filter(Boolean))].sort(),
    [rows],
  );
  const shown = type ? rows.filter((r) => r.gap_type === type) : rows;

  return (
    <>
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <button
          onClick={() => setType("")}
          className={`rounded-md border px-3 py-1.5 font-mono text-[11px] transition-colors ${
            type === "" ? "border-line-bright bg-panel-2 text-ink" : "border-line text-faint"
          }`}
        >
          all {rows.length}
        </button>
        {types.map((t) => {
          const n = rows.filter((r) => r.gap_type === t).length;
          const on = type === t;
          return (
            <button
              key={t}
              onClick={() => setType(on ? "" : t)}
              className="rounded-md border px-3 py-1.5 font-mono text-[11px] transition-colors"
              style={{
                color: on ? TYPE_ACCENT[t] : "var(--color-faint)",
                borderColor: on
                  ? `color-mix(in srgb, ${TYPE_ACCENT[t]} 48%, transparent)`
                  : "var(--color-line)",
                background: on ? `color-mix(in srgb, ${TYPE_ACCENT[t]} 10%, transparent)` : "transparent",
              }}
            >
              {t} {n}
            </button>
          );
        })}
      </div>

      <div className="grid gap-3">
        {shown.map((r) => {
          const isOpen = open === r.gap_id;
          const accent = TYPE_ACCENT[r.gap_type] ?? "var(--color-muted)";
          const unverified = ids(r.unverified_clause_ids);
          return (
            <Panel key={r.gap_id} className="overflow-hidden">
              <button
                onClick={() => setOpen(isOpen ? null : r.gap_id)}
                className="flex w-full items-start gap-4 px-5 py-4 text-left hover:bg-panel-2/50"
              >
                <span
                  className="mt-1 h-10 w-1 shrink-0 rounded-full"
                  style={{ background: accent }}
                />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11.5px] font-semibold text-ink">{r.gap_id}</span>
                    <Pill accent={accent}>{r.gap_type}</Pill>
                    <Pill
                      accent={r.confidence === "certain" ? "var(--color-pass)" : "var(--color-block)"}
                      title={CONFIDENCE_NOTE[r.confidence]}
                    >
                      {r.confidence}
                    </Pill>
                    {r.negative_finding === "yes" && (
                      <Pill accent="var(--color-human)">negative finding</Pill>
                    )}
                    <Pill>{r.source}</Pill>
                  </span>
                  <span className="mt-2 block text-[13px] leading-relaxed text-muted">
                    {r.domain_gap}
                  </span>
                </span>
                <span className="mt-1 shrink-0 font-mono text-[10px] text-faint">
                  {isOpen ? "−" : "+"}
                </span>
              </button>

              {isOpen && (
                <div className="border-t border-line bg-ground/50 px-5 py-5">
                  <dl className="grid min-w-0 gap-4 lg:grid-cols-2">
                    <Field label="India">{r.india_instance || "—"}</Field>
                    <Field label="Neighbour">{r.neighbour_instance || "—"}</Field>
                    <Field label="Global comparator">{r.global_example || "—"}</Field>
                    <Field label="ITU hook">{r.itu_hook || "—"}</Field>
                    <Field label="Evidence">
                      <code className="font-mono text-[11px]">{r.evidence || "—"}</code>
                    </Field>
                    <Field label="Violated property">
                      {r.violated_property ? (
                        <span className="flex flex-wrap items-center gap-2">
                          <Pill accent="var(--color-fail)">{r.violated_property}</Pill>
                          {r.margin_india && (
                            <span className="font-mono text-[11px] tabular-nums">
                              margin {r.margin_india}
                            </span>
                          )}
                        </span>
                      ) : (
                        "— (document-derived, not simulation-derived)"
                      )}
                    </Field>
                    <Field label="Passes under">
                      {ids(r.passes_under_packs).length ? (
                        <span className="flex flex-wrap gap-1.5">
                          {ids(r.passes_under_packs).map((p) => (
                            <Pill key={p} accent="var(--color-pass)">
                              {PACK_SHORT[p] ?? p}
                            </Pill>
                          ))}
                        </span>
                      ) : (
                        "no comparator regime passes this"
                      )}
                    </Field>
                    <Field label="Confidence basis">
                      {CONFIDENCE_NOTE[r.confidence] ?? "—"}
                      {unverified.length > 0 && (
                        <span className="mt-1.5 flex flex-wrap gap-1.5">
                          {unverified.map((c) => (
                            <Pill key={c} accent="var(--color-block)" title="still a summary record">
                              {c}
                            </Pill>
                          ))}
                        </span>
                      )}
                    </Field>
                  </dl>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Clauses label="India clauses" list={ids(r.india_clause_ids)} />
                    <Clauses label="Neighbour clauses" list={ids(r.neighbour_clause_ids)} />
                    <Clauses label="Global clauses" list={ids(r.global_clause_ids)} />
                  </div>

                  {r.replay_cmd && (
                    <div className="mt-4 min-w-0 rounded-md border border-line bg-ground/70 px-3 py-2.5">
                      <div className="mb-1 font-mono text-[10px] tracking-wider text-faint uppercase">
                        Reproduce
                      </div>
                      <code className="block overflow-x-auto font-mono text-[10.5px] whitespace-pre text-muted">
                        {r.replay_cmd}
                      </code>
                    </div>
                  )}
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-mono text-[10px] tracking-wider text-faint uppercase">{label}</dt>
      <dd className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{children}</dd>
    </div>
  );
}

function Clauses({ label, list }: { label: string; list: string[] }) {
  return (
    <div className="rounded-lg border border-line bg-panel-2/40 p-3">
      <div className="font-mono text-[10px] tracking-wider text-faint uppercase">{label}</div>
      {list.length === 0 ? (
        <div className="mt-1.5 text-[11.5px] text-faint">none cited</div>
      ) : (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {list.map((c) => (
            <Pill key={c} accent="var(--color-us)">
              {c}
            </Pill>
          ))}
        </div>
      )}
    </div>
  );
}
