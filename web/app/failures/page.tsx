import { Panel, Pill, Provenance, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { PACK_ACCENT, PACK_SHORT, packOrder, signed } from "@/lib/format";

export const metadata = { title: "Failure Atlas — CHAKRAVYUH" };

export default function FailuresPage() {
  const b = getBundle();
  const totalRuns = b.fuzz.runs.reduce((n, r) => n + (r.runs_completed ?? 0), 0);
  const seconds = b.fuzz.runs.reduce((n, r) => n + (r.wall_seconds ?? 0), 0);
  const cards = [...b.fuzz.cards].sort((a, c) => packOrder(a.pack_id, c.pack_id));

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          Property-based fuzzing · Hypothesis
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Failure Atlas</h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          A stateful fuzzer mutates the world — escalating damage, delaying channels, forging
          orders — and asserts the four safety properties after every run. When a property breaks,
          Hypothesis shrinks the mutation sequence to the smallest one that still breaks it. What
          survives shrinking is a minimal, attributable counterexample, not an anecdote.
        </p>
        <Provenance>python scripts/run_fuzz.py --pack &lt;pack&gt; --scenario amphan_2020</Provenance>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={totalRuns.toLocaleString()} label="mutated worlds" sub="across every pack" accent="var(--color-block)" />
        <Stat value={cards.length} label="minimal counterexamples" sub="after shrinking" accent="var(--color-fail)" />
        <Stat value={`${Math.round(seconds)}s`} label="search time" sub="wall clock, all packs" />
        <Stat value={b.fuzz.runs.length} label="fuzz campaigns" sub="one per pack and assertion set" />
      </div>

      {/* Baselines first: a pack already failing at baseline has nothing left to fuzz, and saying
          so is more honest than reporting a search that was never run. */}
      <Panel className="mb-6 overflow-hidden">
        <div className="border-b border-line px-5 py-3.5">
          <h2 className="text-[14px] font-semibold text-ink">Campaign baselines</h2>
          <p className="mt-1 text-[12px] text-muted">
            A property already violated on the unmutated scenario is excluded from the search — it
            is a finding, not a target.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">Pack</th>
                <th className="px-4 py-2.5 font-medium">Asserted</th>
                <th className="px-4 py-2.5 font-medium">Excluded at baseline</th>
                <th className="px-4 py-2.5 font-medium">Runs</th>
                <th className="px-4 py-2.5 font-medium">Unique failures</th>
              </tr>
            </thead>
            <tbody>
              {b.fuzz.runs.map((r, i) => (
                <tr key={i} className="border-b border-line/60 last:border-0">
                  <td className="px-5 py-3">
                    <span className="font-mono font-semibold" style={{ color: PACK_ACCENT[r.pack_id] }}>
                      {PACK_SHORT[r.pack_id] ?? r.pack_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex flex-wrap gap-1">
                      {r.asserted_properties.map((p) => (
                        <Pill key={p}>{p}</Pill>
                      ))}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex flex-wrap gap-1">
                      {r.excluded_at_baseline.length === 0 ? (
                        <span className="text-faint">none</span>
                      ) : (
                        r.excluded_at_baseline.map((p) => (
                          <Pill key={p} accent="var(--color-fail)">
                            {p} already violated
                          </Pill>
                        ))
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-muted tabular-nums">
                    {r.runs_completed?.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-ink tabular-nums">
                    {r.unique_minimal_failures}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {cards.map((c) => (
          <Panel key={`${c.pack_id}-${c.failure_id}`} className="min-w-0 overflow-hidden">
            <div
              className="border-b border-line px-5 py-3.5"
              style={{ background: `color-mix(in srgb, ${PACK_ACCENT[c.pack_id]} 7%, transparent)` }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-mono text-[12px] font-semibold text-ink">{c.failure_id}</span>
                <span className="flex gap-1.5">
                  <Pill accent={PACK_ACCENT[c.pack_id]}>{PACK_SHORT[c.pack_id] ?? c.pack_id}</Pill>
                  <Pill accent="var(--color-fail)">{c.violated_property} violated</Pill>
                  <Pill accent="var(--color-human)">{c.gap_class}</Pill>
                </span>
              </div>
            </div>

            <div className="grid min-w-0 gap-4 p-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-line bg-panel-2/50 px-3.5 py-2.5">
                  <div className="font-mono text-lg text-fail tabular-nums">{signed(c.margin)}</div>
                  <div className="mt-1 text-[10.5px] text-faint">margin past the threshold</div>
                </div>
                <div className="rounded-lg border border-line bg-panel-2/50 px-3.5 py-2.5">
                  <div className="font-mono text-lg text-ink tabular-nums">{c.mutations.length}</div>
                  <div className="mt-1 text-[10.5px] text-faint">mutation(s) after shrinking</div>
                </div>
              </div>

              <div>
                <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
                  Minimal mutation sequence
                </div>
                <div className="grid gap-1.5">
                  {c.mutations.map((m, i) => (
                    <div key={i} className="rounded-md border border-line bg-ground/60 px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11.5px] text-brand">{m.op}</span>
                        <Pill>{m.family}</Pill>
                      </div>
                      <pre className="mt-1.5 overflow-x-auto font-mono text-[10.5px] text-muted">
                        {JSON.stringify(m.args)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
                  Clauses in force when it broke
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {c.responsible_clause_ids.map((id) => (
                    <Pill key={id} accent="var(--color-us)">
                      {id}
                    </Pill>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
                  Survives under
                </div>
                {c.passes_under_packs.length === 0 ? (
                  <p className="text-[12.5px] text-muted">
                    No comparator regime passes this counterexample — it is not a gap between
                    countries, it is a gap in all three.
                  </p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {c.passes_under_packs.map((p) => (
                      <Pill key={p} accent="var(--color-pass)">
                        {PACK_SHORT[p] ?? p} passes
                      </Pill>
                    ))}
                  </div>
                )}
              </div>

              <div className="min-w-0 rounded-md border border-line bg-ground/70 px-3 py-2.5">
                <div className="mb-1 font-mono text-[10px] tracking-wider text-faint uppercase">
                  Reproduce
                </div>
                <code className="block overflow-x-auto font-mono text-[10.5px] whitespace-pre text-muted">
                  {c.replay_cmd}
                </code>
              </div>
            </div>
          </Panel>
        ))}
      </div>
    </div>
  );
}
