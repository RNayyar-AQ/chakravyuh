# CHAKRAVYUH — web UI

A Next.js 16 static site that renders what the Python pipeline already decided. It holds no logic
of its own: no scoring, no re-derivation, no model. Every number on screen was read from an
artefact in `runs/` or `outputs/`, so the UI cannot drift from the simulator.

## Build

Artefacts first, page second — there is nothing to render otherwise.

```bash
# from the repository root
python scripts/showcase.py --fast    # ~35 s offline: runs, fuzz, evals, ledgers
python scripts/export_web.py         # writes web/public/data/

cd web
npm install
npm run dev                          # http://localhost:3000
npm run build                        # static export into web/out/
```

`npm run build` emits a plain folder. Serve it with anything:

```bash
npx serve out            # or: python3 -m http.server -d out 8080
```

## Layout

| Path | What it is |
|---|---|
| `app/page.tsx` | Overview — the property × regime scorecard, the architecture, the limits |
| `app/simulation/` | Ledger replay with per-regime switching, filters and expandable verdicts |
| `app/agents/` | The six roles: mandate, blind spots, inbox filter, channel latency |
| `app/failures/` | Fuzz campaigns and the minimal counterexamples that survived shrinking |
| `app/gaps/` | The gap register, with computed confidence and replay commands |
| `app/evidence/` | Clause provenance, source manifest, retrieval scores, hash chains |
| `app/standards/` | Y.3172 node map generated from the decorator registry |
| `lib/types.ts` | The shapes `scripts/export_web.py` writes — the only contract between the two halves |

## Rules

- **The UI computes nothing.** If a number needs deriving, derive it in Python and export it.
  One source of truth, and it is the one with the tests.
- **`web/public/data/` is a build product** and is gitignored, like `outputs/` and `data/clauses/`.
  Regenerate it; never hand-edit it.
- **No runtime data fetching from anywhere but `/data`.** The site must work offline, on a
  conference Wi-Fi, from a folder.
