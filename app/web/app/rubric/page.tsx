import Link from "next/link";

import { Panel, PanelHead, Pill, Provenance, Stat } from "@/components/ui";
import { getBundle } from "@/lib/data";
import type { RubricCheck } from "@/lib/types";

export const metadata = { title: "Rubric — CHAKRAVYUH" };

const STATUS_ACCENT: Record<string, string> = {
  PASS: "var(--color-pass)",
  WAIVED: "var(--color-block)",
  FAIL: "var(--color-fail)",
};

/** Which part of the submission each criterion letter belongs to. */
const FAMILY: Record<string, { title: string; blurb: string }> = {
  A: {
    title: "Knowledge base",
    blurb:
      "Whether the corpus is real: fields present, hashes reproducible, citations resolvable, retrieval scored.",
  },
  B: {
    title: "Agent capability",
    blurb:
      "Whether the simulation is a simulation: a real timeline, uneven information, cited answers, an adversarial injection that reaches the engine.",
  },
  C: { title: "Gap analysis", blurb: "Whether the register says what the brief asks it to say." },
  D: { title: "Audit", blurb: "Whether the record can be checked by someone who distrusts it." },
  E: {
    title: "ITU alignment",
    blurb: "Whether the standards mapping is generated from the code rather than claimed.",
  },
  F: { title: "Ground rules", blurb: "Whether the brief's own corrections hold across the repo." },
  G: {
    title: "Submission",
    blurb: "Whether what was promised exists, replays offline, and overclaims nothing.",
  },
};

function Row({ c }: { c: RubricCheck }) {
  const accent = STATUS_ACCENT[c.status] ?? "var(--color-muted)";
  return (
    <div className="grid gap-3 px-5 py-4 lg:grid-cols-[88px_1fr_96px] lg:gap-5">
      <div>
        <div className="font-mono text-[13px] font-semibold text-ink">{c.id}</div>
        <div className="mt-0.5 text-[10.5px] leading-snug text-faint">{c.criterion}</div>
      </div>
      <div className="min-w-0">
        <div className="text-[13px] leading-snug text-ink">{c.question}</div>
        <p className="mt-1.5 text-[12px] leading-relaxed break-words text-muted">{c.detail}</p>
        {c.waiver && (
          <p
            className="mt-2 rounded-md border px-3 py-2 text-[12px] leading-relaxed text-muted"
            style={{
              borderColor: "color-mix(in srgb, var(--color-block) 32%, transparent)",
              background: "color-mix(in srgb, var(--color-block) 6%, transparent)",
            }}
          >
            <span className="font-semibold text-block">Why this is waived. </span>
            {c.waiver}
          </p>
        )}
      </div>
      <div className="lg:text-right">
        <span
          className="inline-block rounded-md border px-2.5 py-1 font-mono text-[10.5px] font-bold tracking-[0.14em]"
          style={{
            color: accent,
            borderColor: `color-mix(in srgb, ${accent} 38%, transparent)`,
            background: `color-mix(in srgb, ${accent} 10%, transparent)`,
          }}
        >
          {c.status}
        </span>
      </div>
    </div>
  );
}

