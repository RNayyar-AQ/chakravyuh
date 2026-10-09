import Link from "next/link";

import { Chakra } from "@/components/Chakra";
import { Scorecard } from "@/components/Scorecard";
import { Dot, Panel, PanelHead, Pill, Provenance, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { PACK_ACCENT, packOrder, tPlus } from "@/lib/format";

/** The three layers, named the way the code names them. */
const LAYERS = [
  {
    tag: "Propose",
    node: "Y.3172 node M",
    title: "Six role-bound agents",
    body:
      "Each agent sees only its own inbox — redacted, delayed, incomplete — and returns a typed proposal citing the rule it believes authorises it. Agents may be rule twins, an LLM, or an external tier; the simulator cannot tell them apart.",
    accent: "#4aa8ff",
  },
  {
    tag: "Decide",
    node: "Y.3172 node D",
    title: "One deterministic Game Master",
    body:
      "Every proposal is resolved against one world state and one rulebook, in one fixed order. The policy engine is a pure function with no model in its import graph, and a test enforces that. An overreaching proposal is not filtered out — it is BLOCKed and recorded.",
    accent: "var(--color-brand)",
  },
  {
    tag: "Prove",
    node: "Y.3172 node SINK",
    title: "A hash-chained ledger",
    body:
      "Events, proposals, verdicts, effects and property checks are appended to a chain where each entry commits to the one before it. Change any byte and verification names the sequence number that broke.",
    accent: "#2dd4a7",
  },
];

export default function Home() {
  const b = getBundle();
  const packs = [...b.packs].sort((a, c) => packOrder(a.pack_id, c.pack_id));
  const totalEntries = b.ledger.runs.reduce((n, r) => n + r.entries, 0);
  const allVerified = b.ledger.runs.every((r) => r.verified);
  const tamperCaught = b.ledger.tamper.length > 0 && b.ledger.tamper.every((t) => !t.verified);
  const fuzzRuns = b.fuzz.runs.reduce((n, r) => n + (r.runs_completed ?? 0), 0);
  const verbatim = b.kb.total - (b.kb.verbatim_status["unverified_summary"] ?? 0);
  const indiaFails = b.scorecard.properties.filter((p) => p.fails_under.includes("india_current"));

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
            the law of three countries, and measures four things a telecom emergency response must
            never get wrong. Agents reason. Rules decide. Everything is written to a tamper-evident
            ledger, so every claim on this site has a command that reproduces it.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/simulation"
              className="rounded-lg bg-brand px-5 py-2.5 text-[13px] font-semibold text-ground transition-opacity hover:opacity-90"
            >
              Replay the simulation →
            </Link>
            <Link
              href="/gaps"
              className="rounded-lg border border-line-bright px-5 py-2.5 text-[13px] font-medium text-ink transition-colors hover:bg-panel-2"
            >
              Read the gap register
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
            properties that at least one comparator regime passes on identical input. That
            difference is the finding, and it is attributable to specific clauses.
          </p>
          <Provenance>
            python scripts/run_demo.py --pack india_current --scenario
            data/scenarios/amphan_2020.yaml --seed 0
          </Provenance>
        </div>
      </Panel>

      {/* ------------------------------------------------------------- the regimes */}
      <div className="mt-6 grid gap-4 md:grid-cols-3">
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

      {/* --------------------------------------------------------------- how it works */}
      <section className="mt-20">
        <div className="mb-6 max-w-3xl">
          <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            Architecture
          </div>
          <h2 className="text-2xl font-semibold tracking-tight">
            Agents propose. Deterministic code decides.
          </h2>
          <p className="mt-3 text-[14px] leading-relaxed text-muted">
            The split is DeepMind&apos;s Concordia pattern with one deliberate change: the Game
            Master is ordinary Python, not a model. That is what makes a run reproducible, and it is
            why a judge can re-derive every number here instead of trusting it.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {LAYERS.map((l, i) => (
            <Panel key={l.tag} className="relative overflow-hidden p-5" grid>
              <div
                className="absolute inset-x-0 top-0 h-px"
                style={{ background: `linear-gradient(90deg, transparent, ${l.accent}, transparent)` }}
              />
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] font-semibold tracking-[0.16em] uppercase" style={{ color: l.accent }}>
                  {i + 1} · {l.tag}
                </span>
                <Pill>{l.node}</Pill>
              </div>
              <h3 className="mt-3 text-[15px] font-semibold text-ink">{l.title}</h3>
              <p className="mt-2 text-[12.5px] leading-relaxed text-muted">{l.body}</p>
            </Panel>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------ what is the AI */}
      <section className="mt-16 grid gap-4 lg:grid-cols-[1.1fr_1fr]">
        <Panel className="p-6">
          <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            Honest answer
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Where the AI actually is</h2>
          <ul className="mt-4 grid gap-3.5">
            {[
              {
                k: "Agent reasoning",
                v: "Three interchangeable tiers behind one Agent protocol: deterministic rule twins, an LLM tier through a record/replay cache, and an optional external tier. The demo on this site runs the rule twins, so it needs no credential and no network.",
              },
              {
                k: "Retrieval",
                v: `Hybrid BM25 + vector embeddings fused by Reciprocal Rank Fusion over ${b.kb.total} clause records, scored on ${b.retrieval[0]?.questions ?? 0} questions including deliberately unanswerable ones.`,
              },
              {
                k: "Search",
                v: `Hypothesis property-based fuzzing explored ${fuzzRuns.toLocaleString()} mutated worlds and shrank each violation to a minimal counterexample. This is the component that finds the failures.`,
              },
            ].map((r) => (
              <li key={r.k} className="border-l-2 border-line-bright pl-3.5">
                <div className="text-[13px] font-semibold text-ink">{r.k}</div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{r.v}</p>
              </li>
            ))}
          </ul>
          <p className="mt-5 rounded-lg border border-line bg-panel-2/60 px-4 py-3 text-[12.5px] leading-relaxed text-muted">
            <span className="font-semibold text-ink">No model decides anything.</span> The policy
            engine has no model in its transitive import graph, and a test fails the build if one
            appears. A model can propose an unlawful action; it cannot perform one.
          </p>
        </Panel>

        <div className="grid grid-cols-2 gap-4 content-start">
          <Stat
            value={b.kb.total}
            label="clause records"
            sub={`${verbatim} carry the instrument's own words`}
            accent="var(--color-us)"
          />
          <Stat
            value={totalEntries.toLocaleString()}
            label="ledger entries"
            sub={allVerified ? "every chain verifies" : "verification failed"}
            accent="var(--color-allow)"
          />
          <Stat
            value={fuzzRuns.toLocaleString()}
            label="worlds fuzzed"
            sub={`${b.fuzz.cards.length} minimal counterexamples`}
            accent="var(--color-block)"
          />
          <Stat
            value={b.gaps.length}
            label="registered gaps"
            sub="each with a replay command"
            accent="var(--color-human)"
          />
          <div className="col-span-2">
            <Panel className="p-5">
              <div className="flex items-center gap-2">
                <Dot accent={tamperCaught ? "var(--color-allow)" : "var(--color-fail)"} />
                <h3 className="text-[13px] font-semibold text-ink">Tamper check</h3>
              </div>
              <p className="mt-2 text-[12.5px] leading-relaxed text-muted">
                {tamperCaught
                  ? "A single field was edited in a sealed ledger. Verification caught it and named the exact sequence number — in every case."
                  : "Tamper demonstration has not been run."}
              </p>
              <div className="mt-3 grid gap-1.5">
                {b.ledger.tamper.map((t) => (
                  <div key={t.run_id} className="font-mono text-[10.5px] text-faint">
                    <span style={{ color: "var(--color-fail)" }}>✕</span>{" "}
                    {t.run_id.replace(".tampered", "")} — {t.message}
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      </section>

      {/* ----------------------------------------------------------------- limits */}
      <section className="mt-16">
        <Panel className="p-6">
          <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            What this is not
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Limits, stated up front</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {[
              {
                t: "It is a simulation",
                d: "No money, no casualties, no confidence intervals. A margin is a distance from a threshold inside this model, not a prediction about the world.",
              },
              {
                t: `${b.kb.verbatim_status["unverified_summary"] ?? 0} clauses are still summaries`,
                d: `Of ${b.kb.total} records, ${verbatim} carry primary text. A finding resting on a summary is capped at "likely" and never reads "certain".`,
              },
              {
                t: "Three documents are missing",
                d: "The complete TCS Rules 2024, the 2025 amendment and DoT SOP-2020 are not public in a verifiable form. Each one caps a specific finding, and the register says which.",
              },
            ].map((x) => (
              <div key={x.t} className="rounded-lg border border-line bg-panel-2/50 p-4">
                <div className="text-[13px] font-semibold text-ink">{x.t}</div>
                <p className="mt-1.5 text-[12px] leading-relaxed text-muted">{x.d}</p>
              </div>
            ))}
          </div>
        </Panel>
      </section>
    </div>
  );
}
