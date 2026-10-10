"use client";

import { useState } from "react";

import { Panel, Pill } from "@/components/ui";
import { PACK_ACCENT, PACK_SHORT, packOrder, signed } from "@/lib/format";
import type { Derivation, Pack } from "@/lib/types";

function Operand({
  label,
  value,
  accent,
  unit,
}: {
  label: string;
  value: string;
  accent: string;
  unit?: string;
}) {
  return (
    <div className="min-w-0 rounded-lg border border-line bg-ground/60 px-3.5 py-2.5 text-center">
      <div className="font-mono text-[19px] leading-none tabular-nums" style={{ color: accent }}>
        {value}
        {unit && <span className="ml-1 text-[10px] text-faint">{unit}</span>}
      </div>
      <div className="mt-1.5 text-[10.5px] leading-snug text-faint">{label}</div>
    </div>
  );
}

function Operator({ children }: { children: string }) {
  return (
    <div className="self-center px-1 font-mono text-[18px] text-line-bright">{children}</div>
  );
}

/** Each margin, recomputed in front of you from the operands the run recorded. */
export function Derivations({
  derivations,
  packs,
  properties,
}: {
  derivations: Derivation[];
  packs: Pack[];
  properties: Record<string, string>;
}) {
  const ordered = [...packs].sort((a, b) => packOrder(a.pack_id, b.pack_id));
  const [pack, setPack] = useState(ordered[0]?.pack_id ?? "");
  const rows = derivations
    .filter((d) => d.pack_id === pack)
    .sort((a, b) => a.property_id.localeCompare(b.property_id));
  const accent = PACK_ACCENT[pack] ?? "var(--color-brand)";
  const disagreements = derivations.filter((d) => !d.agrees).length;

  return (
    <Panel className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-3.5">
        <div className="mr-auto">
          <div className="font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            Y.3172 node SINK · recomputed from the ledger
          </div>
          <h3 className="mt-1 text-[15px] font-semibold text-ink">
            Every margin, with its arithmetic shown
          </h3>
        </div>
        {ordered.map((p) => (
          <button
            key={p.pack_id}
            onClick={() => setPack(p.pack_id)}
            className={`rounded-md border px-3 py-1.5 text-[12px] font-medium transition-colors ${
              p.pack_id === pack ? "bg-panel-2 text-ink" : "text-muted hover:text-ink"
            }`}
            style={{
              borderColor:
                p.pack_id === pack
                  ? `color-mix(in srgb, ${PACK_ACCENT[p.pack_id]} 48%, transparent)`
                  : "var(--color-line)",
            }}
          >
            {PACK_SHORT[p.pack_id] ?? p.pack_id}
          </button>
        ))}
      </div>

      <div className="grid gap-4 p-5 lg:grid-cols-2">
        {rows.map((d) => {
          const verdict = d.passed ? "var(--color-pass)" : "var(--color-fail)";
          return (
            <div key={d.property_id} className="min-w-0 rounded-lg border border-line bg-panel-2/40 p-4">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="font-mono text-[13px] font-semibold" style={{ color: accent }}>
                  {d.property_id}
                </span>
                <span
                  className="font-mono text-[10.5px] font-bold tracking-[0.14em]"
                  style={{ color: verdict }}
                >
                  {d.passed ? "HOLDS" : "VIOLATED"}
                </span>
                <span className="ml-auto font-mono text-[10px] text-faint">ledger seq {d.seq}</span>
              </div>
              <p className="mt-1.5 text-[12.5px] leading-snug text-muted">
                {properties[d.property_id]}
              </p>

              {!d.applicable ? (
                <p className="mt-3 rounded-md border border-line bg-ground/60 px-3 py-2.5 text-[12px] leading-relaxed text-faint">
                  {d.note}
                </p>
              ) : (
                <>
                  <code className="mt-3 block overflow-x-auto rounded-md border border-line bg-ground/70 px-3 py-2 font-mono text-[10.5px] whitespace-pre text-muted">
                    {d.formula}
                  </code>

                  <div className="mt-3 grid grid-cols-[1fr_auto_1fr_auto_1fr] gap-1">
                    {d.property_id === "P1" ? (
                      <>
                        <Operand
                          label={d.observed_label}
                          value={String(d.observed)}
                          accent="var(--color-ink)"
                        />
                        <Operator>−</Operator>
                        <Operand
                          label={d.threshold_name}
                          value={String(d.threshold)}
                          accent="var(--color-muted)"
                        />
                      </>
                    ) : (
                      <>
                        <Operand
                          label={d.threshold_name}
                          value={String(d.threshold)}
                          accent="var(--color-muted)"
                        />
                        <Operator>−</Operator>
                        <Operand
                          label={d.observed_label}
                          value={String(d.observed)}
                          accent="var(--color-ink)"
                        />
                      </>
                    )}
                    <Operator>=</Operator>
                    <Operand label="margin" value={signed(d.margin)} accent={verdict} />
                  </div>

                  <p className="mt-2.5 text-[11.5px] leading-relaxed text-muted">{d.note}</p>

                  {d.terms.length > 0 && (
                    <div className="mt-3">
                      <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
                        What went into the worst case
                      </div>
                      <div className="mt-1.5 grid gap-1">
                        {d.terms.slice(0, 10).map((term, i) => (
                          <div
                            key={`${term.label}-${i}`}
                            className="flex items-baseline gap-2 border-b border-line/40 py-1 text-[11.5px] last:border-0"
                          >
                            <span className="font-mono text-muted">{term.label}</span>
                            <span className="truncate text-[10.5px] text-faint">{term.note}</span>
                            <span className="ml-auto font-mono tabular-nums text-ink">
                              {term.value ?? "—"}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-3 flex flex-wrap items-center gap-1.5">
                    <Pill accent={d.agrees ? "var(--color-pass)" : "var(--color-fail)"}>
                      {d.agrees
                        ? "recomputation matches the recorded margin"
                        : `recomputed ${d.recomputed}, recorded ${d.margin}`}
                    </Pill>
                    <Pill>unit: {d.unit}</Pill>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>

      <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
        None of these numbers is read off a report. The export walks the ledger, takes the operands
        each property check recorded for itself, redoes the arithmetic, and compares the result
        with the margin the run wrote.{" "}
        {disagreements === 0 ? (
          <span className="text-ink">
            All {derivations.length} recomputations across all three rulebooks agree.
          </span>
        ) : (
          <span className="text-fail">
            {disagreements} of {derivations.length} disagree, and are flagged above rather than
            reconciled.
          </span>
        )}
      </div>
    </Panel>
  );
}
