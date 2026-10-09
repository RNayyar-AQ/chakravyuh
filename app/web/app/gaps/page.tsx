import { Panel, Provenance, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";

import { GapExplorer } from "./GapExplorer";

export const metadata = { title: "Gap Register — CHAKRAVYUH" };

export default function GapsPage() {
  const b = getBundle();
  const certain = b.gaps.filter((g) => g.confidence === "certain").length;
  const simulation = b.gaps.filter((g) => g.source === "simulation").length;
  const negative = b.gaps.filter((g) => g.negative_finding === "yes").length;

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          outputs/gap_register.csv
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Gap Register</h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          Every row names a gap, the Indian instance, what a neighbouring and a global regime do
          instead, the evidence, and the ITU instrument that already addresses it. Rows marked{" "}
          <span className="font-mono text-ink">simulation</span> were produced by a run; rows marked{" "}
          <span className="font-mono text-ink">document</span> come from reading the instruments.
        </p>
        <p className="mt-4 text-[13.5px] leading-relaxed text-muted">
          Confidence is <span className="font-semibold text-ink">computed, never asserted</span>. A
          finding reads <span className="font-mono">certain</span> only when every clause it cites
          carries the instrument&apos;s own words. Where a clause is still a summary, the row is
          capped at <span className="font-mono">likely</span> and names the clause responsible.
        </p>
        <Provenance>python app/scripts/run_demo.py — writes the register, then reads it back</Provenance>
      </header>

      <div className="mb-7 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={b.gaps.length} label="registered gaps" accent="var(--color-brand)" />
        <Stat value={simulation} label="from simulation" sub={`${b.gaps.length - simulation} from documents`} accent="var(--color-us)" />
        <Stat value={negative} label="negative findings" sub="an absence, which needs quotable text" accent="var(--color-human)" />
        <Stat
          value={`${certain}/${b.gaps.length}`}
          label="rated certain"
          sub={certain === 0 ? "every row still rests on at least one summary" : undefined}
          accent={certain === 0 ? "var(--color-block)" : "var(--color-pass)"}
        />
      </div>

      <GapExplorer rows={b.gaps} />

      {certain === 0 && (
        <Panel className="mt-6 p-5">
          <h2 className="text-[14px] font-semibold text-ink">Why no row reads &ldquo;certain&rdquo;</h2>
          <p className="mt-2 max-w-4xl text-[13px] leading-relaxed text-muted">
            {b.kb.verbatim_status["unverified_summary"] ?? 0} of {b.kb.total} clause records are
            still model-written summaries rather than gazette text, and three primary documents —
            the complete Telecommunications (Temporary Suspension of Services) Rules 2024, the 2025
            amendment, and DoT SOP-2020 — are not available in a verifiable form. The rating is the
            system refusing to overclaim, and it will rise on its own as those documents are
            ingested. No row needs rewriting for that to happen.
          </p>
        </Panel>
      )}
    </div>
  );
}
