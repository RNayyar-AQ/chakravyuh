# 🌀 CHAKRAVYUH

**Policy fuzzing for emergency telecom governance.** Six institutional agents with different
mandates and different information respond to a cyclone across a border. They only *propose*; a
deterministic Game Master and policy engine decide what is lawful and what happens. Then the same
scenario is replayed under three legal regimes, and the differences are the findings.

Built for the ITU AI for Good Sandbox Build-a-thon 5.0 — *Creating innovative agents in 5G*.

The one-line claim: **the simulator does not opine that a law has a gap. It runs the law and
measures what breaks.**

---

## What it produces

Running the **real Cyclone Amphan timeline** (IMD RSMC bulletins, 16–20 May 2020, real warned
districts) under India's current law, then under two comparators — same facts, same agents, same
seed, only the law changes:

| Property | India (current) | Bangladesh | US (47 CFR 4.17) |
|---|---|---|---|
| **P1** relief traffic survives a suspension | **FAIL** −60 % of cells | PASS +40 | PASS +40 |
| **P2** no irreversible act on a forged order | **FAIL** −1 execution | PASS 0 | PASS 0 |
| **P3** every area alerted in a local language | **FAIL** −7140 min | PASS +345 | PASS +345 |
| **P4** disaster roaming active after landfall | **FAIL** −855 min | **FAIL** −855 min | PASS +345 |

Margin is signed slack in each property's own illustrative unit; negative means violated.
India's four failures classify as **policy** gaps, each citing the clauses responsible. See
`outputs/gap_register.csv`.

**Bangladesh also fails P4, and for a different reason** — a *coordination* gap the real timeline
exposed. Sites went down in Balasore and only the operator knew; under both the Indian and
Bangladeshi packs only the authority can trigger roaming, and nothing told it. Under 47 CFR 4.17
the operator owes roaming on a standing trigger and acts on what it alone knows. That is the MDRI
contrast, measured rather than asserted.

The headline gap, phrased as the brief asks — domain first, country as instance:

> **Emergency telecom: no standing cross-border trigger.** No instrument empowers any actor to
> alert or enable roaming across the border in time; the domestic power is scoped to domestic areas.
> *Instance:* India–Bangladesh (BD-KHULNA). *Comparator:* FCC MDRI (US), which passes the same seed.

Fuzzing then attacks the packs that *pass*, and finds new failures the baseline misses: escalating
damage into a district that was never forecast puts it outside the alerting flow entirely, because
the alert path is driven by forecasts and the damage path is not. Cards reproduce from their saved
replay command with identical margins.

---

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate     # Python 3.11
pip install -e ".[test,ui,kb]"                        # kb = ChromaDB, for the ITU vector index

python scripts/showcase.py            # EVERYTHING, in dependency order (~4 min with fuzzing)
python scripts/showcase.py --fast     # same, without the fuzz campaign (~35 s)

