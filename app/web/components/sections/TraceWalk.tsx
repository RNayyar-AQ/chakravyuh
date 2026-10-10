"use client";

import { useState } from "react";

import { ClauseText } from "@/components/ClauseText";
import { Dot, Panel, Pill } from "@/components/ui";
import { DECISION_ACCENT, ROLE_ACCENT, ROLE_SHORT, istClock, signed, tPlus } from "@/lib/format";
import type { ClauseRecord, Trace } from "@/lib/types";

const STEP = [
  { n: 1, label: "Released", node: "D" },
  { n: 2, label: "Delivered", node: "D" },
  { n: 3, label: "Proposed", node: "M" },
  { n: 4, label: "Decided", node: "P" },
  { n: 5, label: "World changed", node: "D" },
  { n: 6, label: "Number moved", node: "SINK" },
];

function Step({ n, title, node, children }: { n: number; title: string; node: string; children: React.ReactNode }) {
  return (
    <div className="relative grid gap-3 border-l border-line pl-6 pb-6 last:pb-0 sm:grid-cols-[1fr]">
      <span className="absolute top-0.5 -left-[11px] flex size-[21px] items-center justify-center rounded-full border border-line-bright bg-panel font-mono text-[10px] text-muted">
        {n}
      </span>
      <div>
        <div className="flex items-center gap-2">
          <h4 className="text-[13px] font-semibold text-ink">{title}</h4>
          <Pill>node {node}</Pill>
        </div>
        <div className="mt-2.5">{children}</div>
      </div>
    </div>
  );
}

