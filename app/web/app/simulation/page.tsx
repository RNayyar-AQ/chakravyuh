import { Panel, Provenance } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { packOrder } from "@/lib/format";

import { TimelineExplorer } from "./TimelineExplorer";

export const metadata = { title: "Simulation — CHAKRAVYUH" };

export default function SimulationPage() {
  const b = getBundle();
  const packs = [...b.packs].sort((x, y) => packOrder(x.pack_id, y.pack_id));

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          Ledger replay · {b.scenario.scenario_id} · seed 0
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">{b.scenario.title}</h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">{b.scenario.description}</p>
        <p className="mt-4 text-[13.5px] leading-relaxed text-muted">
          Below is the sealed ledger of one run, not a re-enactment. Switch the rulebook to watch
          the same six agents, fed the same events in the same order, be answered differently.
          Expand any row for the reasoning the agent gave, the rules the engine applied and the
          clauses behind them.
        </p>
        <Provenance>
          verify: python app/scripts/verify_ledger.py · replay: bash app/scripts/replay_demo.sh
        </Provenance>
      </header>

      <TimelineExplorer packs={packs} />

      <Panel className="mt-6 p-5">
        <h2 className="text-[14px] font-semibold text-ink">Reading a verdict</h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-3">
          {[
            ["ALLOW", "A rule in this pack permits the action. It executes and changes the world.", "var(--color-allow)"],
            ["BLOCK", "No rule permits it, or a rule forbids it. The attempt is recorded, not erased — a filtered overreach would be a finding destroyed.", "var(--color-block)"],
            ["NEEDS_HUMAN", "Permitted but marked irreversible, so it is held for authorisation. Y.3173 human-in-the-loop. The report never claims a human reviewed it when the gate auto-released.", "var(--color-human)"],
          ].map(([k, v, c]) => (
            <div key={k} className="rounded-lg border border-line bg-panel-2/50 p-3.5">
              <dt className="font-mono text-[11px] font-semibold tracking-wide" style={{ color: c }}>
                {k}
              </dt>
              <dd className="mt-1.5 text-[12px] leading-relaxed text-muted">{v}</dd>
            </div>
          ))}
        </dl>
      </Panel>
    </div>
  );
}
