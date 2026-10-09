# Phase 8 submission checklist

Generated-by-hand status, verified against the repo on the date of the last `showcase.py` run.
The machine-checkable half of this list is `docs/rubric_status.html`; this file covers the rest.

| # | Item | Status | Where |
|---|---|---|---|
| 1 | Repo public (or essential parts public; README says which) | **open — owner's call** | not yet published; nothing in the repo blocks it |
| 2 | `docs/rubric_status.html` all PASS or waived with reasons | **done** — 16 PASS, 2 WAIVED with printed reasons, 0 FAIL | `docs/rubric_status.html` |
| 3 | KB: clause records + Chroma + `kb_report.md` + `retrieval_eval.md` | **done** | `data/clauses/clauses.jsonl`, `data/chroma/`, `docs/kb_report.md`, `docs/retrieval_eval.md` |
| 4 | `gap_register.csv` + `gap_register.md` | **done** — 11 rows, 4 simulation + 7 document, all four gap types | `outputs/gap_register.csv`, `docs/gap_register.md` |
| 5 | `audit_sample.jsonl`, `y3172_map.md`, `ai_readiness_map.md` | **done** — the sample verifies as a chain on its own | `outputs/audit_sample.jsonl`, `docs/y3172_map.md`, `docs/ai_readiness_map.md` |
| 6 | Technical report ≤ 5 pages | **not written** | see the section template below |
| 7 | Demo video ≤ 7 min | **not recorded** | script in `docs/demo_flow.md` |
| 8 | Limits paragraph present | **done** | `out/demo_report.md` opens with it; `README.md` § Limits; `docs/judge_qa.md` |
| 9 | §0 corrections applied everywhere | **done** — checked mechanically on every audit run | `docs/rubric_status.html` check F1 |

Items 1, 6 and 7 are the owner's, not the code's. Everything they depend on exists.

## The technical report's sections

From the UAE sister-hackathon FAQ template, with the file that supplies each section:

| Section | Source |
|---|---|
| Introduction | `README.md` opening + `docs/judge_qa.md` "What did you find that's new?" |
| Use case | `README.md` § What it produces |
| Requirements | `CHAKRAVYUH_IMPLEMENTATION.md` §§1–6 |
| Y.3172 mapping | `docs/y3172_map.md` (generated from `@node`) |
| AI Readiness 2.0 mapping | `docs/ai_readiness_map.md` (labels read from ITU's `dimensions.json`) |
| Requirements mapped to local policies | `data/packs/india_current.yaml` + `docs/kb_report.md` pack-compilation table |
| Evaluation scenario (technical) | `docs/demo_report.md`, `docs/retrieval_eval.md`, `docs/adviser_eval.md`, `docs/run_stats.md` |
| Evaluation scenario (policy) | `docs/demo_report.md` § Where the packs disagree |
| Policy and standards gaps | `docs/gap_register.md` — lead with G1/P4 and G3/P2 |

## What a reviewer should be told without being asked

- The network layer is synthetic, calibrated to reported aggregates (COAI Amphan, BTRC Remal).
  The IMD timeline and the legal text are real.
- 110 of 157 clause records carry the instrument's own words; 47 are labelled summaries.
- Property margins are illustrative units. No harm estimates, no confidence intervals.
- Three findings rest on an instrument being *silent*, and P2 is one of them. The gap register's
  `confidence` column is computed from clause provenance and currently reads `likely` on every
  row for exactly this reason.
