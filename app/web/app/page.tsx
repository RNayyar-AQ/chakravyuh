import Link from "next/link";

import { Chakra } from "@/components/Chakra";
import { GapExplorer } from "@/components/GapExplorer";
import { LiveRun } from "@/components/LiveRun";
import { Scorecard } from "@/components/Scorecard";
import { TimelineExplorer } from "@/components/TimelineExplorer";
import { Agents } from "@/components/sections/Agents";
import { Derivations } from "@/components/sections/Derivations";
import { Evidence } from "@/components/sections/Evidence";
import { FailureAtlas } from "@/components/sections/FailureAtlas";
import { Flow } from "@/components/sections/Flow";
import { KnowledgeBase } from "@/components/sections/KnowledgeBase";
import { Retrieval } from "@/components/sections/Retrieval";
import { Standards } from "@/components/sections/Standards";
import { TraceWalk } from "@/components/sections/TraceWalk";
import { Dot, Panel, PanelHead, Pill, Provenance, Section, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { PACK_ACCENT, packOrder, tPlus } from "@/lib/format";

export default function Home() {
  const b = getBundle();
  const packs = [...b.packs].sort((a, c) => packOrder(a.pack_id, c.pack_id));
  const totalEntries = b.ledger.runs.reduce((n, r) => n + r.entries, 0);
  const tamperCaught = b.ledger.tamper.length > 0 && b.ledger.tamper.every((t) => !t.verified);
  const fuzzBudget = b.fuzz.runs.reduce((n, r) => n + (r.examples_budgeted ?? 0), 0);
  const indiaFails = b.scorecard.properties.filter((p) => p.fails_under.includes("india_current"));
  const certain = b.gaps.filter((g) => g.confidence === "certain").length;
  const negative = b.gaps.filter((g) => g.negative_finding === "yes").length;
  const simulation = b.gaps.filter((g) => g.source === "simulation").length;
  const unverified = b.kb.verbatim_status["unverified_summary"] ?? 0;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6">
      {/* ---------------------------------------------------------------- hero */}
      <section className="cv-rise grid items-center gap-10 py-14 lg:grid-cols-[1.35fr_1fr] lg:py-20">
        <div>
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <Pill accent="var(--color-brand)">ITU AI for Good · Sandbox Build-a-thon 5.0</Pill>
            <Pill>Team Quantum QAI</Pill>
          </div>
          <h1 className="text-[2.1rem] leading-[1.1] font-semibold tracking-tight text-balance sm:text-5xl">
            One cyclone. Three legal regimes.
            <br />
            <span className="text-brand">Provably different outcomes.</span>
          </h1>
          <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-muted">
            CHAKRAVYUH replays a real cyclone — {b.scenario.title.split("—")[0].trim()} — against
            the law of three countries and measures four things a telecom emergency response must
            never get wrong. Agents reason. Rules decide. Everything lands in a tamper-evident
            ledger, so every number below is followed, on this page, back to the entry that
            produced it.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="#live"
              className="rounded-lg bg-brand px-5 py-2.5 text-[13px] font-semibold text-ground transition-opacity hover:opacity-90"
            >
              ▶ Run the backend live
            </a>
            <a
              href="#flow"
              className="rounded-lg border border-line-bright px-5 py-2.5 text-[13px] font-medium text-ink transition-colors hover:bg-panel-2"
            >
              Walk the pipeline
            </a>
            <a
              href="#trace"
              className="rounded-lg border border-line px-5 py-2.5 text-[13px] font-medium text-muted transition-colors hover:bg-panel-2 hover:text-ink"
            >
              Follow one cyclone warning
            </a>
            <Link
              href="/rubric"
              className="rounded-lg border border-line px-5 py-2.5 text-[13px] font-medium text-muted transition-colors hover:bg-panel-2 hover:text-ink"
            >
              Rubric: {b.rubric.totals.pass} pass · {b.rubric.totals.fail} fail
            </Link>
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 font-mono text-[11px] text-faint">
            <span className="flex items-center gap-1.5">
              <Dot accent="var(--color-allow)" /> {b.scenario.areas.length} real districts
            </span>
            <span className="flex items-center gap-1.5">
              <Dot accent="var(--color-us)" /> horizon {tPlus(b.scenario.horizon_min)}
            </span>
            <span className="flex items-center gap-1.5">
              <Dot accent="var(--color-human)" /> tick {b.scenario.tick_min} min
            </span>
            <span className="flex items-center gap-1.5">
              <Dot accent="var(--color-india)" /> seed 0
            </span>
          </div>
        </div>

        <div className="relative hidden justify-center lg:flex">
          <div
            className="absolute inset-0 rounded-full blur-3xl"
            style={{ background: "radial-gradient(circle, #ff7a4522 0%, transparent 66%)" }}
          />
          <Chakra size={330} />
        </div>
      </section>

      {/* ------------------------------------------------------- run it from here */}
      <LiveRun packs={packs.map((p) => p.pack_id)} />

      {/* ---------------------------------------------------------- the scorecard */}
      <Panel className="overflow-hidden">
        <PanelHead
          kicker="The result"
          title="The same seed, run under three rulebooks"
          right={
            <div className="hidden items-center gap-3 font-mono text-[10.5px] text-faint sm:flex">
              <span className="flex items-center gap-1.5">
                <Dot accent="var(--color-pass)" /> holds
              </span>
              <span className="flex items-center gap-1.5">
                <Dot accent="var(--color-fail)" /> violated
              </span>
            </div>
          }
        />
        <Scorecard properties={b.scorecard.properties} packs={b.packs} />
        <div className="border-t border-line px-5 py-4">
          <p className="text-[13px] leading-relaxed text-muted">
            Nothing about the hazard changed between these columns — same districts, same IMD
            timeline, same agents, same seed. Only the rulebook changed. India&apos;s current law
            fails{" "}
            <span className="font-mono text-ink">
              {indiaFails.length} of {b.scorecard.properties.length}
            </span>{" "}
            properties that at least one comparator regime passes on identical input.{" "}
            <a href="#numbers" className="text-brand underline underline-offset-2">
              Every one of those margins is recomputed further down the page.
            </a>
          </p>
          <Provenance>
            python app/scripts/run_demo.py --pack india_current --scenario
            data/scenarios/amphan_2020.yaml --seed 0
          </Provenance>
        </div>
      </Panel>

      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {packs.map((p) => {
          const fails = b.scorecard.properties.filter((q) => q.fails_under.includes(p.pack_id));
          return (
            <Panel key={p.pack_id} className="p-5">
              <div className="flex items-center gap-2">
                <Dot accent={PACK_ACCENT[p.pack_id]} />
                <h3
                  className="font-mono text-[13px] font-semibold tracking-wide"
                  style={{ color: PACK_ACCENT[p.pack_id] }}
                >
                  {p.label}
                </h3>
              </div>
              <p className="mt-2.5 text-[12.5px] leading-relaxed text-muted">{p.blurb}</p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                {b.scorecard.properties.map((q) => {
                  const pass = q.passes_under.includes(p.pack_id);
                  return (
                    <Pill
                      key={q.property_id}
                      accent={pass ? "var(--color-pass)" : "var(--color-fail)"}
                      title={q.text}
                    >
                      {q.property_id} {pass ? "✓" : "✕"}
                    </Pill>
                  );
                })}
              </div>
              <div className="mt-4 border-t border-line pt-3 font-mono text-[10.5px] text-faint">
                pack {p.pack_id} · v{p.version} · {p.rule_count} rules ·{" "}
                {fails.length === 0 ? "no violations" : `${fails.length} violated`}
              </div>
            </Panel>
          );
        })}
      </div>

      <div className="mt-16 grid gap-16 pb-10">
        {/* ------------------------------------------------------------- 1. flow */}
        <Section
          id="flow"
          kicker="Y.3172 pipeline · SRC → C → PP → M → P → D → SINK"
          title="The flow this whole thing is illustrating"
          lead={
            <>
              A gazette PDF enters on the left and a measured, attributable failure comes out on
              the right. Every stage is a real module with a real command, and the figure on each
              stage is what that stage produced in the run this page is built from — not an
              illustration of one. Click a stage.
            </>
          }
        >
          <Flow stages={b.flow} />
          <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat
              value={b.kb.total}
              label="clause records"
              sub={`${b.kb_graph.real_text} carry the instrument's own words`}
              accent="var(--color-us)"
            />
            <Stat
              value={totalEntries.toLocaleString()}
              label="ledger entries"
              sub={tamperCaught ? "every chain verifies; edits are caught" : "verification failed"}
              accent="var(--color-allow)"
            />
            <Stat
              value={fuzzBudget.toLocaleString()}
              label="worlds searched"
              sub={`${b.fuzz.cards.length} minimal counterexamples`}
              accent="var(--color-block)"
            />
            <Stat
              value={b.gaps.length}
              label="registered gaps"
              sub="each with a replay command"
              accent="var(--color-human)"
            />
          </div>
        </Section>

        {/* -------------------------------------------------------- 2. knowledge */}
        <Section
          id="knowledge"
          kicker="Y.3172 nodes SRC, C, PP"
          title="What the knowledge base actually looks like"
          lead={
            <>
              Two indexes over the same corpus, used for two different things. One is exact and
              hash-checked and feeds the engine; the other is ranked and feeds a person asking a
              question. Keeping them apart is why a legality decision is never downstream of a
              similarity score.
            </>
          }
          provenance="python app/scripts/build_kb.py — writes docs/kb_report.md"
        >
          <KnowledgeBase b={b} />
        </Section>

        {/* -------------------------------------------------------- 3. retrieval */}
        <Section
          id="retrieval"
          kicker="Y.3172 node PP"
          title="Retrieval, with the fusion written out"
          lead={
            <>
              Five retrievers scored over the same question set, and then one question carried
              through all of them so the ranking can be checked by hand rather than taken on
              trust.
            </>
          }
          provenance="python app/scripts/eval_retrieval.py — writes outputs/retrieval_eval.json"
        >
          <Retrieval b={b} />
        </Section>

        {/* ------------------------------------------------------------ 4. agents */}
        <Section
          id="agents"
          kicker="Y.3172 node M"
          title="Who is in the room, and what each one cannot see"
          lead={
            <>
              Powers come from the rulebook, never from the agent. The same six agents behave
              differently under three legal regimes without one line of agent code changing — which
              is what makes the comparison a comparison of law rather than of prompts.
            </>
          }
          provenance="app/chakravyuh/agents/roles.py · app/chakravyuh/agents/base.py"
        >
          <Agents roles={b.roles} />
        </Section>

        {/* ------------------------------------------------------------- 5. trace */}
        <Section
          id="trace"
          kicker="Replay · amphan_2020 · india_current · seed 0"
          title="One event, followed to the number it moves"
          lead={
            <>
              This is the whole argument in six steps. A cyclone warning and a forged suspension
              order are each followed from the moment the world released them, through who heard
              them and when, to the clause an agent cited, the verdict the engine returned, the
              change to the world, and the exact property margin that changed as a result.
            </>
          }
          provenance="every step below is an entry in runs/amphan_2020__india_current__rule__seed0.jsonl"
        >
          <TraceWalk traces={b.traces} clauses={b.clauses} />
        </Section>

        {/* ----------------------------------------------------------- 6. numbers */}
        <Section
          id="numbers"
          kicker="Y.3172 node SINK"
          title="Where the numbers come from"
          lead={
            <>
              A margin is a distance from a threshold, and both sides of that subtraction are
              recorded by the run itself. The export walks the ledger, takes those operands, redoes
              the arithmetic and compares its answer with the margin the run wrote — so a
              disagreement would appear here rather than be smoothed over.
            </>
          }
          provenance="app/chakravyuh/fuzz/properties.py — check_p1 … check_p4"
        >
          <Derivations
            derivations={b.derivations}
            packs={b.packs}
            properties={b.properties}
          />
        </Section>

        {/* ------------------------------------------------------------ 7. replay */}
        <Section
          id="replay"
          kicker={`Ledger replay · ${b.scenario.scenario_id} · seed 0`}
          title="The full run, as it was sealed"
          lead={
            <>
              {b.scenario.description} Switch the rulebook to watch the same six agents, fed the
              same events in the same order, be answered differently. Expand any row for the
              reasoning, the rules applied and the clauses behind them.
            </>
          }
          provenance="verify: python app/scripts/verify_ledger.py · replay: bash app/scripts/replay_demo.sh"
        >
          <TimelineExplorer packs={packs} />
          <Panel className="mt-4 p-5">
            <h3 className="text-[14px] font-semibold text-ink">Reading a verdict</h3>
            <dl className="mt-3 grid gap-3 sm:grid-cols-3">
              {[
                [
                  "ALLOW",
                  "A rule in this pack permits the action. It executes and changes the world.",
                  "var(--color-allow)",
                ],
                [
                  "BLOCK",
                  "No rule permits it, or a rule forbids it. The attempt is recorded, not erased — a filtered overreach would be a finding destroyed.",
                  "var(--color-block)",
                ],
                [
                  "NEEDS_HUMAN",
                  "Permitted but irreversible, so it is held for authorisation. Y.3173 human-in-the-loop. The report never claims a human reviewed it when the gate auto-released.",
                  "var(--color-human)",
                ],
              ].map(([k, v, c]) => (
                <div key={k} className="rounded-lg border border-line bg-panel-2/50 p-3.5">
                  <dt
                    className="font-mono text-[11px] font-semibold tracking-wide"
                    style={{ color: c }}
                  >
                    {k}
                  </dt>
                  <dd className="mt-1.5 text-[12px] leading-relaxed text-muted">{v}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </Section>

        {/* ---------------------------------------------------------- 8. failures */}
        <Section
          id="failures"
          kicker="Hypothesis · property-based fuzzing"
          title="Failure atlas"
          lead={
            <>
              A stateful fuzzer mutates the world — escalating damage, delaying channels, forging
              orders — and asserts the four properties after every run. When one breaks, Hypothesis
              shrinks the mutation sequence to the smallest one that still breaks it. What survives
              shrinking is a minimal, attributable counterexample, not an anecdote.
            </>
          }
          provenance="python app/scripts/run_fuzz.py --pack <pack> --scenario amphan_2020"
        >
          <FailureAtlas runs={b.fuzz.runs} cards={b.fuzz.cards} />
        </Section>

        {/* -------------------------------------------------------------- 9. gaps */}
        <Section
          id="gaps"
          kicker="outputs/gap_register.csv"
          title="Gap register"
          lead={
            <>
              Every row names a gap, the Indian instance, what a neighbouring and a global regime
              do instead, the evidence, and the ITU instrument that already addresses it.
              Confidence is <span className="font-semibold text-ink">computed, never asserted</span>
              : a row reads <span className="font-mono">certain</span> only when every clause it
              cites carries the instrument&apos;s own words.
            </>
          }
          provenance="python app/scripts/run_demo.py — writes the register, then reads it back"
        >
          <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat value={b.gaps.length} label="registered gaps" accent="var(--color-brand)" />
            <Stat
              value={simulation}
              label="from simulation"
              sub={`${b.gaps.length - simulation} from documents`}
              accent="var(--color-us)"
            />
            <Stat
              value={negative}
              label="negative findings"
              sub="an absence, which needs quotable text"
              accent="var(--color-human)"
            />
            <Stat
              value={`${certain}/${b.gaps.length}`}
              label="rated certain"
              sub={certain === 0 ? "every row still rests on at least one summary" : undefined}
              accent={certain === 0 ? "var(--color-block)" : "var(--color-pass)"}
            />
          </div>
          <GapExplorer rows={b.gaps} />
        </Section>

        {/* --------------------------------------------------------- 10. evidence */}
        <Section
          id="evidence"
          kicker="Provenance and audit"
          title="The place to doubt everything above"
          lead={
            <>
              A claim about the law is only as good as the text behind it. Every source document
              carries a SHA-256 and a completeness check, and every run carries a hash chain that
              names the sequence number where an edit broke it.
            </>
          }
          provenance="python app/scripts/fetch_sources.py --verify · python app/scripts/verify_ledger.py --all"
        >
          <Evidence b={b} />
        </Section>

        {/* -------------------------------------------------------- 11. standards */}
        <Section
          id="standards"
          kicker="Conformance"
          title="Standards, mapped from the code"
          lead={
            <>
              Claiming conformance on a slide is easy. Here a decorator registers each entry point
              against its ITU-T Y.3172 node, and the map is produced by walking the package at
              build time.
            </>
          }
          provenance="python app/scripts/gen_y3172_map.py — writes docs/y3172_map.md"
        >
          <Standards nodes={b.y3172} />
        </Section>

        {/* ------------------------------------------------------------ 12. limits */}
        <Section
          id="limits"
          kicker="What this is not"
          title="Limits, stated up front"
          lead="A result that does not say what it cannot support is not a result."
        >
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                t: "It is a simulation",
                d: "No money, no casualties, no confidence intervals. A margin is a distance from a threshold inside this model, not a prediction about the world.",
              },
              {
                t: `${unverified} clauses are still summaries`,
                d: `Of ${b.kb.total} records, ${b.kb_graph.real_text} carry primary text. A finding resting on a summary is capped at "likely" and never reads "certain" — which is why none of the ${b.gaps.length} rows does.`,
              },
              {
                t: "Three documents are missing",
                d: "The complete TCS Rules 2024, the 2025 amendment and DoT SOP-2020 are not public in a verifiable form. Each caps a specific finding, and the register says which.",
              },
            ].map((x) => (
              <Panel key={x.t} className="p-5">
                <div className="text-[13px] font-semibold text-ink">{x.t}</div>
                <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{x.d}</p>
              </Panel>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