pytest                                # every acceptance gate
```

Then the web UI, which renders what that run produced:

```bash
cd web && npm install
npm run dev                           # http://localhost:3000
npm run build && npx serve out        # static export, no server needed
```

Two interfaces, deliberately different jobs. **`web/` is the submission UI**: a static Next.js
site over the sealed artefacts, so it is identical for every judge and works with the Wi-Fi off.
`streamlit run app/streamlit_app.py` is the *operator* view — it drives a live run and exposes
the human-in-the-loop approval button that a static page cannot.

`showcase.py` ends by printing the rubric scorecard and writing
`docs/rubric_status.html`. Each stage is also a standalone command, so
anything that fails can be re-run on its own:

| # | Command | What it produces |
|---|---|---|
| 1 | `python scripts/build_kb.py` | clause store (157 records), chunks, Chroma `kb_main`, compiled packs → `docs/kb_report.md` |
| 2 | `python scripts/eval_retrieval.py` | BM25 / vector / hybrid / hybrid+rerank / tree, with abstention separability → `docs/retrieval_eval.md` |
| 3 | `python scripts/eval_adviser.py` | Adviser scored against 23 hand-labelled cases → `docs/adviser_eval.md` |
| 4 | `python scripts/run_demo.py --seed 0` | replays Amphan under all three packs → `docs/demo_report.md`, `docs/gap_register.md + outputs/gap_register.csv`, `outputs/comparison.json` |
| 5 | `python scripts/run_fuzz.py` | mutates the scenario until a property breaks, then shrinks it → `docs/failure_atlas.md` |
| 6 | `python scripts/export_audit_sample.py` | first 50 ledger entries, self-verifying → `outputs/audit_sample.jsonl` |
| 7 | `python scripts/gen_y3172_map.py` | Y.3172 node map, generated from the `@node` decorators |
| 8 | `python scripts/gen_ai_readiness_map.py` | AI Readiness 2.0 map, labels read from ITU's `dimensions.json` |
| 9 | `python scripts/gen_run_stats.py` | wall time, LLM calls and tokens per run → `docs/run_stats.md` |
| 10 | `python scripts/check_sources.py` | do the cited URLs still resolve? (needs network) |
| 11 | `python scripts/verify_ledger.py --all` | every run's hash chain |
| 12 | `python scripts/verify_ledger.py --tamper-demo <ledger>` | **flip one character, watch the chain catch it** |
| 13 | `python scripts/rubric_audit.py` | 18 rubric checks → `docs/rubric_status.html` |

Add `--strict` to `rubric_audit.py` or `showcase.py` to make a *waived* check fail too — the
mode to use when you want the state with no allowances made.

**It all runs offline.** The rule-based agent twins need no model, and the Adviser falls back to
extractive mode (quoting retrieved clauses, generating nothing) when no LLM is reachable. ChromaDB
and LiteLLM are optional; retrieval degrades to BM25 and the demo still runs end to end.

### API keys

**None of the above needs an API key.** Not one command, not the UI, not the tests. The rule-based
twins, the policy engine, the clause store, properties, gap classification, fuzzing and the
extractive Adviser are all deterministic code.

Keys matter only for the LLM agent tier and the generative Adviser, and only in `record` or `live`
mode. Two ways in — pick either:

```bash
# A. Local — the ITU Sandbox reference stack. NO API KEY, just Ollama running.
ollama pull qwen2.5:14b && ollama pull nomic-embed-text
CHAKRAVYUH_LLM_MODE=record python scripts/run_demo.py --tier llm

# B. Hosted — one model, for the showcase run only. Needs that provider's key.
export CHAKRAVYUH_HOSTED_MODEL=anthropic/claude-sonnet-5
export ANTHROPIC_API_KEY=sk-ant-...
CHAKRAVYUH_LLM_MODE=record python scripts/run_demo.py --tier llm --hosted