/** One real event, followed from release to the margin it moves. */
export function TraceWalk({
  traces,
  clauses,
}: {
  traces: Trace[];
  clauses: Record<string, ClauseRecord>;
}) {
  const [t, setT] = useState(0);
  const [p, setP] = useState(0);
  const trace = traces[t];
  if (!trace || !trace.event) return null;

  const proposal = trace.proposals[Math.min(p, trace.proposals.length - 1)];
  const verdict = proposal?.verdict ?? null;
  const effect = proposal ? trace.effects.find((e) => e.seq > proposal.seq) : trace.effects[0];
  const ev = trace.event;
  const forged = ev.authentic === false;

  return (
    <Panel className="overflow-hidden">
      <div className="flex flex-wrap items-center gap-2 border-b border-line px-5 py-3.5">
        <div className="mr-auto">
          <div className="font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            Follow one event
          </div>
          <h3 className="mt-1 text-[15px] font-semibold text-ink">
            {ev.type.replace(/_/g, " ")} · {ev.event_id}
          </h3>
        </div>
        {traces.map((x, i) => (
          <button
            key={x.event_id}
            onClick={() => {
              setT(i);
              setP(0);
            }}
            className={`rounded-md border px-3 py-1.5 font-mono text-[11px] transition-colors ${
              i === t
                ? "border-line-bright bg-panel-2 text-ink"
                : "border-line text-muted hover:text-ink"
            }`}
          >
            {x.event_id}
            <span className="ml-1.5 text-[10px] text-faint">
              {x.event?.authentic === false ? "forged" : "authentic"}
            </span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-x-5 gap-y-1.5 border-b border-line bg-ground/40 px-5 py-2.5 font-mono text-[10.5px] text-faint">
        {STEP.map((s) => (
          <span key={s.n}>
            {s.n}. {s.label}
          </span>
        ))}
      </div>

      <div className="grid gap-0 p-5 lg:grid-cols-[1.05fr_1fr] lg:gap-8">
        {/* ---------------------------------------------------------- left column */}
        <div>
          <Step n={1} title="The event is released into the world" node="D">
            <div
              className="rounded-lg border px-4 py-3"
              style={{
                borderColor: forged
                  ? "color-mix(in srgb, var(--color-fail) 40%, transparent)"
                  : "var(--color-line)",
                background: forged ? "color-mix(in srgb, var(--color-fail) 7%, transparent)" : undefined,
              }}
            >
              <div className="flex flex-wrap items-center gap-2">
                <Pill accent="var(--color-brand)">{tPlus(ev.t)}</Pill>
                <Pill>{istClock(ev.t)}</Pill>
                {ev.area && <Pill accent="var(--color-us)">{ev.area}</Pill>}
                <Pill accent={forged ? "var(--color-fail)" : "var(--color-pass)"}>
                  {forged ? "authentic = false" : "authentic = true"}
                </Pill>
                {ev.synthetic && <Pill accent="var(--color-block)">synthetic injection</Pill>}
              </div>
              {ev.claimed_issuer && (
                <p className="mt-2.5 text-[12.5px] text-muted">
                  Claims to come from{" "}
                  <span className="text-ink">{ev.claimed_issuer}</span>.
                </p>
              )}
              <pre className="mt-2.5 max-h-44 overflow-auto rounded-md border border-line bg-ground/70 px-3 py-2 font-mono text-[10.5px] leading-relaxed whitespace-pre-wrap text-muted">
                {JSON.stringify(
                  Object.fromEntries(Object.entries(ev.payload).filter(([k]) => k !== "truth")),
                  null,
                  1,
                )}
              </pre>
              {trace.hidden_from_agents.length > 0 && (
                <p className="mt-2.5 text-[12px] leading-relaxed text-block">
                  The world also holds{" "}
                  <span className="font-mono">
                    truth.{trace.hidden_from_agents.join(", truth.")}
                  </span>{" "}
                  — ground truth no agent can read. {forged
                    ? "Nothing in the delivered payload says this order is forged."
                    : "It is what the properties are checked against afterwards."}
                </p>
              )}
            </div>
          </Step>

          <Step n={2} title="It reaches each role at a different time" node="D">
            <div className="grid gap-1.5">
              {trace.deliveries.map((d) => (
                <div
                  key={`${d.role}-${d.seq}`}
                  className="flex items-center gap-2.5 rounded-md border border-line bg-panel-2/50 px-3 py-2"
                >
                  <Dot accent={ROLE_ACCENT[d.role] ?? "var(--color-muted)"} />
                  <span className="text-[12.5px] text-ink">{ROLE_SHORT[d.role] ?? d.role}</span>
                  <span className="ml-auto font-mono text-[11px] text-muted">{tPlus(d.arrives_t)}</span>
                  <span
                    className="w-[76px] text-right font-mono text-[10.5px]"
                    style={{ color: d.latency_min ? "var(--color-block)" : "var(--color-faint)" }}
                  >
                    {d.latency_min ? `+${d.latency_min} min` : "no delay"}
                  </span>
                </div>
              ))}
            </div>
            {Object.keys(ev.delay_by_role).length > 0 && (
              <p className="mt-2 text-[12px] leading-relaxed text-muted">
                The scenario deliberately delays{" "}
                {Object.entries(ev.delay_by_role)
                  .map(([r, m]) => `${ROLE_SHORT[r] ?? r} by ${m} min`)
                  .join(" and ")}
                . Roles not listed above never see this event at all — that asymmetry is the thing
                being studied, not a defect.
              </p>
            )}
          </Step>

          <Step n={3} title="An agent proposes, and names the rule it believes allows it" node="M">
            {trace.proposals.length > 1 && (
              <div className="mb-2.5 flex flex-wrap gap-1.5">
                {trace.proposals.map((x, i) => (
                  <button
                    key={x.proposal_id}
                    onClick={() => setP(i)}
                    className={`rounded border px-2 py-0.5 font-mono text-[10px] transition-colors ${
                      i === Math.min(p, trace.proposals.length - 1)
                        ? "border-line-bright bg-panel-2 text-ink"
                        : "border-line text-faint hover:text-muted"
                    }`}
                  >
                    {tPlus(x.t)} {x.action}
                  </button>
                ))}
              </div>
            )}
            {proposal && (
              <div className="rounded-lg border border-line bg-panel-2/50 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Dot accent={ROLE_ACCENT[proposal.role] ?? "var(--color-muted)"} />
                  <span className="text-[13px] font-semibold text-ink">
                    {ROLE_SHORT[proposal.role] ?? proposal.role}
                  </span>
                  <Pill accent="var(--color-brand)">{proposal.action}</Pill>
                  <Pill>{tPlus(proposal.t)}</Pill>
                </div>
                <p className="mt-2.5 text-[12.5px] leading-relaxed text-muted italic">
                  &ldquo;{proposal.reasoning}&rdquo;
                </p>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {proposal.cited_rule_ids.map((r) => (
                    <Pill key={r} accent="var(--color-india)">
                      {r}
                    </Pill>
                  ))}
                </div>
                <div className="mt-2.5 grid gap-1.5">
                  {proposal.cited_clause_ids.map((cid) => (
                    <ClauseText key={cid} id={cid} clause={clauses[cid]} />
                  ))}
                </div>
              </div>
            )}
          </Step>
        </div>

        {/* --------------------------------------------------------- right column */}
        <div>
          <Step n={4} title="Deterministic code decides. No model is in this path." node="P">
            {verdict ? (
              <div
                className="rounded-lg border px-4 py-3"
                style={{
                  borderColor: `color-mix(in srgb, ${DECISION_ACCENT[verdict.decision]} 40%, transparent)`,
                  background: `color-mix(in srgb, ${DECISION_ACCENT[verdict.decision]} 8%, transparent)`,
                }}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className="font-mono text-[14px] font-bold tracking-[0.14em]"
                    style={{ color: DECISION_ACCENT[verdict.decision] }}
                  >
                    {verdict.decision}
                  </span>
                  <Pill>mode {verdict.mode}</Pill>
                  <Pill>seq {verdict.seq}</Pill>
                </div>
                <p className="mt-2 font-mono text-[11.5px] text-muted">{verdict.explanation}</p>
                <p className="mt-2.5 text-[12.5px] leading-relaxed text-muted">
                  {verdict.decision === "ALLOW" && forged
                    ? "The rulebook permits this action and imposes no duty to authenticate the order it rests on. The engine is behaving exactly as the encoded law says — which is the finding."
                    : verdict.decision === "ALLOW"
                      ? "A rule in force permits this action and its preconditions were met on the world as it stood at this tick."
                      : "The action was refused before it could touch the world, and the refusal is in the chain."}
                </p>
              </div>
            ) : (
              <p className="text-[12.5px] text-faint">no verdict recorded for this proposal</p>
            )}
          </Step>

          <Step n={5} title="The Game Master applies the effect" node="D">
            {effect ? (
              <div className="rounded-lg border border-line bg-panel-2/50 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Pill accent="var(--color-allow)">{effect.action}</Pill>
                  {effect.area && <Pill accent="var(--color-us)">{effect.area}</Pill>}
                  <Pill>{tPlus(effect.t)}</Pill>
                </div>
                <pre className="mt-2.5 max-h-40 overflow-auto rounded-md border border-line bg-ground/70 px-3 py-2 font-mono text-[10.5px] leading-relaxed whitespace-pre-wrap text-muted">
                  {JSON.stringify(effect.detail, null, 1)}
                </pre>
              </div>
            ) : (
              <p className="text-[12.5px] text-faint">
                nothing executed — the proposal did not reach the world
              </p>
            )}
          </Step>

          <Step n={6} title="And this is the number it moves" node="SINK">
            {trace.moves.length === 0 ? (
              <p className="text-[12.5px] text-faint">
                No property check turns on anything this event produced.
              </p>
            ) : (
              <div className="grid gap-2">
                {trace.moves.map((m) => (
                  <div
                    key={m.property_id}
                    className="rounded-lg border px-4 py-3"
                    style={{
                      borderColor: `color-mix(in srgb, ${m.passed ? "var(--color-pass)" : "var(--color-fail)"} 38%, transparent)`,
                      background: `color-mix(in srgb, ${m.passed ? "var(--color-pass)" : "var(--color-fail)"} 7%, transparent)`,
                    }}
                  >
                    <div className="flex items-baseline gap-2.5">
                      <span className="font-mono text-[13px] font-semibold text-brand">
                        {m.property_id}
                      </span>
                      <span
                        className="font-mono text-[11px] font-bold tracking-[0.14em]"
                        style={{ color: m.passed ? "var(--color-pass)" : "var(--color-fail)" }}
                      >
                        {m.passed ? "HOLDS" : "VIOLATED"}
                      </span>
                      <span className="ml-auto font-mono text-[15px] tabular-nums text-ink">
                        {signed(m.margin)}
                      </span>
                    </div>
                    {m.via.map((v) => (
                      <p key={v.kind} className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
                        {v.kind === "id"
                          ? "The check's own working names "
                          : "The check turns on a moment this event created: "}
                        <span className="font-mono text-faint">{v.what.join(", ")}</span>
                        {v.kind === "id" ? "." : "."}
                      </p>
                    ))}
                  </div>
                ))}
              </div>
            )}
            <p className="mt-3 text-[12px] leading-relaxed text-faint">
              Every step above is an entry in the hash chain, in sequence. Re-run with the same
              seed and the same entries appear with the same hashes.
            </p>
          </Step>
        </div>
      </div>
    </Panel>
  );
}
