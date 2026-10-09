# CHAKRAVYUH — submission

**Entry:** CHAKRAVYUH — policy fuzzing for emergency telecommunications governance
**Team:** Quantum QAI · Ranny Nayyar
**Event:** ITU AI for Good Sandbox Build-a-thon 5.0, New Delhi, 10 October 2026
**Licence:** Apache-2.0

> We stress-test disaster-telecom policy before the cyclone does. One real cyclone timeline,
> replayed under three encoded legal regimes. Where an obligation fails to fire in time, the
> system names the clause responsible.

**Run everything, offline, in one command:**

```bash
pip install -e ".[test,ui,kb]"
bash scripts/replay_demo.sh          # no network required
```

---

## 1. Rubric → evidence

| Criterion | Evidence a judge can open | Command to reproduce |
|---|---|---|
| **1. Knowledge base quality** | [`data/sources/MANIFEST.yaml`](data/sources/MANIFEST.yaml) · [`docs/kb_report.md`](docs/kb_report.md) · [`docs/retrieval_eval.md`](docs/retrieval_eval.md) | `python scripts/build_kb.py && pytest tests/test_p1_clause_store.py` |
| **2. Agent capability in error scenarios** | [`docs/architecture.md`](docs/architecture.md) · [`runs/`](runs/) · [`docs/adviser_eval.md`](docs/adviser_eval.md) | `bash scripts/replay_demo.sh` |
| **3. Gap identification** (global + neighbour examples) | [`docs/gap_register.md`](docs/gap_register.md) — 11 gaps, each with an Indian clause, a neighbour and a global example | `python scripts/run_demo.py --seed 0` |
| **4. Auditability** | [`outputs/audit_sample.jsonl`](outputs/audit_sample.jsonl) · the **Why?** tab in the UI | `python scripts/verify_ledger.py --all` then `--tamper-demo <ledger>` |
| **5. ITU standards alignment** | [`docs/y3172_map.md`](docs/y3172_map.md) · [`docs/ai_readiness_map.md`](docs/ai_readiness_map.md) | `python scripts/gen_y3172_map.py && python scripts/gen_ai_readiness_map.py` |

**Self-audit:** [`docs/rubric_status.html`](docs/rubric_status.html) — 18 checks measured on every
run, not asserted by hand. Currently **16 PASS · 2 WAIVED with printed reasons · 0 FAIL**.
A waived check is one whose condition does not hold and which we decided should not, for a
reason that lives in the check's own code. `python scripts/rubric_audit.py --strict` fails on a
waiver too.

## 2. Mandatory brief items

- [x] **Queryable policy/legal adviser that cannot act** — [`chakravyuh/agents/adviser.py`](chakravyuh/agents/adviser.py). Holds zero powers, proposes nothing. Scored 23/23 on never citing a clause outside the retrieved set.
- [x] **Institutional actor agents + multi-agent coordination** — six roles in [`chakravyuh/agents/roles.py`](chakravyuh/agents/roles.py), resolved against one world state by the Game Master.
- [x] **Events released progressively, chunked, uneven per agent** — [`chakravyuh/sim/bus.py`](chakravyuh/sim/bus.py) + per-event `delay_by_role`. Nine events reach two or more roles at different times; the cross-border channel runs 75 minutes behind.
- [x] **Audit logging + reasoning traces** — hash-chained ledger, 928 entries in the India run. Every proposal carries `reasoning`, `cited_rule_ids` and `cited_clause_ids`.
- [x] **ITU reference documents ingested into a vector KB** — ChromaDB `kb_main`, 257 chunks, each carrying `clause_id`, `instrument`, `jurisdiction`, `page`, `sha256`, `verbatim_status`.
- [x] **AI Readiness perspectives mapped** — all 13 dimensions accounted for, labels read from ITU's own `dimensions.json`.

## 3. What we found

