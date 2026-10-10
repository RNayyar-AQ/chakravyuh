import { Dot, Panel, PanelHead, Pill } from "@/components/ui";
import { ROLE_ACCENT } from "@/lib/format";
import type { Role } from "@/lib/types";

/** The six roles, each defined as much by what it cannot see. */
export function Agents({ roles }: { roles: Role[] }) {
  return (
    <div className="grid gap-4">
      <Panel className="overflow-hidden">
        <PanelHead
          kicker="Y.3172 node M"
          title="Six role-bound agents, one protocol, three interchangeable tiers"
          right={<Pill accent="var(--color-human)">{roles.length} roles</Pill>}
        />
        <div className="grid gap-4 p-5 lg:grid-cols-3">
          {[
            {
              t: "Rule twins",
              d: "Deterministic Python. No credential, no network, no variance. This is the tier the demo runs, and it is why the site can be rebuilt offline.",
              a: "var(--color-pass)",
            },
            {
              t: "LLM tier",
              d: "One call per tick at temperature 0 through a record/replay cache. In replay a cache miss raises rather than reaching the network, so a run cannot quietly become non-reproducible.",
              a: "var(--color-human)",
            },
            {
              t: "External tier",
              d: "Anything that satisfies the Agent protocol. The Game Master cannot tell the tiers apart, which is what makes a comparison between them like for like.",
              a: "var(--color-us)",
            },
          ].map((x) => (
            <div key={x.t} className="rounded-lg border border-line bg-panel-2/50 p-4">
              <div className="flex items-center gap-2">
                <Dot accent={x.a} />
                <span className="text-[13px] font-semibold text-ink">{x.t}</span>
              </div>
              <p className="mt-2 text-[12px] leading-relaxed text-muted">{x.d}</p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        {roles.map((r) => {
          const accent = ROLE_ACCENT[r.role_id] ?? "var(--color-muted)";
          return (
            <Panel key={r.role_id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <span className="mt-1.5">
                    <Dot accent={accent} />
                  </span>
                  <div>
                    <h3 className="text-[14.5px] leading-snug font-semibold text-ink">{r.name}</h3>
                    <div className="mt-1 font-mono text-[10.5px] text-faint">{r.role_id}</div>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <Pill accent={accent}>priority {r.priority}</Pill>
                  {r.channel_latency_min > 0 && (
                    <Pill accent="var(--color-block)">+{r.channel_latency_min} min channel</Pill>
                  )}
                </div>
              </div>

              <p className="mt-3 text-[11.5px] leading-relaxed text-faint italic">{r.analogue}</p>

              <div className="mt-3.5">
                <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
                  Mandate
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{r.mandate}</p>
              </div>

              <div className="mt-3.5">
                <div
                  className="font-mono text-[10px] tracking-wider uppercase"
                  style={{ color: "var(--color-fail)" }}
                >
                  Blind spots
                </div>
                <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{r.boundaries}</p>
              </div>

              <div className="mt-auto pt-3.5">
                <div className="mb-1.5 font-mono text-[10px] tracking-wider text-faint uppercase">
                  Can ever receive
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {r.inbox_types.map((t) => (
                    <Pill key={t}>{t === "*" ? "every event type" : t}</Pill>
                  ))}
                </div>
              </div>
            </Panel>
          );
        })}
      </div>

      <Panel className="p-5">
        <h3 className="text-[14px] font-semibold tracking-tight">Why the Game Master is not a model</h3>
        <p className="mt-2.5 max-w-4xl text-[13px] leading-relaxed text-muted">
          Resolution order inside a tick is fully determined by{" "}
          <code className="font-mono text-ink">(t, role priority, proposal_id)</code>. One world
          state, one rulebook, one order. That removes the conflicting-implicit-decisions failure
          mode from multi-agent systems while still letting agents hold genuinely partial and
          uneven information — which is the thing being studied. It is also the reason a framework
          scheduler sits nowhere between a proposal and a verdict: that is precisely where
          determinism would be lost.
        </p>
      </Panel>
    </div>
  );
}