# Then replay forever, offline and identical every time, with no key and no provider:
python scripts/run_demo.py --tier llm
```

| What you want | Variable | Key needed |
|---|---|---|
| Everything in the quickstart | — | **none** |
| Local LLM agents / Adviser | `OLLAMA_BASE_URL`, `CHAKRAVYUH_LOCAL_MODEL` | **none** (Ollama running) |
| ITU Chroma vector KB | `CHROMA_PATH` | **none** |
| Optional reranker | `CHAKRAVYUH_RERANKER` | **none** (local weights) |
| Hosted showcase run | `CHAKRAVYUH_HOSTED_MODEL` + `--hosted` | `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` |
| Adviser eval's LLM judge | `--judge-model <id>` | that provider's key |

Keys are read by LiteLLM, never by this code. The scripts preflight the one variable your chosen
model needs and exit in a second naming it, rather than failing mid-recording. `.env.example`
documents every variable, and a test asserts it stays in sync with what the code actually reads.

---

## The knowledge base: what is real

| Provenance | Records | What the text is |
|---|---|---|
| `gazette_pdf` | 106 | **The instrument's own words**, split section-by-section from the official eGazette PDFs of the Telecommunications Act 2023 (62 sections) and DPDP Act 2023 (44 sections). Counts match the Acts. |
| `gazette_pdf_subsection` | 4 | Genuine substrings for cited subsections: s.20(1), s.20(2), s.7(g), s.7(h) |
| `secondary_source` | 18 | Summary, but the content claim is attributed to a named source (SCC Online, eCFR, ITU) |
| `model_written` | 29 | Summary, nothing checked |

**70.1 % of the corpus is now the instrument's own words**, up from 0 %. Each real record carries
its page, a hash of the text, and `source_pdf_sha256` — the hash of the PDF itself, which pins the
document even if the link rots. Both eGazette URLs verify as HTTP 200 `application/pdf`.
`scripts/check_sources.py` checks every URL in the store: **0 dead**.

ITU's own India README asks for clause-wise chunking of the Acts because Indian statute text is
section-numbered. ITU's reference ingest splits on ~256-word paragraph boundaries and records no
section, page or hash. This does what the README asks: every chunk in the Chroma collection
`kb_main` carries `clause_id`, `instrument`, `jurisdiction`, `page`, `sha256` and
`verbatim_status`, so a retrieved chunk can be *cited*, not merely quoted.

### What the real text caught

Verification was not cosmetic. It found a substantive error in the pack:

- `IN.TA2023.s24` is **"Establishment of Digital Bharat Nidhi"** — the USO Fund. An earlier draft
  cited it for a priority-routing obligation. The only priority-routing provision in the Act is
  **s.20(1)(b)**, and the rule now cites that. A regression test keeps s.24 out of it.
- **Zero of the Act's 62 sections mention roaming.** The P4 "no standing trigger" finding is now
  evidenced by the absence, not assumed.
- `IN.DPDP2023.s7(h)` confirmed as the disaster-processing ground (not 7(g)), now quotable real
  text including the Explanation that points at DM Act 2005 s.2(d).
- A claimed "3-hour takedown under the IT Amendment Rules 2026" was **dropped**: the ITU file said
  to support it is a one-page MeitY notice about a different draft.
- `US.FCC.MDRI.*` renamed to `US.CFR47.4.17.*`, the MDRI's actual regulatory home.

27 real records carry an interpolated marginal heading from a gazette page break. They are flagged
`verified_with_artifacts` and excluded from `quotable` rather than auto-cleaned — a heuristic fix is
~65 % accurate and would mangle statutory text. Full detail and the verification priority order:
[`data/sources/CLAUSES_PROVENANCE.md`](data/sources/CLAUSES_PROVENANCE.md).

## Rubric traceability

| Rubric criterion | Feature that scores it | Demo evidence |
|---|---|---|
| **KB quality** — completeness, accuracy, structure; retrieval under query | Clause store (1 record/clause, URL, SHA-256) + ITU Chroma KB + BM25/vector/hybrid/tree comparison | `docs/kb_report.md`, `docs/retrieval_eval.md` |
| **Agent capability** — relevant, accurate responses in error scenarios; adheres to laws and mandates | Policy & Legal Adviser queryable mid-scenario; role-bound agents citing rule IDs; Game Master enforcement | `docs/adviser_eval.md`; ask the Adviser at T+90 in the UI |
| **Gap identification** — unclear responsibilities, legislative gaps, coordination problems; **global + neighbouring examples (critical)** | Deterministic gap classifier (policy / coordination / execution / standards) + cross-pack replay, merged with gaps read from the instruments themselves. `confidence` is **computed from clause provenance**, never asserted | `docs/gap_register.md` — 11 rows, each with an Indian clause, a neighbour and a global example; `docs/failure_atlas.md` |
| **Auditability** — logs, chain-of-thought traces, source attribution | Hash-chained JSONL ledger; every proposal stores `reasoning`, `cited_rule_ids` **and `cited_clause_ids`** (resolved by the Game Master from the pack, not claimed by the agent); every LLM call stores prompt hash, retrieved chunk IDs, raw output | `verify_ledger.py --tamper-demo` breaks a chain on camera; **Why?** tab; `outputs/audit_sample.jsonl` |
| **Alignment with ITU standards** — Y.3172 pipeline + AI Readiness | `@node(...)` decorators on every entry point; map generated from the source. AI Readiness labels read from ITU's own `dimensions.json`, never retyped | `docs/y3172_map.md`, `docs/ai_readiness_map.md` |
| **Rubric traceability itself** | 18 checks over the repo, each PASS / WAIVED-with-a-reason / FAIL, measured on every run | `docs/rubric_status.html` |

### The brief's mandatory items

- [x] Agent roles: innovative AI solution (`tsp_network`, the 5G network agent) / policy & legal adviser / institutional participants / multi-agent coordination
- [x] **Sequenced, chunked events released progressively; incomplete, uneven, delayed per agent** — `visible_to` + `delay_by_role`; the operator never receives a meteorological warning, the neighbour is 75+ min behind
- [x] **Audit logging + chain-of-thought tracing** — hash-chained ledger, `reasoning` on every proposal
- [x] Host-country documents mapped — 23 Indian clause records across 7 instruments
- [x] Y.3172 + AI Readiness alignment
- [x] Open-source repo + KB + published gaps

---

### Alerts are CAP 1.2 / ITU-T X.1303 shaped

Every alert the `sdma_alerts` agent issues carries a real CAP 1.2 envelope, built deterministically
from the action's own parameters: `identifier`, `sender`, `sent`, `status`, `msgType`, `scope` and an
`info` block with `language`, `category`, `event`, `urgency`, `severity`, `certainty` and
`area/areaDesc`. Three details are worth knowing:

- **`sent` is a real dateTime**, derived from the scenario epoch (16 May 2020 08:45 IST) plus the
  tick — never from the wall clock, so a replayed run produces a byte-identical envelope.
- **`status` is `Exercise`, never `Actual`.** A simulated alert claiming CAP status `Actual` would
  be the one genuinely misleading field available, so it is the one field we pin.
- **`info/language` is the district's own language tag**, local-language-first: `or-IN` in Odisha,
  `bn-IN` in West Bengal, `bn-BD` across the border in Khulna. The same language takes a different
  tag on each side of a border, and P3 is a cross-border property.

**No polygons are declared.** We hold no district boundary file, and CAP makes `cap:polygon`
optional while requiring `cap:areaDesc`. The one shape in the scenario is a `cap:circle` at
21.65°N 88.30°E — the landfall point the IMD release states. A boundary drawn from memory would be
fabricated geodata dressed as official, so every other area emits `areaDesc` alone.

## Architecture

```
SRC (acts, rules, scenario)
  -> C    kb/ingest.py        ITU reference ingest -> Chroma; clauses -> SQLite
  -> PP   policy/compiler.py  YAML pack -> Rules; clause IDs must exist and hash-match
  -> M    agents/*            LLM agents or rule twins PROPOSE
  -> P    policy/engine.py    deterministic ALLOW | BLOCK | NEEDS_HUMAN
  -> D    sim/bus.py + sim/game_master.py   route facts, resolve in order, apply effects
  -> SINK ledger, failure atlas, gap register, comparison board
```

### The multi-agent framework is hand-written, on purpose

No LangGraph, no AutoGen, no CrewAI. The orchestration is DeepMind's **Concordia** split — agents
propose, a Game Master resolves — with one deliberate change: `sim/game_master.py` is ordinary
Python, not a model. Resolution order inside a tick is fully determined by
`(t, role priority, proposal_id)`, which is what makes "same seed, same ledger head hash" true and
testable. A graph framework would put a scheduler we do not control between the proposal and the
verdict, and the determinism claim would go with it.

What the frameworks usually provide, and where it lives here instead:

| Concern | Here |
|---|---|
| Agent protocol / tool schema | `agents/base.py` — one `Agent` Protocol, three tiers (`rule`, `llm`, `jev`) |
| Message passing | `sim/bus.py` — per-role inboxes with redaction and channel latency |
| Orchestration | `sim/game_master.py` — one world state, one rulebook, one order |
| Structured output | Pydantic `Proposal`; an unparseable LLM reply becomes a logged `NOOP`, not a crash |
| Model access | `llm/client.py` — LiteLLM with a record/replay cache, so a demo never depends on a provider |
| Tracing | `audit/ledger.py` — a hash chain, not a dashboard |

Where the AI actually is: **agent reasoning** (the three tiers above), **retrieval** (BM25 +
ChromaDB vectors fused by RRF), and **search** (Hypothesis property-based fuzzing — the component
that finds the failures). None of them decides anything.

Four design commitments do the real work:

**The LLM never decides legality or world state.** `policy/engine.py` is pure Python over compiled
rules. `tests/test_p2_policy_engine.py::test_engine_has_no_llm_import` walks the transitive import
graph and fails the build if the P node can reach `llm/` at all.

**Agents only propose.** No agent holds a reference to the world. The Game Master resolves every
proposal against one world state and one rulebook in one order — `(t, role priority, proposal_id)`.
That is what lets the agents hold genuinely partial, conflicting information (which the brief
*requires*) without Cognition's conflicting-implicit-decisions failure mode.

**An overreach is a finding, not an error.** A proposal outside a role's powers is not filtered out;
it reaches the engine and comes back `BLOCK: ultra_vires` with the clauses that deny the power. A
filtered overreach would be a destroyed finding.

**Replay is real.** No wall clock, no `uuid4`, no unseeded RNG. The same seed reproduces an
identical ledger head hash, asserted in `tests/test_p3_determinism.py`. LLM calls go through a
record/replay cache keyed on `sha256(model, prompt, schema)`, because a model is not bit-deterministic
and the cache is what makes "replay from seed" true rather than aspirational.

**Legality never goes through similarity search.** Rules cite clause IDs; the engine fetches them by
exact ID from SQLite and compares hashes. Vector and BM25 retrieval exist only for the Adviser's
free-text questions, and §9.2 measures them rather than assuming them.

---

## What "harm" means here

Property violations, not money or lives with confidence intervals. The brief's FAQ says accuracy is
not scored, and invented casualty figures with invented error bars are an attack surface a judge can
puncture in one question. So the units are cells, minutes and percentages, stated as illustrative,
and the thresholds live in the scenario YAML where anyone can change them and re-run.

---

## Limits

- The world is **synthetic**. Timings are shaped to exercise the properties, not to reconstruct any
  real cyclone. Backtesting against documented Amphan timelines is future work.
- Thresholds are **illustrative**, not legal or engineering standards.
- Policy packs are **encodings of selected clauses for simulation — not legal advice**, and not a
  complete statement of any jurisdiction's law. They omit far more than they include.
- **The corpus is mixed, and 30 % of it is still unverified.** 110 records carry real gazette text;
  47 are model-written summaries of instruments not yet obtained (Suspension Rules 2024, Telecom
  Cyber Security Rules 2024, CERT-In Directions, DM Act 2005, DoT SOP-2020, 47 CFR 4.17, the
  Bangladesh and Bhutan SOPs, the ITU Recommendations). Check `provenance` before quoting any
  record.
- **Three findings rest on *negative* records** — assertions that an instrument is silent on
  something (`IN.TCSR2024.no_order_auth`, `BT.TELSOP.no_roaming`, `BD.NETS.gap`). These carry the
  highest risk in the corpus: proving a silence needs the full notified text, and we have secondary
  reporting. The P2 finding depends on one of them. Say so, or get the text.
- **The network layer is synthetic and will stay so.** No public cell-site-level outage dataset
  exists for any Indian cyclone. Cell counts are scaled from reported aggregates (~8,500 towers /
  ~36,000 base stations across the affected districts; networks at 65–70 % capacity on day 3), and
  per-cell outage is simulated.
- **The forged order never happened.** No real forged-order incident is on record; it is a
  constructed adversarial test, labelled as such in the scenario file.
- The retrieval eval **saturates**: recall@5 = 1.000 for BM25 on 45 clauses means the eval is too
  small to discriminate, not that the method is validated. MRR is the informative column at this size.
- The Adviser eval's C1/C4 are decided mechanically and are trustworthy. **C2 and C3 are unjudged**
  until a judge model is configured, and the `human_check` column ships empty on purpose — all 20
  rows are meant to be hand-marked, because judges miss what humans catch.
- LLM agent behaviour is **not yet measured**: no model was reachable in the build environment, so
  every number above comes from the deterministic rule twins. The LLM path is implemented and tested
  against a seeded cache, not against a live model.
- The **Jev / TypeSafe AI third agent tier (spec §11) is not built.** It is waitlist-gated, no API
  key was available, and no MVP feature depends on it — as the spec requires.

---

## Standards alignment

**ITU-T Y.3172** — every module declares its pipeline node, and `docs/y3172_map.md` is generated from
the `@node(...)` decorators, so it cannot drift from the code. The P node is where this architecture
earns the citation: the policy node constrains the model node's output before it reaches the network,
which is exactly what Y.3172 specifies and exactly what the engine-purity test enforces.

**ITU-T Y.3173** — irreversible actions return `NEEDS_HUMAN` and pass through a human-in-the-loop
gate rather than executing autonomously. In batch mode the gate auto-approves after a delay and
**records that the approval was automatic**, so no report can claim a human reviewed it.

**ITU AI Readiness 2.0** — primary **D10 AI & Policies** (policy simulation); also **D4**
contextualisation and regional impact, **D8** collaboration with AI, **D3** cross-domain correlation,
**D11** AI for inclusion, **D13** digital infrastructure. Open source is a *factor*, not D1 — D1 is
the data/model marketplace.

**The brief's eight perspectives**

| Perspective | How it shows up |
|---|---|
| Open data / open source | Repo, clause KB, and gap register all published |
| GenAI content ecosystem | Eight constructed events carry `synthetic: true` and are **greyed in the UI timeline**; the rumour and the forged order are adversarial tests, and the forged order is what P2 exists to catch. The IT Rules takedown claim was dropped rather than asserted |
| Contextualisation | Indian instruments, Odisha/West Bengal/Khulna areas, Odia and Bengali alert requirements |
| Cross-domain | Telecom × disaster management × cyber (CERT-In) × data protection (DPDP) in one rulebook |
| Human supervision | `NEEDS_HUMAN` on irreversible acts, with the gate's automatic approvals logged as automatic |
| Policy opportunity identification | `outputs/gap_register.csv`, classified and cross-compared |
| Social inclusion | P3 fails unless the alert is in a language of that area — English alone does not discharge the duty — and each CAP envelope's `info/language` is that district's own tag, local-language-first (`or-IN`, `bn-IN`, `bn-BD`) |
| Digital infrastructure & energy | A three-pack sweep is ~0.5 s and **zero tokens**: the legality decision is code, so inference is optional and confined to the Adviser. Battery drain is modelled and gated on actual grid loss. Measured per run in `docs/run_stats.md` |

---

## Repository

```
chakravyuh/
  schemas.py          all Pydantic models          y3172.py   node registry -> generated map
  kb/      ingest · clause_store · retrieve · tree_index
  policy/  compiler · engine          (engine imports nothing from llm/, enforced by test)
  world/   state · dynamics           (dynamics is the only writer to the world)
  sim/     events · bus · game_master · runner
  agents/  base · roles · rule_agents · llm_agent · adviser
  fuzz/    properties · mutations · machine · shrink_report
  analysis/ gaps · compare · gap_register
  audit/   ledger · trace            llm/  client (record/replay)
  alerts/  cap        (CAP 1.2 / ITU-T X.1303 envelopes; no model, so replay is identical)
app/streamlit_app.py   scripts/   tests/
web/      Next.js 16 static site; renders artefacts, computes nothing
  app/{,simulation,agents,failures,gaps,evidence,standards}   lib/types.ts = the data contract
data/{sources,packs,scenarios,eval,gaps}   inputs only — see data/README.md
docs/     the five documents the ITU architecture names; everything else is generated
outputs/  generated data: gap_register.csv · audit_sample.jsonl · comparison.json
runs/     generated ledgers, one per (scenario, pack, tier, seed)
```

Generators write straight to their final home — `docs/` for what a judge reads, `outputs/` for
machine-readable data — so there is no intermediate build directory and no copy step. Only
sources are committed: `outputs/`, `runs/`, `data/clauses/` and `web/public/data/` are all
regenerated by `python scripts/showcase.py`, and `.gitignore` says so at each one.

## Future work

Backtest against documented Amphan timelines; expert panel review of the packs; more neighbour packs
(NP, LK, BT, MV); Bhashini integration for live translation; CAP XML emission conformant to X.1303;
A2A/MCP-based inter-agent protocol; the Jev agent tier (§11); propose the failure-card format to
ITU-T SG13 via TEC/NWG-13.

## Licence and status

Research prototype. Not legal advice. Not for operational use.
