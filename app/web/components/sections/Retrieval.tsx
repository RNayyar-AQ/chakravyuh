import { Panel, PanelHead, Pill } from "@/components/ui";
import type { Bundle } from "@/lib/types";

const MODE_ACCENT: Record<string, string> = {
  bm25: "#4aa8ff",
  vector: "#c084fc",
  hybrid: "#2dd4a7",
  hybrid_rerank: "#34d399",
  tree: "#8597ad",
};

/** Retrieval, shown as arithmetic rather than as a claim. */
export function Retrieval({ b }: { b: Bundle }) {
  const ex = b.retrieval_example;
  const hybrid = b.retrieval.find((r) => r.mode === "hybrid") ?? b.retrieval[0];
  const gold = new Set(ex?.gold_clause_ids ?? []);
  const shown = ex?.fused.slice(0, 6) ?? [];

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel className="overflow-hidden">
          <PanelHead
            kicker="48 questions · 5 retrievers"
            title="Scored, not asserted"
            right={<Pill accent="var(--color-pass)">best: hybrid</Pill>}
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[460px] text-left text-[12.5px]">
              <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
                <tr className="border-b border-line">
                  <th className="px-5 py-2.5 font-medium">Mode</th>
                  <th className="px-3 py-2.5 font-medium">Recall@5</th>
                  <th className="px-3 py-2.5 font-medium">MRR</th>
                  <th className="px-5 py-2.5 font-medium">Abstention</th>
                </tr>
              </thead>
              <tbody>
                {b.retrieval.map((r) => (
                  <tr key={r.mode} className="border-b border-line/50 last:border-0">
                    <td className="px-5 py-2.5 font-mono" style={{ color: MODE_ACCENT[r.mode] }}>
                      {r.mode}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-ink">
                      {r.recall_at_k.toFixed(3)}
                    </td>
                    <td className="px-3 py-2.5 font-mono tabular-nums text-muted">
                      {r.mrr.toFixed(3)}
                    </td>
                    <td className="px-5 py-2.5 font-mono tabular-nums text-muted">
                      {r.abstention_separability.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
            Five of the {hybrid?.questions ?? 0} + {hybrid?.abstention_questions ?? 0} questions
            have no answer in the corpus, each tied to a documented absence rather than invented to
            be unanswerable. <span className="text-ink">Abstention separability</span> is the gap
            between top scores on answerable and unanswerable queries — whether the retriever can
            tell that the clauses do not contain the answer.
          </div>
        </Panel>

        <Panel className="overflow-hidden">
          <PanelHead kicker="The Adviser" title="The one component that reads a model's words" />
          <div className="p-5">
            <p className="text-[13px] leading-relaxed text-muted">
              The Adviser answers questions with citations. It holds no powers and proposes no
              actions, so nothing it says can reach the world. Every clause it cites is checked
              twice: it must be in the retrieved set, and it must exist in the clause store.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {[
                ["cases", b.adviser.cases, "var(--color-us)"],
                ["gold clause recovered", b.adviser.c1_correct_clause, "var(--color-pass)"],
                ["no invented clause", b.adviser.c4_no_invented_clause, "var(--color-pass)"],
                ["human-checked", b.adviser.human_checked, "var(--color-block)"],
              ].map(([label, value, accent]) => (
                <div key={String(label)} className="rounded-lg border border-line bg-panel-2/60 px-3.5 py-3">
                  <div
                    className="font-mono text-lg tabular-nums"
                    style={{ color: String(accent) }}
                  >
                    {String(value ?? "—")}
                  </div>
                  <div className="mt-1 text-[11px] leading-snug text-faint">{String(label)}</div>
                </div>
              ))}
            </div>
            <p className="mt-4 rounded-lg border border-line bg-ground/50 px-4 py-3 text-[12.5px] leading-relaxed text-muted">
              Mode <span className="font-mono text-ink">{String(b.adviser.adviser_mode ?? "—")}</span>.
              With no model configured it falls back to extractive answering rather than
              generating, which is a weaker answer but never an invented one.
            </p>
          </div>
        </Panel>
      </div>

      {ex && (
        <Panel className="overflow-hidden">
          <PanelHead
            kicker={`Worked example · ${ex.qid}`}
            title="One question, every retriever, and the fusion written out"
          />
          <div className="border-b border-line px-5 py-4">
            <p className="text-[14px] leading-snug text-ink">&ldquo;{ex.question}&rdquo;</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="font-mono text-[10.5px] text-faint">gold answer</span>
              {ex.gold_clause_ids.map((c) => (
                <Pill key={c} accent="var(--color-pass)">
                  {c}
                </Pill>
              ))}
            </div>
          </div>

          <div className="grid gap-5 p-5 lg:grid-cols-[1fr_1fr]">
            <div>
              <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
                What each retriever returned, in order
              </div>
              <div className="mt-3 grid gap-2.5">
                {ex.rankings.map((r) => (
                  <div key={r.mode}>
                    <div className="flex items-baseline gap-2">
                      <span
                        className="w-[104px] shrink-0 font-mono text-[11.5px]"
                        style={{ color: MODE_ACCENT[r.mode] }}
                      >
                        {r.mode}
                      </span>
                      <span className="font-mono text-[10.5px] text-faint">
                        {r.first_gold_rank ? `gold at rank ${r.first_gold_rank}` : "gold not in top 5"}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {r.retrieved.map((cid, i) => (
                        <span
                          key={`${cid}-${i}`}
                          className="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                          style={{
                            color: gold.has(cid) ? "var(--color-pass)" : "var(--color-muted)",
                            borderColor: gold.has(cid)
                              ? "color-mix(in srgb, var(--color-pass) 40%, transparent)"
                              : "var(--color-line)",
                          }}
                        >
                          {i + 1}. {cid}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
                Reciprocal rank fusion
              </div>
              <code className="mt-2 block rounded-md border border-line bg-ground/70 px-3 py-2 font-mono text-[11px] text-ink">
                {ex.formula}
              </code>
              <div className="mt-3 grid gap-1.5">
                {shown.map((f) => (
                  <div
                    key={f.clause_id}
                    className="rounded-md border border-line bg-panel-2/50 px-3 py-2"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span
                        className="font-mono text-[11px]"
                        style={{ color: gold.has(f.clause_id) ? "var(--color-pass)" : "var(--color-ink)" }}
                      >
                        {f.clause_id}
                      </span>
                      <span className="font-mono text-[11px] tabular-nums text-ink">
                        {f.score.toFixed(6)}
                      </span>
                    </div>
                    <div className="mt-1 font-mono text-[10.5px] text-faint">
                      {f.parts
                        .map((p) => `1/(${ex.k}+${p.rank}) [${p.mode}]`)
                        .join("  +  ")}
                      {f.tied_with_next && (
                        <span className="ml-2 text-block">tied with the next row</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[12px] leading-relaxed text-faint">
                {ex.agrees_with_recorded
                  ? "This reconstruction reproduces the ranking the evaluation recorded."
                  : "The top two tie to the digit, and the engine breaks that tie at chunk level while this reconstruction breaks it by id — so the recorded order differs from the one above. The scores are identical; only the tie-break is not."}{" "}
                {ex.caveat}
              </p>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