export default function RubricPage() {
  const b = getBundle();
  const r = b.rubric;
  const families = [...new Set(r.checks.map((c) => c.id[0]))].sort();

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          {r.source || "Rubric"}
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">
          Audited against the rubric, by a script
        </h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          Every line on this page is measured when{" "}
          <span className="font-mono text-ink">{r.command}</span> runs. Nothing here is asserted by
          hand: each check opens the artefact it is about, counts what it finds, and writes the
          sentence you read. Delete the artefact and the check fails.
        </p>
        <p className="mt-4 text-[13.5px] leading-relaxed text-muted">
          A <span className="font-mono text-block">WAIVED</span> check is one whose condition does
          not hold and which we decided should not. The rubric permits that; what it does not
          permit is a waiver without a reason — so the reason lives in the check&apos;s own code
          and is printed below. Running with{" "}
          <span className="font-mono text-ink">--strict</span> fails on a waiver too, which is the
          mode to use when you want the state with no allowances made.
        </p>
        <Provenance>
          python app/scripts/rubric_audit.py — writes docs/rubric_status.html and
          outputs/rubric_status.json
        </Provenance>
      </header>

      <div className="mb-7 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={r.totals.pass} label="pass" sub={`of ${r.totals.checks} checks`} accent="var(--color-pass)" />
        <Stat
          value={r.totals.waived}
          label="waived"
          sub="each with a reason, printed"
          accent="var(--color-block)"
        />
        <Stat
          value={r.totals.fail}
          label="fail"
          sub={r.totals.fail === 0 ? "nothing outstanding" : "blocking"}
          accent={r.totals.fail === 0 ? "var(--color-pass)" : "var(--color-fail)"}
        />
        <Stat
          value={`${Math.round((r.totals.pass / Math.max(r.totals.checks, 1)) * 100)}%`}
          label="passing outright"
          sub="waivers excluded"
          accent="var(--color-us)"
        />
      </div>

      <Panel className="mb-6 overflow-hidden">
        <PanelHead kicker="At a glance" title="Every check, by criterion" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[12.5px]">
            <thead className="font-mono text-[10px] tracking-wider text-faint uppercase">
              <tr className="border-b border-line">
                <th className="px-5 py-2.5 font-medium">ID</th>
                <th className="px-4 py-2.5 font-medium">Criterion</th>
                <th className="px-4 py-2.5 font-medium">Check</th>
                <th className="px-5 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {r.checks.map((c) => (
                <tr key={c.id} className="border-b border-line/50 last:border-0">
                  <td className="px-5 py-2.5 font-mono text-ink">
                    <a href={`#${c.id}`} className="underline-offset-2 hover:underline">
                      {c.id}
                    </a>
                  </td>
                  <td className="px-4 py-2.5 text-muted">{c.criterion}</td>
                  <td className="px-4 py-2.5 text-muted">{c.question}</td>
                  <td className="px-5 py-2.5">
                    <Pill accent={STATUS_ACCENT[c.status]}>{c.status}</Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-5">
        {families.map((f) => {
          const checks = r.checks.filter((c) => c.id[0] === f);
          const meta = FAMILY[f];
          return (
            <Panel key={f} className="overflow-hidden">
              <PanelHead
                kicker={`Criterion ${f}`}
                title={meta?.title ?? `Criterion ${f}`}
                right={
                  <div className="flex gap-1.5">
                    {(["PASS", "WAIVED", "FAIL"] as const).map((s) => {
                      const n = checks.filter((c) => c.status === s).length;
                      return n ? (
                        <Pill key={s} accent={STATUS_ACCENT[s]}>
                          {n} {s.toLowerCase()}
                        </Pill>
                      ) : null;
                    })}
                  </div>
                }
              />
              {meta && (
                <p className="border-b border-line px-5 py-3 text-[12.5px] leading-relaxed text-muted">
                  {meta.blurb}
                </p>
              )}
              <div className="divide-y divide-line">
                {checks.map((c) => (
                  <div key={c.id} id={c.id} className="scroll-mt-24">
                    <Row c={c} />
                  </div>
                ))}
              </div>
            </Panel>
          );
        })}
      </div>

      <Panel className="mt-6 p-6">
        <h2 className="text-[15px] font-semibold tracking-tight">
          What a passing audit does and does not mean
        </h2>
        <p className="mt-3 max-w-4xl text-[13px] leading-relaxed text-muted">
          It means the artefacts exist, agree with each other, and say what they claim to say. It
          does not mean the law is correctly encoded — that rests on {b.kb_graph.real_text} of{" "}
          {b.kb.total} clause records holding the instrument&apos;s own words, and on three
          documents we do not hold. Those limits are in the register, in the waivers above, and on{" "}
          <Link href="/#limits" className="text-brand underline underline-offset-2">
            the main page
          </Link>
          . No part of this project claims ITU certification, approval or compliance; check G3
          exists to keep it that way.
        </p>
      </Panel>
    </div>
  );
}
