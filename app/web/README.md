# CHAKRAVYUH — web UI

A Next.js 16 static site that renders what the Python pipeline already decided. It holds no logic
of its own: no scoring, no re-derivation, no model. Every number on screen was read from an
artefact in `runs/` or `outputs/`, so the UI cannot drift from the simulator.

## Build

Artefacts first, page second — there is nothing to render otherwise.

```bash
# from the repository root
python app/scripts/showcase.py --fast    # ~35 s offline: runs, fuzz, evals, ledgers
python app/scripts/export_web.py         # writes app/web/public/data/

cd app/web
npm install
npm run dev                          # http://localhost:3000
npm run build                        # static export into app/web/out/
```

`npm run build` emits a plain folder. Serve it with anything:

```bash
npx serve out            # or: python3 -m http.server -d out 8080
```

## Layout

Two routes. The demo is one page you scroll, because a judge with seven minutes should never have
to find a tab.

| Path | What it is |
|---|---|
| `app/page.tsx` | The whole argument: the pipeline, the knowledge base, retrieval, the agents, one event followed to the number it moves, the arithmetic behind every margin, the ledger replay, the failures, the gaps, the evidence, the standards, the limits |
| `app/rubric/page.tsx` | Every rubric check with its measured detail and, where waived, the reason |
| `components/sections/` | One component per band of the page |
| `components/TimelineExplorer.tsx` | Ledger replay with per-regime switching, filters, expandable verdicts |
| `components/GapExplorer.tsx` | The gap register, with computed confidence and replay commands |
| `lib/types.ts` | The shapes `app/scripts/export_web.py` writes — the only contract between the two halves |

## Rules

- **The UI computes nothing.** If a number needs deriving, derive it in Python and export it.
  One source of truth, and it is the one with the tests.
- **`app/web/public/data/` is a build product.** It is committed, and only because Vercel builds
  from git with no Python available; a test regenerates it and fails on any drift. Regenerate it
  with `make artefacts`; never hand-edit it.
- **No runtime data fetching from anywhere but `/data`.** The site must work offline, on a
  conference Wi-Fi, from a folder.
