import { LiveVerify } from "@/components/LiveVerify";
import { Dot, Panel, PanelHead, Pill, Provenance, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";

export const metadata = { title: "Evidence — CHAKRAVYUH" };

const STATUS_ACCENT: Record<string, string> = {
  held: "var(--color-pass)",
  partial: "var(--color-block)",
  wanted: "var(--color-fail)",
};

const PROVENANCE_LABEL: Record<string, string> = {
  gazette_pdf: "Gazette PDF",
  gazette_pdf_subsection: "Gazette PDF, subsection",
  secondary_source: "Secondary source",
  model_written: "Model-written summary",
  verified: "Verified against the instrument",
  verified_with_artifacts: "Verified, with page and hash",
  unverified_summary: "Summary, not yet verified",
};

function Bar({ parts, total }: { parts: [string, number, string][]; total: number }) {
  return (
    <>
      <div className="flex h-2.5 overflow-hidden rounded-full border border-line">
        {parts.map(([k, n, c]) => (
          <span key={k} title={`${k}: ${n}`} style={{ width: `${(n / total) * 100}%`, background: c }} />
        ))}
      </div>
      <div className="mt-3 grid gap-1.5">
        {parts.map(([k, n, c]) => (
          <div key={k} className="flex items-center gap-2 text-[12px]">
            <Dot accent={c} />
            <span className="text-muted">{PROVENANCE_LABEL[k] ?? k.replace(/_/g, " ")}</span>
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

export default function EvidencePage() {
  const b = getBundle();
  const verbatim = b.kb.total - (b.kb.verbatim_status["unverified_summary"] ?? 0);
  const hybrid = b.retrieval.find((r) => r.mode === "hybrid") ?? b.retrieval[0];
  const held = b.sources.filter((s) => s.status === "held").length;

  const PROV_COLORS: Record<string, string> = {
    gazette_pdf: "#2dd4a7",
    gazette_pdf_subsection: "#4aa8ff",
    secondary_source: "#f0b429",
    model_written: "#fb7185",
    verified: "#2dd4a7",
    verified_with_artifacts: "#4aa8ff",
    unverified_summary: "#fb7185",
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          Knowledge base · retrieval · audit chain
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Evidence</h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          A claim about the law is only as good as the text behind it. Every clause record carries
          its provenance, every source document carries a SHA-256 and a completeness check, and
          every run carries a hash chain. This page is the place to doubt the rest of the site.
        </p>
        <Provenance>
          python app/scripts/fetch_sources.py --verify · python app/scripts/verify_ledger.py
        </Provenance>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={b.kb.total} label="clause records" accent="var(--color-us)" />
        <Stat
          value={`${((verbatim / b.kb.total) * 100).toFixed(0)}%`}
          label="carry primary text"
          sub={`${verbatim} of ${b.kb.total}`}
          accent="var(--color-pass)"
        />
        <Stat value={`${held}/${b.sources.length}`} label="source documents held" sub="hash-verified" accent="var(--color-block)" />
        <Stat
          value={hybrid ? hybrid.recall_at_k.toFixed(3) : "—"}
          label="recall@5, hybrid"
          sub={hybrid ? `${hybrid.questions} questions · MRR ${hybrid.mrr.toFixed(3)}` : undefined}
          accent="var(--color-human)"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <PanelHead kicker="Knowledge base" title="Where each clause record came from" />
          <div className="p-5">
            <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
              Provenance — where the record came from
            </div>
            <Bar
              parts={Object.entries(b.kb.provenance).map(
                ([k, n]) => [k, n, PROV_COLORS[k] ?? "#8597ad"] as [string, number, string],
              )}
              total={b.kb.total}
            />

            <div className="mt-6 mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
              Verbatim status — whether we hold its own words
            </div>
            <Bar
              parts={Object.entries(b.kb.verbatim_status).map(
                ([k, n]) => [k, n, PROV_COLORS[k] ?? "#8597ad"] as [string, number, string],
              )}
              total={b.kb.total}
            />

            <p className="mt-5 text-[12.5px] leading-relaxed text-muted">
              These two measure different things, and the difference matters. Provenance says where
              a record came from; verbatim status says whether the instrument&apos;s own words are
              in hand. A record can come from a gazette PDF and still be awaiting verification —
              which is why{" "}
              <span className="font-mono text-ink">
                {b.kb.verbatim_status["unverified_summary"] ?? 0}
              </span>{" "}
              records are unverified while only{" "}
              <span className="font-mono text-ink">{b.kb.provenance["model_written"] ?? 0}</span>{" "}
              were written by a model. The gap register caps confidence on either, which is why no
              finding currently reads <span className="font-mono">certain</span>.
            </p>
            <div className="mt-4 flex flex-wrap gap-1.5">
              {Object.entries(b.kb.jurisdiction).map(([j, n]) => (
                <Pill key={j}>
                  {j} {n}
                </Pill>
              ))}
            </div>
          </div>
        </Panel>

        <Panel>
          <PanelHead kicker="Retrieval" title="Hybrid BM25 + vector, fused by RRF" />
          <div className="overflow-x-auto p-5">
            <table className="w-full min-w-[480px] text-left text-[12.5px]">
              <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
                <tr className="border-b border-line">
                  <th className="pb-2 font-medium">Mode</th>
                  <th className="pb-2 font-medium">Recall@5</th>
                  <th className="pb-2 font-medium">MRR</th>
                  <th className="pb-2 font-medium">Abstention</th>
                </tr>
              </thead>
              <tbody>
                {b.retrieval.map((r) => (
                  <tr key={r.mode} className="border-b border-line/50 last:border-0">
                    <td className="py-2.5 font-mono text-ink">{r.mode}</td>
                    <td className="py-2.5 font-mono text-muted tabular-nums">
                      {r.recall_at_k.toFixed(3)}
                    </td>
                    <td className="py-2.5 font-mono text-muted tabular-nums">{r.mrr.toFixed(3)}</td>
                    <td className="py-2.5 font-mono text-muted tabular-nums">
                      {r.abstention_separability.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-4 text-[12.5px] leading-relaxed text-muted">
              The question set includes deliberately unanswerable questions. Abstention separability
              measures the gap between top scores on answerable and unanswerable queries — whether
              the retriever knows when the clauses do not contain the answer.
            </p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              <Pill accent="var(--color-us)">adviser mode: {String(b.adviser.adviser_mode ?? "—")}</Pill>
              <Pill accent="var(--color-pass)">
                correct clause {String(b.adviser.c1_correct_clause ?? "—")}/
                {String(b.adviser.cases ?? "—")}
              </Pill>
              <Pill accent="var(--color-pass)">
                no invented clause {String(b.adviser.c4_no_invented_clause ?? "—")}/
                {String(b.adviser.cases ?? "—")}
              </Pill>
              <Pill accent="var(--color-block)">
                human-checked {String(b.adviser.human_checked ?? 0)}
              </Pill>
            </div>
          </div>
        </Panel>
      </div>

      {/* ---------------------------------------------------------- source manifest */}
      <Panel className="mt-6 overflow-hidden">
        <PanelHead
          kicker="data/sources/MANIFEST.yaml"
          title="Primary documents, and the ones we do not have"
        />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[840px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Status</th>
                <th className="px-4 py-2.5 font-medium">Instrument</th>
                <th className="px-4 py-2.5 font-medium">Gazette reference</th>
                <th className="px-4 py-2.5 font-medium">SHA-256</th>
                <th className="px-4 py-2.5 font-medium">Feeds</th>
              </tr>
            </thead>
            <tbody>
              {b.sources.map((s) => (
                <tr key={s.id} className="border-b border-line/50 align-top last:border-0">
                  <td className="px-5 py-3">
                    <Pill accent={STATUS_ACCENT[s.status]}>{s.status}</Pill>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-ink">{s.instrument || s.id}</div>
                    <div className="mt-0.5 font-mono text-[10.5px] text-faint">
                      {s.jurisdiction}
                      {s.pages ? ` · ${s.pages}pp` : ""}
                      {s.official ? " · official" : ""}
                    </div>
                    {s.reason && (
                      <div className="mt-1 text-[11.5px] leading-snug text-block">
                        {Array.isArray(s.reason) ? s.reason.join("; ") : s.reason}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[11.5px] leading-snug text-muted">{s.gazette || "—"}</td>
                  <td className="px-4 py-3 font-mono text-[10.5px] text-faint">
                    {s.sha256 ? `${s.sha256}…` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex flex-wrap gap-1">
                      {s.feeds.map((f) => (
                        <Pill key={f}>{f}</Pill>
                      ))}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
          A hash alone proves a file did not change; it does not prove the file is complete. Each
          source therefore also declares strings it must contain. That check caught a composite PDF
          that would have made a missing authentication requirement look like a confirmed absence —
          the exact false negative this project exists to prevent.
        </div>
      </Panel>

      {/* ------------------------------------------------------------- audit chain */}
      <Panel className="mt-6 overflow-hidden">
        <PanelHead kicker="Audit" title="Hash-chained ledgers, and what happens when one is edited" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Run</th>
                <th className="px-4 py-2.5 font-medium">Entries</th>
                <th className="px-4 py-2.5 font-medium">Head hash</th>
                <th className="px-4 py-2.5 font-medium">Verification</th>
              </tr>
            </thead>
            <tbody>
              {b.ledger.runs.map((r) => (
                <tr key={r.run_id} className="border-b border-line/50 last:border-0">
                  <td className="px-5 py-3 font-mono text-[11px] text-ink">{r.run_id}</td>
                  <td className="px-4 py-3 font-mono text-muted tabular-nums">
                    {r.entries.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-[10.5px] text-faint">
                    {r.head_hash.slice(0, 20)}…
                  </td>
                  <td className="px-4 py-3">
                    <Pill accent={r.verified ? "var(--color-pass)" : "var(--color-fail)"}>
                      {r.verified ? "chain intact" : r.message}
                    </Pill>
                  </td>
                </tr>
              ))}
              {b.ledger.tamper.map((t) => (
                <tr key={t.run_id} className="border-b border-line/50 bg-fail/5 last:border-0">
                  <td className="px-5 py-3 font-mono text-[11px] text-muted">{t.run_id}</td>
                  <td className="px-4 py-3 text-faint">—</td>
                  <td className="px-4 py-3 text-faint">—</td>
                  <td className="px-4 py-3">
                    <Pill accent="var(--color-fail)">{t.message}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <LiveVerify />
        <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
          Each entry commits to{" "}
          <code className="font-mono text-ink">
            sha256(prev_hash | seq | t | kind | canonical_json(payload))
          </code>
          . The tampered rows are deliberate: one field was changed in a sealed ledger, and
          verification names the sequence number where the chain breaks rather than reporting a
          vague failure.
        </div>
      </Panel>
    </div>
  );
}
