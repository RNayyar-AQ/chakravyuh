"use client";

import { useState } from "react";

import { Pill } from "@/components/ui";
import type { ClauseRecord } from "@/lib/types";

const PROV_ACCENT: Record<string, string> = {
  gazette_pdf: "var(--color-pass)",
  gazette_pdf_subsection: "var(--color-us)",
  secondary_source: "var(--color-block)",
  model_written: "var(--color-fail)",
};

const PROV_LABEL: Record<string, string> = {
  gazette_pdf: "the instrument's own words",
  gazette_pdf_subsection: "the instrument's own words, subsection",
  secondary_source: "summary, attributed to a named secondary source",
  model_written: "model-written summary, nothing verified",
};

/** A cited clause, openable in place, with its provenance stated beside its text. */
export function ClauseText({ id, clause }: { id: string; clause?: ClauseRecord }) {
  const [open, setOpen] = useState(false);
  const accent = clause ? (PROV_ACCENT[clause.provenance] ?? "var(--color-muted)") : "var(--color-faint)";

  if (!clause) {
    return <Pill>{id}</Pill>;
  }

  return (
    <div className="min-w-0 rounded-md border border-line bg-ground/50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <span className="font-mono text-[11px]" style={{ color: accent }}>
          {clause.clause_id}
        </span>
        <span className="truncate text-[11.5px] text-muted">
          {clause.instrument} — {clause.section}
        </span>
        <span className="ml-auto font-mono text-[10px] text-faint">{open ? "hide" : "read"}</span>
      </button>
      {open && (
        <div className="border-t border-line px-3 py-3">
          <p className="text-[12.5px] leading-relaxed whitespace-pre-wrap text-ink">
            {clause.text}
          </p>
          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
            <Pill accent={accent}>{PROV_LABEL[clause.provenance] ?? clause.provenance}</Pill>
            {clause.page !== null && <Pill>page {clause.page}</Pill>}
            <Pill>sha {clause.sha256}…</Pill>
            {!clause.quotable && <Pill accent="var(--color-block)">not safe to quote verbatim</Pill>}
          </div>
          {clause.source_url && (
            <a
              href={clause.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 block truncate font-mono text-[10.5px] text-faint underline underline-offset-2 hover:text-muted"
            >
              {clause.source_url}
            </a>
          )}
        </div>
      )}
    </div>
  );
}
