"use client";

import { useState } from "react";

import { Dot, Panel, Pill } from "@/components/ui";
import type { FlowStage } from "@/lib/types";

const NODE_ACCENT: Record<string, string> = {
  SRC: "#4aa8ff",
  C: "#38bdf8",
  PP: "#2dd4a7",
  M: "#c084fc",
  P: "#f0b429",
  D: "var(--color-brand)",
  SINK: "#fb7185",
};

/** The pipeline, stage by stage, each stage holding the number it produced. */
export function Flow({ stages }: { stages: FlowStage[] }) {
  const [open, setOpen] = useState(0);
  const active = stages[open] ?? stages[0];
  if (!active) return null;

  return (
    <Panel grid className="overflow-hidden">
      <div className="overflow-x-auto border-b border-line">
        <div className="flex min-w-[900px] items-stretch">
          {stages.map((s, i) => {
            const accent = NODE_ACCENT[s.node] ?? "var(--color-muted)";
            const on = i === open;
            return (
              <button
                key={`${s.node}-${s.title}`}
                onClick={() => setOpen(i)}
                className="group relative flex-1 border-r border-line px-3.5 py-4 text-left transition-colors last:border-r-0"
                style={{ background: on ? `color-mix(in srgb, ${accent} 10%, transparent)` : undefined }}
              >
                <span
                  className="absolute inset-x-0 top-0 h-0.5 transition-opacity"
                  style={{ background: accent, opacity: on ? 1 : 0.18 }}
                />
                <span className="flex items-center gap-1.5">
                  <span
                    className="font-mono text-[10.5px] font-bold tracking-[0.14em]"
                    style={{ color: accent }}
                  >
                    {s.node}
                  </span>
                  {i < stages.length - 1 && (
                    <span className="ml-auto text-[11px] text-faint/60">→</span>
                  )}
                </span>
                <span
                  className={`mt-1.5 block text-[12px] leading-snug font-medium ${on ? "text-ink" : "text-muted"}`}
                >
                  {s.title}
                </span>
                <span className="mt-2 block font-mono text-[13px] tabular-nums" style={{ color: on ? accent : "var(--color-faint)" }}>
                  {s.measure}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-5 p-5 lg:grid-cols-[1.5fr_1fr]">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Dot accent={NODE_ACCENT[active.node] ?? "var(--color-muted)"} />
            <h3 className="text-[15px] font-semibold text-ink">{active.title}</h3>
            <Pill accent={NODE_ACCENT[active.node]}>Y.3172 node {active.node}</Pill>
          </div>
          <p className="mt-3 max-w-2xl text-[13px] leading-relaxed text-muted">{active.body}</p>
        </div>
        <div className="grid content-start gap-2.5">
          <div className="rounded-lg border border-line bg-panel-2/60 px-4 py-3">
            <div className="font-mono text-xl tabular-nums text-ink">{active.measure}</div>
            <div className="mt-1 text-[11.5px] text-faint">{active.measure_sub}</div>
          </div>
          <div className="rounded-lg border border-line bg-ground/60 px-3.5 py-2.5">
            <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
              Produced by
            </div>
            <code className="mt-1 block overflow-x-auto font-mono text-[11px] whitespace-pre text-muted">
              {active.command}
            </code>
            <div className="mt-1.5 font-mono text-[10.5px] text-faint">app/{active.module}</div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
