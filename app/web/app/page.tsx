import Link from "next/link";

import { Chakra } from "@/components/Chakra";
import { LiveRun } from "@/components/LiveRun";
import { Flow } from "@/components/sections/Flow";
import { Tech } from "@/components/sections/Tech";
import { Dot, Pill, Section, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { packOrder, tPlus } from "@/lib/format";

export default function Home() {
  const b = getBundle();
  const packs = [...b.packs].sort((a, c) => packOrder(a.pack_id, c.pack_id));
  const totalEntries = b.ledger.runs.reduce((n, r) => n + r.entries, 0);
  const tamperCaught = b.ledger.tamper.length > 0 && b.ledger.tamper.every((t) => !t.verified);
  const fuzzBudget = b.fuzz.runs.reduce((n, r) => n + (r.examples_budgeted ?? 0), 0);

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
            ledger. Run it from this page and watch the pipeline produce those numbers live.
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
              href="#tech"
              className="rounded-lg border border-line px-5 py-2.5 text-[13px] font-medium text-muted transition-colors hover:bg-panel-2 hover:text-ink"
            >
              The stack
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

      <div className="mt-12 grid gap-16 pb-16">
        {/* ------------------------------------------------------------- the flow */}
        <Section
          id="flow"
          kicker="Y.3172 pipeline · SRC → C → PP → M → P → D → SINK"
          title="The flow, end to end"
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

        {/* ------------------------------------------------------------- the tech */}
        <Section
          id="tech"
          kicker="Stack"
          title="The tech this runs on"
          lead={
            <>
              Grouped by the pipeline stage it serves. The deterministic core carries the
              decisions; the language model is optional and sits outside it, so pulling the LLM
              out changes the prose and not one verdict.
            </>
          }
          provenance="pyproject.toml · requirements.txt · app/web/package.json · vercel.json"
        >
          <Tech />
        </Section>
      </div>
    </div>
  );
}
