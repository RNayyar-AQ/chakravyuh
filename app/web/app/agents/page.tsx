import { Chakra } from "@/components/Chakra";
import { Dot, Panel, Pill, Provenance } from "@/components/ui";
import { getBundle } from "@/lib/data";
import { ROLE_ACCENT } from "@/lib/format";

export const metadata = { title: "Agents — CHAKRAVYUH" };

export default function AgentsPage() {
  const b = getBundle();

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-10 grid items-start gap-8 lg:grid-cols-[1.4fr_auto]">
        <div className="max-w-3xl">
          <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
            Y.3172 node M · six roles
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Each agent is defined as much by what it cannot see
          </h1>
          <p className="mt-4 text-[14px] leading-relaxed text-muted">
            A role carries a mandate, an inbox filter, a channel latency and an explicit statement
            of its blind spots. Powers come from the rulebook, never from the agent — which is why
            the same six agents behave differently under three legal regimes without a line of
            agent code changing.
          </p>
          <p className="mt-4 text-[13.5px] leading-relaxed text-muted">
            Every tier — deterministic rule twins, an LLM, an external agent — implements one
            protocol and returns the same typed proposal. The Game Master cannot tell them apart,
            so a comparison between tiers is like for like.
          </p>
          <Provenance>app/chakravyuh/agents/roles.py · app/chakravyuh/agents/base.py</Provenance>
        </div>
        <div className="hidden lg:block">
          <Chakra size={150} />
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        {b.roles.map((r) => {
          const accent = ROLE_ACCENT[r.role_id] ?? "var(--color-muted)";
          return (
            <Panel key={r.role_id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <span className="mt-1.5">
                    <Dot accent={accent} />
                  </span>
                  <div>
                    <h2 className="text-[15px] leading-snug font-semibold text-ink">{r.name}</h2>
                    <div className="mt-1 font-mono text-[10.5px] text-faint">{r.role_id}</div>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1.5">
                  <Pill accent={accent}>priority {r.priority}</Pill>
                  {r.channel_latency_min > 0 && (
                    <Pill accent="var(--color-fail)">+{r.channel_latency_min} min channel</Pill>
                  )}
                </div>
              </div>

              <p className="mt-3.5 text-[11.5px] leading-relaxed text-faint italic">{r.analogue}</p>

              <div className="mt-4">
                <div className="font-mono text-[10px] tracking-wider text-faint uppercase">
                  Mandate
                </div>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{r.mandate}</p>
              </div>

              <div className="mt-4">
                <div className="font-mono text-[10px] tracking-wider uppercase" style={{ color: "var(--color-fail)" }}>
                  Blind spots
                </div>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{r.boundaries}</p>
              </div>

              <div className="mt-auto pt-4">
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

      <Panel className="mt-6 p-6">
        <h2 className="text-[15px] font-semibold tracking-tight">Why the Game Master is not a model</h2>
        <p className="mt-3 max-w-4xl text-[13px] leading-relaxed text-muted">
          Resolution order inside a tick is fully determined by{" "}
          <code className="font-mono text-ink">(t, role priority, proposal_id)</code>. One world
          state, one rulebook, one order. That is what removes the conflicting-implicit-decisions
          failure mode from multi-agent systems while still letting agents hold genuinely partial
          and uneven information — which is the thing being studied here.
        </p>
        <Provenance>app/chakravyuh/sim/game_master.py — Y.3172 node D</Provenance>
      </Panel>
    </div>
  );
}
