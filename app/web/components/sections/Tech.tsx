import { Panel, Pill } from "@/components/ui";

type Dep = { name: string; version: string; role: string };
type Layer = {
  id: string;
  title: string;
  accent: string;
  node: string;
  blurb: string;
  deps: Dep[];
};

/**
 * The stack, taken from the files that actually pin it: pyproject.toml,
 * requirements.txt, app/web/package.json and vercel.json. Versions here are the
 * declared floors, not whatever happens to be resolved in a given venv.
 */
const LAYERS: Layer[] = [
  {
    id: "core",
    title: "Deterministic core",
    accent: "#2dd4a7",
    node: "C · PP · P · D",
    blurb:
      "The part that decides anything. No model, no network, no randomness beyond a seed you pass in — which is what lets the same scenario be replayed byte-for-byte under three rulebooks.",
    deps: [
      { name: "Python", version: "≥3.11", role: "runtime" },
      { name: "pydantic", version: "≥2.6", role: "every event, verdict and clause is a typed schema" },
      { name: "pyyaml", version: "≥6.0", role: "scenarios and policy packs are YAML, diffable in review" },
      { name: "rank-bm25", version: "≥0.2.2", role: "lexical retrieval over the clause store" },
    ],
  },
  {
    id: "proof",
    title: "Fuzzing and proof",
    accent: "#f0b429",
    node: "P",
    blurb:
      "Four properties asserted after every mutated run. When one breaks, the mutation sequence is shrunk to the smallest one that still breaks it, so the output is a minimal counterexample rather than an anecdote.",
    deps: [
      { name: "hypothesis", version: "≥6.100", role: "stateful property-based fuzzing + shrinking" },
      { name: "pytest", version: "≥8.0", role: "the P0–P13 gate suite" },
      { name: "hashlib / SHA-256", version: "stdlib", role: "hash-chained ledger; an edit names its own seq" },
    ],
  },
  {
    id: "agents",
    title: "Agents and language",
    accent: "#c084fc",
    node: "M",
    blurb:
      "Optional by design. Agents propose; the rule engine disposes. Pull the LLM out and the pipeline still runs end to end — the deterministic agents take over and the verdicts are identical.",
    deps: [
      { name: "litellm", version: "≥1.40", role: "one interface over Claude / OpenAI / local models" },
      { name: "chromadb", version: "≥0.5", role: "vector index over the ITU reference corpus" },
      { name: "rule agents", version: "in-tree", role: "the no-LLM fallback the tests run against" },
    ],
  },
  {
    id: "service",
    title: "Service tier",
    accent: "#4aa8ff",
    node: "SINK",
    blurb:
      "A read-only HTTP surface over the artefacts, plus the endpoint behind the Run button. It serves artefacts and re-walks a hash chain — a test asserts it cannot import the simulator.",
    deps: [
      { name: "fastapi", version: "≥0.115", role: "the API in api/index.py" },
      { name: "uvicorn", version: "≥0.30", role: "local server for make dev" },
    ],
  },
  {
    id: "web",
    title: "This page",
    accent: "var(--color-brand)",
    node: "SINK",
    blurb:
      "A static export built from one bundle.json that the Python side writes. Nothing on this page is typed in by hand — if a number here is wrong, the export that produced it is wrong.",
    deps: [
      { name: "Next.js", version: "16.4", role: "App Router, static export" },
      { name: "React", version: "19.3", role: "" },
      { name: "TypeScript", version: "5.x", role: "the bundle is typed in lib/types.ts" },
      { name: "Tailwind CSS", version: "4.x", role: "" },
    ],
  },
  {
    id: "delivery",
    title: "Build and delivery",
    accent: "#fb7185",
    node: "—",
    blurb:
      "Two services behind one domain: the static site, and the FastAPI function the Run button calls. The bundle is regenerated on push, so the deployed page can never drift from the committed run.",
    deps: [
      { name: "Vercel", version: "web + api", role: "rewrites /api/* to the function, everything else to the site" },
      { name: "GitHub Actions", version: "on push", role: "regenerates the bundle and runs the gate suite" },
      { name: "ruff", version: "lint", role: "" },
      { name: "hatchling", version: "build", role: "" },
    ],
  },
];

export function Tech() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {LAYERS.map((l) => (
        <Panel key={l.id} className="flex flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-[14px] font-semibold text-ink">{l.title}</h3>
            <Pill accent={l.accent}>{l.node}</Pill>
          </div>
          <p className="mt-2.5 text-[12.5px] leading-relaxed text-muted">{l.blurb}</p>

          <dl className="mt-4 grid gap-2 border-t border-line pt-3.5">
            {l.deps.map((d) => (
              <div key={d.name}>
                <dt className="flex items-baseline gap-2">
                  <span
                    className="font-mono text-[12px] font-semibold"
                    style={{ color: l.accent }}
                  >
                    {d.name}
                  </span>
                  <span className="font-mono text-[10.5px] text-faint">{d.version}</span>
                </dt>
                {d.role && (
                  <dd className="mt-0.5 text-[11.5px] leading-snug text-faint">{d.role}</dd>
                )}
              </div>
            ))}
          </dl>
        </Panel>
      ))}
    </div>
  );
}
