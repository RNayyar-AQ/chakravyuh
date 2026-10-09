import { Panel, PanelHead, Pill, Provenance } from "@/components/ui";
import { getBundle } from "@/lib/data";

export const metadata = { title: "Standards — CHAKRAVYUH" };

const NODE_ACCENT: Record<string, string> = {
  SRC: "#4aa8ff",
  C: "#38bdf8",
  PP: "#2dd4a7",
  M: "#c084fc",
  P: "#f0b429",
  D: "var(--color-brand)",
  SINK: "#fb7185",
};

/** Instruments this system implements against, and where in the repo each one shows up. */
const INSTRUMENTS = [
  {
    id: "ITU-T Y.3172",
    title: "Architectural framework for machine learning in future networks",
    use: "Every pipeline entry point is tagged with its ML node via an @node() decorator, and the map below is generated from that registry rather than written by hand.",
  },
  {
    id: "ITU-T Y.3173",
    title: "Framework for evaluating intelligence levels of future networks",
    use: "Irreversible actions never execute on an agent's say-so. They return NEEDS_HUMAN and are held at a gate, and the report records when a gate auto-released rather than claiming review.",
  },
  {
    id: "ITU-T Y.3181",
    title: "Architectural framework for ML sandbox",
    use: "The whole simulator is a sandbox: models propose into a world that cannot touch production, and the policy engine has no model in its import graph.",
  },
  {
    id: "ITU-T X.1303 / OASIS CAP 1.2",
    title: "Common Alerting Protocol",
    use: "Public alerts are emitted as real CAP 1.2 envelopes with RFC-3066 language tags, region-aware across borders, and shape-checked on every emission.",
  },
  {
    id: "ITU-T E.106",
    title: "International Emergency Preference Scheme",
    use: "Property P1 measures whether relief traffic survives a lawful suspension — the obligation E.106 exists to protect.",
  },
  {
    id: "ITU-T Q.3057 / Q.3062 / Q.3063",
    title: "Signalling and interconnection security",
    use: "Property P2 measures whether an unauthenticated, forged direction can cause an irreversible action.",
  },
];

export default function StandardsPage() {
  const b = getBundle();
  const total = b.y3172.reduce((n, x) => n + x.count, 0);

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
      <header className="mb-8 max-w-3xl">
        <div className="mb-2 font-mono text-[10px] tracking-[0.18em] text-faint uppercase">
          Conformance
        </div>
        <h1 className="text-3xl font-semibold tracking-tight">Standards map</h1>
        <p className="mt-4 text-[14px] leading-relaxed text-muted">
          Claiming conformance in a slide is easy. Here the mapping is generated from the code: a
          decorator registers each entry point against its ITU-T Y.3172 node, and{" "}
          <span className="font-mono text-ink">{total}</span> registrations across{" "}
          {b.y3172.filter((n) => n.count > 0).length} nodes are counted by walking the package at
          build time. Delete a function and this page loses it.
        </p>
        <Provenance>python scripts/gen_y3172_map.py — writes docs/y3172_map.md</Provenance>
      </header>

      <Panel className="mb-6 overflow-hidden">
        <PanelHead kicker="ITU-T Y.3172" title="ML pipeline nodes, counted from the decorator registry" />
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
          {b.y3172.map((n) => (
            <div key={n.node} className="rounded-lg border border-line bg-panel-2/50 p-4">
              <div className="flex items-baseline justify-between">
                <span
                  className="font-mono text-[15px] font-bold tracking-wider"
                  style={{ color: NODE_ACCENT[n.node] ?? "var(--color-muted)" }}
                >
                  {n.node}
                </span>
                <span className="font-mono text-[18px] text-ink tabular-nums">{n.count}</span>
              </div>
              <p className="mt-2 text-[11.5px] leading-relaxed text-muted">{n.description}</p>
            </div>
          ))}
        </div>
      </Panel>

      <Panel className="mb-6 overflow-hidden">
        <PanelHead kicker="Registry detail" title="Which functions sit at which node" />
        <div className="divide-y divide-line">
          {b.y3172
            .filter((n) => n.count > 0)
            .map((n) => (
              <div key={n.node} className="px-5 py-4">
                <div className="mb-2.5 flex items-center gap-2.5">
                  <span
                    className="font-mono text-[12px] font-bold tracking-wider"
                    style={{ color: NODE_ACCENT[n.node] ?? "var(--color-muted)" }}
                  >
                    {n.node}
                  </span>
                  <span className="text-[12px] text-muted">{n.description}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {n.members.map((m) => (
                    <Pill key={m}>{m}</Pill>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </Panel>

      <Panel className="overflow-hidden">
        <PanelHead kicker="Instruments" title="What each standard is actually doing here" />
        <div className="divide-y divide-line">
          {INSTRUMENTS.map((x) => (
            <div key={x.id} className="grid gap-2 px-5 py-4 lg:grid-cols-[250px_1fr] lg:gap-6">
              <div>
                <div className="font-mono text-[12px] font-semibold text-brand">{x.id}</div>
                <div className="mt-1 text-[11.5px] leading-snug text-faint">{x.title}</div>
              </div>
              <p className="text-[12.5px] leading-relaxed text-muted">{x.use}</p>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
