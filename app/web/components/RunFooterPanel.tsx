import { Panel, Pill } from "@/components/ui";
import { tPlus } from "@/lib/format";
import type { RunFooter } from "@/lib/types";

/**
 * The run's own closing accounting. It is the part to read first, because it is where
 * the system reports against itself — including the fact that the human gate auto-released.
 */
export function RunFooterPanel({ footer }: { footer: RunFooter }) {
  const gate = footer.human_gate;
  const auto = (gate?.decisions ?? []).filter((d) => d.approver === "auto_batch");
  const forged = footer.forged_executions ?? 0;

  return (
    <Panel className="p-5">
      <h2 className="text-[14px] font-semibold text-ink">What this run reported about itself</h2>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div>
          <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
            Why proposals were refused
          </div>
          <div className="mt-2 grid gap-1.5">
            {Object.entries(footer.blocks_by_reason ?? {}).map(([k, n]) => (
              <div key={k} className="flex items-baseline gap-2 text-[12px]">
                <span className="font-mono text-ink tabular-nums">{n}</span>
                <span className="text-muted">{k.replace(/_/g, " ")}</span>
              </div>
            ))}
            {Object.keys(footer.blocks_by_reason ?? {}).length === 0 && (
              <span className="text-[12px] text-faint">nothing was refused</span>
            )}
          </div>
          <p className="mt-2 text-[11.5px] leading-relaxed text-faint">
            <span className="text-muted">preconditions unmet</span> is an agent acting early or on
            the wrong area; <span className="text-muted">prohibited by rule</span> is the rulebook
            refusing a power outright.
          </p>
        </div>

        <div>
          <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
            Human-in-the-loop · Y.3173
          </div>
          {gate ? (
            <>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Pill>mode {gate.mode}</Pill>
                <Pill accent={auto.length ? "var(--color-block)" : "var(--color-pass)"}>
                  {gate.decisions.length} held
                </Pill>
                {gate.still_pending.length > 0 && (
                  <Pill accent="var(--color-human)">{gate.still_pending.length} never released</Pill>
                )}
              </div>
              {auto.length > 0 && (
                <p className="mt-2.5 text-[12px] leading-relaxed text-block">
                  {auto.length} irreversible action
                  {auto.length === 1 ? " was" : "s were"} released by the batch timer, not by a
                  person. The report says <span className="font-mono">auto_batch</span> rather than
                  claiming a human reviewed it.
                </p>
              )}
              <div className="mt-2 grid gap-1">
                {gate.decisions.map((d) => (
                  <div key={d.proposal_id} className="font-mono text-[10.5px] text-faint">
                    {tPlus(d.at)} · {d.approver} · {d.proposal_id}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="mt-2 text-[12px] text-faint">no gate activity in this run</p>
          )}
        </div>

        <div>
          <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
            Adversarial outcome
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Pill accent={forged > 0 ? "var(--color-fail)" : "var(--color-pass)"}>
              {forged} forged order{forged === 1 ? "" : "s"} executed
            </Pill>
            <Pill
              accent={
                (footer.undelivered_at_horizon ?? 0) > 0 ? "var(--color-block)" : "var(--color-pass)"
              }
            >
              {footer.undelivered_at_horizon ?? 0} undelivered at horizon
            </Pill>
          </div>
          <p className="mt-2.5 text-[12px] leading-relaxed text-muted">
            {forged > 0
              ? "An unauthenticated direction was acted on as if genuine. That is property P2, and it is the finding the forged-order injection exists to produce."
              : "No unauthenticated direction caused an irreversible action under this rulebook."}
          </p>
        </div>
      </div>
    </Panel>
  );
}