| | Finding | Evidence |
|---|---|---|
| **G1 / P4** | **No standing disaster-roaming trigger.** Under 47 CFR 4.17 roaming is a standing obligation on a provider whose network is impaired — passes at **+345 min**. Under the Indian and Bangladeshi packs it must be requested — both fail at **−855 min**. Same storm, same seed; only the legal construction differs. | `docs/gap_register.md` G1 |
| **G3 / P2** | **Orders are not verifiably authenticated.** The Suspension Rules 2024 r.4(2) require a suspension order to reach the nodal officer *"in writing or through a secure electronic communication, by an officer not below the rank of Superintendent of Police"* — but prescribe **no mechanism the operator can check**. "Secure" is undefined; `authenticat*` returns 0 hits in the instrument. A forged order executes exactly like a genuine one. | `docs/gap_register.md` G3 |
| **Bangladesh / P4** | A **coordination** gap, not a policy one: sites went down in Balasore and only the operator knew; under both packs only the authority can trigger roaming, and nothing told it. | `docs/gap_register.md` |

## 4. Reproducibility

| | |
|---|---|
| Determinism | Same seed ⇒ same ledger head hash. 11/11 ledgers verify. |
| Offline | The entire demo path needs no network and **no API key**. |
| LLM calls in every result shown | **0.** The deterministic tier costs 0 tokens; the policy engine provably cannot import a model. |
| Models, when enabled | `ollama/qwen2.5:14b` (agents, adviser) · `nomic-embed-text` or Chroma's `all-MiniLM-L6-v2` (embeddings) |
| Tests | 140 passing · `ruff` clean |
| Dependencies | pinned in [`requirements.lock`](requirements.lock) |

## 5. Limits — read these

Stated in full in [`docs/limits.md`](docs/limits.md). The short version:

- The **IMD timeline and the legal text are real; the per-cell network is simulated**, calibrated to reported aggregates (COAI, BTRC). Eight of fifteen scenario events are our construction, flagged `synthetic: true` and greyed in the UI.
- **110 of 157 clause records carry the instrument's own words**; 47 are labelled summaries. Which ones, and what each blocks, is in `docs/limits.md`.
- Property margins are **illustrative units** — cells, minutes, percentages. No money, no casualties, **no confidence intervals**, no accuracy claims.
- **Three findings rest on an instrument being silent, and P2 is one of them.** The gap register's `confidence` column is computed from clause provenance and currently reads `likely` on all 11 rows for exactly this reason.

## 6. Deliberate deviations from the repo standard

Two, both argued rather than overlooked:

1. **The package stays at `chakravyuh/`, not `src/chakravyuh/nodes/…` named after Y.3172 nodes.** Node membership is declared by an `@node("P")` decorator on every entry point and [`docs/y3172_map.md`](docs/y3172_map.md) is generated from that registry — which is stronger evidence than a directory name, because it cannot drift from the code and is checked by a test. Restructuring a working, 140-test system the night before the event would have risked the demo to gain a cosmetic signal.
2. **Clause data lives under `data/`, not `kb/`.** Same contents, same manifest, same schema — `data/sources/MANIFEST.yaml`, `data/clauses/*.jsonl`. Renaming it would have broken every generated artefact path for no judge-visible gain.

## 7. Known gaps in the submission itself

- `docs/report.pdf`, `docs/slides.pdf` and the demo video are **not in the repo yet**.
- Three primary sources are still missing and each blocks a finding from reaching `certain`: the **complete** Telecom Cyber Security Rules 2024, the **Telecom Cyber Security Amendment Rules 2025** (G.S.R. 771(E), 22 Oct 2025), and **DoT SOP-2020**. Tracked with status and blocking reason in [`data/sources/MANIFEST.yaml`](data/sources/MANIFEST.yaml).

## Acknowledgements

Extends the ITU AI Readiness reference implementation (MIT) and the ITU Sandbox training
dataset. Aligned with ITU-T Y.3172, Y.3173, Y.3181, X.1303, E.106 and Q.3057/Q.3062/Q.3063.
Not certified, approved or endorsed by the ITU. See [`NOTICE`](NOTICE).
