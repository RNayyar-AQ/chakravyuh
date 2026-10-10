import { Panel, PanelHead, Pill } from "@/components/ui";
import type { Bundle } from "@/lib/types";

const PROV_COLOR: Record<string, string> = {
  gazette_pdf: "#2dd4a7",
  gazette_pdf_subsection: "#4aa8ff",
  secondary_source: "#f0b429",
  model_written: "#fb7185",
  verified: "#2dd4a7",
  verified_with_artifacts: "#4aa8ff",
  unverified_summary: "#fb7185",
};

const PROV_LABEL: Record<string, string> = {
  gazette_pdf: "Gazette PDF",
  gazette_pdf_subsection: "Gazette PDF, subsection",
  secondary_source: "Secondary source",
  model_written: "Model-written summary",
  verified: "Verified against the instrument",
  verified_with_artifacts: "Verified, page-break artifact flagged",
  unverified_summary: "Summary, not yet verified",
};

function Bar({ parts, total }: { parts: [string, number][]; total: number }) {
  return (
    <>
      <div className="flex h-2.5 overflow-hidden rounded-full border border-line">
        {parts.map(([k, n]) => (
          <span
            key={k}
            title={`${k}: ${n}`}
            style={{ width: `${(n / total) * 100}%`, background: PROV_COLOR[k] ?? "#8597ad" }}
          />
        ))}
      </div>
      <div className="mt-3 grid gap-1.5">
        {parts.map(([k, n]) => (
          <div key={k} className="flex items-center gap-2 text-[12px]">
            <span
              className="inline-block size-1.5 shrink-0 rounded-full"
              style={{ background: PROV_COLOR[k] ?? "#8597ad" }}
            />
            <span className="text-muted">{PROV_LABEL[k] ?? k.replace(/_/g, " ")}</span>
            <span className="ml-auto font-mono text-ink tabular-nums">{n}</span>
            <span className="w-11 text-right font-mono text-[10.5px] text-faint">
              {((n / total) * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

/** One box in the pipeline drawing. */
function Box({
  title,
  lines,
  accent,
  note,
}: {
  title: string;
  lines: string[];
  accent: string;
  note?: string;
}) {
  return (
    <div
      className="min-w-0 flex-1 rounded-lg border bg-panel-2/60 px-3.5 py-3"
      style={{ borderColor: `color-mix(in srgb, ${accent} 34%, transparent)` }}
    >
      <div className="font-mono text-[10.5px] font-semibold tracking-wide" style={{ color: accent }}>
        {title}
      </div>
      {lines.map((l) => (
        <div key={l} className="mt-1 text-[11.5px] leading-snug text-muted">
          {l}
        </div>
      ))}
      {note && <div className="mt-1.5 text-[10.5px] leading-snug text-faint">{note}</div>}
    </div>
  );
}

function Arrow({ label }: { label: string }) {
  return (
    <div className="flex shrink-0 flex-col items-center justify-center px-1 py-2 lg:py-0">
      <span className="font-mono text-[9.5px] whitespace-nowrap text-faint">{label}</span>
      <span className="text-[13px] leading-none text-line-bright">
        <span className="hidden lg:inline">→</span>
        <span className="lg:hidden">↓</span>
      </span>
    </div>
  );
}

/** What the knowledge base is actually shaped like, drawn from its own counts. */
export function KnowledgeBase({ b }: { b: Bundle }) {
  const g = b.kb_graph;
  const held = b.sources.filter((s) => s.status === "held").length;
  const top = g.instruments.slice(0, 8);

  return (
    <div className="grid gap-4">
      <Panel className="overflow-hidden">
        <PanelHead
          kicker="Y.3172 nodes SRC → C → PP"
          title="How a gazette PDF becomes something a rule may cite"
          right={<Pill accent="var(--color-us)">{g.clauses} clauses · {g.chunks} chunks</Pill>}
        />
        <div className="p-5">
          <div className="flex flex-col items-stretch lg:flex-row lg:items-center">
            <Box
              title="PRIMARY SOURCE"
              accent="#4aa8ff"
              lines={[`${held} documents held`, `${b.sources.length - held} named but not held`]}
              note="pinned by sha256, checked against strings only the real instrument carries"
            />
            <Arrow label="split" />
            <Box
              title="CLAUSE RECORD"
              accent="#2dd4a7"
              lines={[`${g.clauses} records`, `${g.real_text} with the instrument's own words`]}
              note="text, sha256 of that text, page, and the hash of the source PDF"
            />
            <Arrow label="chunk" />
            <Box
              title="CHUNK"
              accent="#c084fc"
              lines={[`${g.chunks} chunks`, "one per clause, split only when long"]}
              note={`carries ${g.chunk_metadata_fields.length} metadata fields, so a hit can be cited`}
            />
          </div>

          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-line-bright bg-ground/50 p-4">
              <div className="font-mono text-[10.5px] font-semibold tracking-wide text-ink">
                EXACT STORE — SQLite
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-muted">
                Lookup by clause id. Raises rather than guessing, and hash-matches the text before
                a rule may cite it. <span className="text-ink">The policy engine reads only this.</span>
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                <Pill accent="var(--color-pass)">no similarity score</Pill>
                <Pill>data/clauses/clauses.sqlite</Pill>
              </div>
            </div>
            <div className="rounded-lg border border-line-bright bg-ground/50 p-4">
              <div className="font-mono text-[10.5px] font-semibold tracking-wide text-ink">
                RETRIEVAL INDEX — BM25 + Chroma
              </div>
              <p className="mt-1.5 text-[12px] leading-relaxed text-muted">
                Ranked search for the Adviser, fused by Reciprocal Rank Fusion. Answers questions;
                never decides anything.
              </p>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {Object.entries(g.collections).map(([c, n]) => (
                  <Pill key={c} accent="var(--color-human)">
                    {c} {n}
                  </Pill>
                ))}
              </div>
            </div>
          </div>

          <p className="mt-4 border-l-2 border-line-bright pl-3.5 text-[12.5px] leading-relaxed text-muted">
            The split is the point. A legality decision that went through the ranked index would be
            downstream of a similarity score; here it is downstream of an exact id and a hash
            match. Retrieval helps a person find the clause. It never tells the engine which clause
            applies.
          </p>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-[1fr_1.25fr]">
        <Panel>
          <PanelHead kicker="Honesty ledger" title="Where each record came from" />
          <div className="p-5">
            <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
              Provenance
            </div>
            <Bar parts={Object.entries(b.kb.provenance)} total={b.kb.total} />
            <div className="mt-6 mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
              Verbatim status
            </div>
            <Bar parts={Object.entries(b.kb.verbatim_status)} total={b.kb.total} />
            <p className="mt-5 text-[12.5px] leading-relaxed text-muted">
              These measure different things. Provenance says where a record came from; verbatim
              status says whether its own words are in hand. A finding resting on a summary is
              capped at <span className="font-mono text-ink">likely</span> and can never read{" "}
              <span className="font-mono text-ink">certain</span> — which is why none of them does.
            </p>
            <div className="mt-3.5 flex flex-wrap gap-1.5">
              {Object.entries(b.kb.jurisdiction).map(([j, n]) => (
                <Pill key={j}>
                  {j} {n}
                </Pill>
              ))}
            </div>
          </div>
        </Panel>

        <Panel className="overflow-hidden">
          <PanelHead
            kicker="Corpus"
            title="Instruments by weight in the store"
            right={<Pill>{g.instruments.length} instruments</Pill>}
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-[12.5px]">
              <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
                <tr className="border-b border-line">
                  <th className="px-5 py-2.5 font-medium">Instrument</th>
                  <th className="px-3 py-2.5 font-medium">Clauses</th>
                  <th className="px-3 py-2.5 font-medium">Own words</th>
                  <th className="px-5 py-2.5 font-medium">Quotable</th>
                </tr>
              </thead>
              <tbody>
                {top.map((r) => (
                  <tr key={r.instrument} className="border-b border-line/50 last:border-0">
                    <td className="px-5 py-2.5">
                      <div className="leading-snug text-ink">{r.instrument}</div>
                      <div className="mt-0.5 font-mono text-[10px] text-faint">{r.jurisdiction}</div>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-ink tabular-nums">{r.clauses}</td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-muted">{r.real_text}</td>
                    <td className="px-5 py-2.5 font-mono tabular-nums text-muted">{r.quotable}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-line px-5 py-3.5 text-[12px] leading-relaxed text-faint">
            {g.instruments.length - top.length} further instruments hold the remaining{" "}
            {g.instruments.slice(top.length).reduce((n, r) => n + r.clauses, 0)} clauses.{" "}
            {g.with_pdf_hash} records carry the hash of the PDF they were extracted from, which
            pins the document even if the link rots.
          </div>
        </Panel>
      </div>
    </div>
  );
}
