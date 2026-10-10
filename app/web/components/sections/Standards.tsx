import { Panel, PanelHead, Pill } from "@/components/ui";
import type { Y3172Node } from "@/lib/types";

const NODE_ACCENT: Record<string, string> = {
  SRC: "#4aa8ff",
  C: "#38bdf8",
  PP: "#2dd4a7",
  M: "#c084fc",
  P: "#f0b429",
  D: "var(--color-brand)",
  SINK: "#fb7185",
};

const INSTRUMENTS = [
  {
    id: "ITU-T Y.3172",
    title: "Architectural framework for machine learning in future networks",
    use: "Every pipeline entry point is tagged with its ML node by an @node() decorator, and the map is generated from that registry rather than written by hand.",
  },
  {
    id: "ITU-T Y.3173",
    title: "Framework for evaluating intelligence levels of future networks",
    use: "Irreversible actions never execute on an agent's say-so. They return NEEDS_HUMAN and are held at a gate, and the run reports when a gate auto-released rather than claiming review.",
  },
  {
    id: "ITU-T Y.3181",
    title: "Architectural framework for an ML sandbox",
    use: "The simulator is the sandbox: models propose into a world that cannot touch production, and the policy engine has no model in its import graph.",
  },
  {
    id: "ITU-T X.1303 / OASIS CAP 1.2",
    title: "Common Alerting Protocol",
    use: "Public alerts are emitted as real CAP 1.2 envelopes with RFC-3066 language tags, region-aware across borders, shape-checked on every emission.",
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

/** Conformance claimed in code, counted by walking the package. */
export function Standards({ nodes }: { nodes: Y3172Node[] }) {
  const total = nodes.reduce((n, x) => n + x.count, 0);

  return (
    <div className="grid gap-4">
      <Panel className="overflow-hidden">
        <PanelHead
          kicker="ITU-T Y.3172"
          title="ML pipeline nodes, counted from the decorator registry"
          right={<Pill accent="var(--color-brand)">{total} registrations</Pill>}
        />
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-4">
          {nodes.map((n) => (
            <div key={n.node} className="rounded-lg border border-line bg-panel-2/50 p-4">
              <div className="flex items-baseline justify-between">
                <span
                  className="font-mono text-[15px] font-bold tracking-wider"
                  style={{ color: NODE_ACCENT[n.node] ?? "var(--color-muted)" }}
                >
                  {n.node}
                </span>
                <span className="font-mono text-[18px] tabular-nums text-ink">{n.count}</span>
              </div>
              <p className="mt-2 text-[11.5px] leading-relaxed text-muted">{n.description}</p>
            </div>
          ))}
        </div>
        <div className="border-t border-line px-5 py-4 text-[12.5px] leading-relaxed text-muted">
          Delete a function and this map loses it. The same registry generates{" "}
          <span className="font-mono text-ink">docs/y3172_map.md</span>, so the documentation
          cannot drift from the code.
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
