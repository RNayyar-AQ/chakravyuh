# CHAKRAVYUH — Implementation Spec (for an AI coding agent)

> **Read this whole file before writing code.** It is the single source of truth for the build.
> Target: ITU AI for Good Sandbox Build-a-thon 5.0 ("Creating innovative agents in 5G"), New Delhi, 10 Oct 2026.
> Owner: Ranny Nayyar (team lead, Quantum QAI). Confidence tags: **[Certain]** = verified source, **[Likely]** = strong inference, **[Guessing]** = assumption, flag it if wrong.

---

## 0. TL;DR decisions (do not relitigate these)

| Decision | Choice | Why (one line) |
|---|---|---|
| Orchestration | **Plain Python discrete-event engine + "Game Master"**, no agent framework in the core loop | Determinism and replay matter more than framework features; Concordia's grounded-action pattern |
| Agents | **Role-bound LLM agents returning typed JSON (Pydantic)**, plus **rule-based twins** of each for fuzzing | LLMs for the showcase run, cheap rules for thousands of fuzz runs |
| Who decides outcomes | **Deterministic Game Master + policy engine** (Y.3172 P-node). LLM never decides legality or world state | Rubric: auditability; Riyadh winners separated verdict from LLM |
| Fuzzing + shrinking | **Hypothesis** (property-based testing, stateful) | Shrinking to a minimal replayable case is built in; don't hand-roll it |
| Knowledge base | **Hybrid, three layers:** (1) structured clause store (SQLite, exact lookup by clause ID + hash), (2) ITU reference ChromaDB vector index (mandatory) + BM25, (3) PageIndex-style section tree for long acts (optional, P2) | Brief mandates the ITU vector KB; legality must not depend on similarity search |
| LLM access | **LiteLLM** client → Ollama `qwen2.5:14b` (ITU reference stack) **and** one hosted model (Claude/GPT) | Same code on Sandbox and laptop |
| Replayability with LLMs | **Record/replay cache** keyed by `sha256(model, prompt, schema)`; temperature 0 | LLMs aren't bit-deterministic; the cache is what makes "replay from seed" true |
| Audit | **Append-only, hash-chained JSONL ledger**; every action stores cited clause IDs + reasoning trace | Rubric criterion "Auditability" |
| UI | **Streamlit** (single page, 4 tabs) | Fastest credible demo |
| Harm | **Property violations, not money/lives with CIs.** Illustrative units only, stated as such | Accuracy is not scored; invented CIs are an attack surface |
| Jev (TypeSafe AI) | **Optional third agent tier for fuzzing only, behind a flag.** Never in the policy engine, never for showcase agents. See §11 | Fast typed decisions fit fuzz throughput; no rationales, waitlist access, and weak on dates and negation rule out everything else |

**MVP scope (hard cap):** 1 cyclone scenario (Amphan-like, Odisha → West Bengal → Bangladesh), 3 policy packs (India-current, Bangladesh, US-FCC-MDRI-style "standing roaming trigger"), 2 fuzz mutation families (forged order, delayed/rumour-driven events), 6 agents, 4 properties. Everything else is §13 "Future work".

---

## 1. Research basis (why this architecture)

### 1.1 Multi-agent: when it helps, when it hurts
- **[Certain] Anthropic, "How we built our multi-agent research system" (2025):** orchestrator–worker; multi-agent beat single-agent Opus 4 by 90.2% on their research eval, but used ~15× the tokens of chat. Works for breadth-first, parallelisable tasks; poor fit for "domains requiring shared context across agents" or "real-time coordination". Subagents need "an objective, an output format, guidance on tools and sources, and clear task boundaries". Eval: start with ~20 cases, LLM-as-judge with a rubric, plus human review. Production needs full tracing and external memory.
- **[Likely] Cognition, "Don't Build Multi-Agents" (2025):** actions carry implicit decisions; parallel agents with partial context make conflicting decisions. Their remedy: share full traces, or keep a single thread.
- **[Likely] Anthropic, "Building effective agents" (2024):** prefer simple, composable workflows (chaining, routing, parallelisation, orchestrator-workers, evaluator-optimizer) before autonomous agents; invest in tool interfaces.
- **[Certain] OpenAI, "A practical guide to building agents" (2025):** maximise a single agent first; manager-vs-decentralised patterns; layered guardrails; human intervention for high-risk actions.

**How CHAKRAVYUH reconciles this:** the brief *requires* agents with "different information, different mandates, independent assessments" and information "received at different times". So partial context is the **object of study**, not a bug. Cognition's failure mode (conflicting implicit decisions) is neutralised because **agents only propose; the Game Master resolves every proposal against one world state and one rulebook, in order.** No agent ever mutates the world directly. This is exactly where multi-agent is defensible.

### 1.2 Grounded simulation
- **[Certain] Concordia (DeepMind, 2023, arXiv 2312.03664):** a Game Master translates agents' natural-language intents into grounded effects in the world. We use the same split, but our Game Master is deterministic code, not an LLM.

### 1.3 Knowledge base: vector vs vectorless vs structured
- **[Certain] Anthropic Contextual Retrieval (2024):** contextual embeddings cut failed retrievals 35%; + BM25 49%; + reranking 67%. If the corpus is < ~200k tokens (~500 pages), consider putting it all in the prompt with caching instead of RAG.
- **[Likely] PageIndex (VectifyAI):** vectorless, builds a ToC-like tree and lets the LLM reason down it. Claims 98.7% on FinanceBench (vendor-reported, via Mafin 2.5; verify before citing). Strong for long, well-structured documents (statutes, regulations); weaker on noisy PDFs; slower and costlier per query; no access control.
- **[Certain] Brief requirement:** use "ITU reference code to extract, structure, and ingest data into a vectorized, distributed knowledge base hosted in the ITU AI for Good Sandbox". The ITU reference stack is Ollama `qwen2.5:14b` + `nomic-embed-text` + ChromaDB (collections `kb_main`, `kb_decisions`, `kb_framework`). **[Likely]** from the team's teardown of the Riyadh reference code.

**Verdict:** you cannot go fully vectorless (brief mandates the vector KB). But **legality checks must never go through similarity search**: rules cite clause IDs, the policy engine fetches clauses by ID from the structured store, and the verbatim check compares hashes. Retrieval (vector + BM25, optionally tree) is used only by the **Policy & Legal Adviser** agent to answer free-text questions. Then **measure** it (§9.2): BM25 vs vector vs hybrid vs tree, recall@5 on 30 labelled questions. That table is direct evidence for rubric criterion "Knowledge base quality".

### 1.4 Fuzzing and shrinking
- **[Certain] Hypothesis** (Python property-based testing) supports stateful testing (`RuleBasedStateMachine`) and automatically shrinks failing examples to a minimal case; failures are reproducible from a stored seed/database. This is "policy fuzzing" off the shelf.

---

## 2. Rubric → feature traceability (keep this table in the README and report)

| Rubric criterion [Certain, from brief] | Feature that scores it | Demo evidence |
|---|---|---|
| KB quality: completeness, accuracy, structure; retrieval under query | Clause store (1 record/clause, URL, SHA-256) + ITU Chroma KB + retrieval eval table | `kb_report.md` with counts per instrument + recall@5 table |
| Agent capability: relevant, accurate responses in error scenarios; adheres to laws, mandates, coordination | Policy & Legal Adviser (queryable mid-scenario), role-bound agents citing rule IDs, Game Master enforcement | Live: ask the Adviser a question at T+90 min; show cited clauses |
| Gap identification: unclear responsibilities, legislative/standards gaps, coordination problems, conflicting objectives; **global + neighbouring-country examples (critical)** | Failure atlas + gap classifier (policy / coordination / execution) + cross-pack comparison | `gap_register.csv`: gap, domain, India clause, neighbour example, global example, evidence run ID |
| Auditability: logs, chain-of-thought traces, source attribution | Hash-chained ledger; each agent output stores `reasoning`, `cited_clause_ids`, `retrieved_chunk_ids` | Ledger viewer tab; `verify_ledger` CLI returns OK |
| Alignment with ITU standards: Y.3172 pipeline + AI Readiness Framework | Modules tagged with Y.3172 node; auto-generated node map; 8-perspective mapping table | `y3172_map.md` generated from code |

Brief's mandatory items checklist [Certain]:
- [ ] Agent roles: Innovative AI solution / Policy & legal adviser / Institutional participant / Multi-agent coordination (we do all four)
- [ ] **Sequenced, chunked events released progressively; incomplete, uneven, delayed per agent** (§5.3)
- [ ] **Audit logging + chain-of-thought tracing** (§7)
- [ ] Host-country documents mapped (India register)
- [ ] Y.3172 + AI Readiness alignment (§8)
- [ ] Open-source repo + KB + gaps published

---

## 3. Tech stack

| Layer | Tool | Version pin guidance | Notes |
|---|---|---|---|
| Language | Python | 3.11 | |
| Schemas | Pydantic | v2 | All inter-module data is a Pydantic model |
| LLM client | LiteLLM | latest | `OLLAMA_BASE_URL`, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` from env |
| Local model | Ollama `qwen2.5:14b`, embeddings `nomic-embed-text` | ITU reference | Match the Sandbox |
| Hosted model | one of Claude Sonnet / GPT class | via env | Use for the showcase run only |
| Vector DB | ChromaDB | match ITU reference code | Use ITU ingest scripts as-is where possible |
| Lexical | `rank_bm25` | | Hybrid with Chroma via reciprocal rank fusion |
| Reranker (P2) | `bge-reranker-base` via sentence-transformers | | Only if recall@5 < 0.8 |
| Tree index (P2) | PageIndex (open-source repo) **or** own 60-line ToC tree from statute headings | | Statutes have clean section structure |
| Clause store | SQLite (stdlib `sqlite3`) | | Exact lookup by `clause_id` |
| Fuzzing | Hypothesis | latest | `RuleBasedStateMachine` + `@seed` |
| Event engine | own priority queue (`heapq`) | | SimPy unnecessary |
| Ledger | JSONL + `hashlib.sha256` | | Hash chain |
| UI | Streamlit + Plotly | | 4 tabs |
| Tests | pytest | | Every module has acceptance tests (§10) |
| Optional | MCP server exposing `kb.search` / `kb.get_clause` | | Nice standards story (agent tooling); P3 |

No LangGraph/CrewAI/AutoGen in the core. **[Likely]** They add hidden state and nondeterminism that fight replay. If the team wants LangGraph for the Adviser's internal retrieve→answer→verify loop, it is allowed **inside** that one agent only.

---

## 4. Repository layout (Y.3172 node in every module docstring)

```
chakravyuh/
  README.md                  # rubric table (§2), quickstart, limits
  pyproject.toml
  .env.example
  data/
    sources/                 # downloaded PDFs/MD (git-lfs or links only)
    clauses/                 # clauses.jsonl (generated) + clauses.sqlite
    packs/                   # india_current.yaml, bangladesh.yaml, fcc_mdri.yaml
    scenarios/amphan_like.yaml
    eval/retrieval_qa.jsonl  # 30 labelled Q -> gold clause_ids
    eval/adviser_cases.jsonl # 20 scenario questions + rubric
  chakravyuh/
    schemas.py               # ALL Pydantic models (§6)
    y3172.py                 # node enum + registry decorator; generates y3172_map.md
    kb/
      ingest.py              # SRC + C: wraps ITU reference ingest -> Chroma; also writes clause store
      clause_store.py        # PP: exact lookup, verbatim/hash check
      retrieve.py            # hybrid BM25 + vector (+ tree) with RRF
      tree_index.py          # P2
    policy/
      compiler.py            # PP: YAML pack -> validated Rule objects, every rule cites clause_ids that exist + hash-match
      engine.py              # P node: evaluate(action, state, pack) -> Verdict. NO LLM IMPORTS ALLOWED.
    world/
      state.py               # 5G world state (cells per circle, slices, priority, roaming, alerts, outages)
      dynamics.py            # deterministic effects of approved actions + exogenous events
    sim/
      events.py              # scenario loader, chunked release, per-role visibility + delay
      bus.py                 # D node: message bus with per-channel latency
      game_master.py         # resolves proposals in time order; calls policy.engine; applies world.dynamics
      runner.py              # run(scenario, pack, agents, seed) -> RunResult
    agents/
      base.py                # Agent protocol: observe(inbox) -> list[Proposal]
      llm_agent.py           # generic role-bound LLM agent (prompt template + schema)
      rule_agents.py         # deterministic twin per role (for fuzzing)
      roles.py               # role definitions: mandate, powers, inbox filters, prompt
      adviser.py             # Policy & Legal Adviser (RAG, queryable)
    fuzz/
      properties.py          # P1..P4 invariants (§5.5)
      mutations.py           # forged order, delay, rumour, damage shift
      machine.py             # Hypothesis RuleBasedStateMachine
      shrink_report.py       # minimal case -> failure card
    analysis/
      gaps.py                # classify violation -> policy | coordination | execution
      compare.py             # same failure seeds across packs
      gap_register.py        # writes gap_register.csv
    audit/
      ledger.py              # append, verify chain
      trace.py               # per-call trace capture (prompt hash, retrieved ids, reasoning, output)
    llm/
      client.py              # LiteLLM wrapper + record/replay cache
  app/
    streamlit_app.py
  scripts/
    build_kb.py  run_demo.py  run_fuzz.py  eval_retrieval.py  eval_adviser.py  verify_ledger.py  gen_y3172_map.py
  tests/
```

---

## 5. Core design

### 5.1 Data flow (Y.3172 labels)

```
SRC (acts, rules, register, scenario) 
  -> C  kb/ingest.py (ITU reference ingest -> Chroma; clauses -> SQLite)
  -> PP policy/compiler.py (YAML pack -> Rules; verbatim+hash check)
  -> M  agents/* (LLM or rule twins propose actions)
  -> P  policy/engine.py (deterministic: ALLOW | BLOCK | NEEDS_HUMAN)
  -> D  sim/bus.py + sim/game_master.py (route events/messages, apply effects)
  -> SINK ledger, failure atlas, gap register, comparison board (Streamlit)
```

### 5.2 Agents (MVP = 6)

| Role id | Real-world analogue | Powers (examples, from pack) | Sees |
|---|---|---|---|
| `competent_authority` | Union/State Home Secretary under Telecom Act 2023 s.20 + Suspension Rules 2024 | order suspension (area, duration), order disaster roaming | official reports, rumour reports, orders inbox |
| `tsp_network` | Telecom operator NOC (**the 5G network/services agent**) | re-prioritise slices (E.106-style priority for relief), restore sites, enable roaming once ordered, report incidents | cell/site telemetry, orders |
| `sdma_alerts` | NDMA/SDMA (DM Act 2005), CAP alerts via SACHET | issue CAP alert (area, language) | IMD-style warnings, damage reports |
| `cert_in` | CERT-In (Directions 2022, 6-hour reporting) | receive incident reports, flag forged orders | incident reports only |
| `neighbour_authority` | Bangladesh regulator / disaster authority | its own pack's powers; cross-border alert/roaming requests | cross-border channel only (higher latency) |
| `adviser` | Policy & Legal Adviser | none (advisory); answers questions with cited clauses | KB + read-only ledger summary |

Each role has a **mandate** (what it optimises), **powers** (action types it may propose), **inbox filter** (which events reach it), and **channel latencies**. Delegation spec per Anthropic lesson: every LLM agent prompt contains objective, output schema, allowed actions, and boundaries ("you cannot see X; if unsure, request information via `ASK` action").

`Proposal` must include `cited_rule_ids` (may be empty) and `reasoning` (stored as the CoT trace). An agent that proposes an action outside its powers → Game Master `BLOCK` with reason `ultra_vires`, which is itself a logged finding.

### 5.3 Events: sequenced, chunked, uneven (mandatory brief item)

Scenario YAML defines a timeline of `Event`s. Each event has:
- `t_minutes` (release time), `type` (`IMD_WARNING`, `LANDFALL`, `SITE_DOWN`, `RUMOUR`, `ORDER`, `DAMAGE_REPORT`, `CROSS_BORDER_REQUEST`, ...)
- `visible_to: list[role]` and `delay_by_role: dict[role, minutes]`, so the same fact reaches different agents at different times
- `authentic: bool` (forged orders are `False`; agents don't see this field)
- `truth` payload (what really happened; only the Game Master and world see it)

The runner advances simulated time in 15-minute ticks; at each tick: release due events → deliver via bus with delays → agents observe their inbox and propose → GM resolves in deterministic order (by `t`, then role priority, then proposal id) → world dynamics step → ledger append.

### 5.4 Game Master and policy engine (P node)

```python
def resolve(proposal, state, pack) -> Verdict:
    # 1. powers check (ultra vires)
    # 2. authentication check: if proposal triggered by an ORDER event with authentic=False
    #    and pack has no authentication requirement -> ALLOW (this is the vulnerability we measure)
    # 3. evaluate rules matching (actor_role, action_type): conditions, preconditions (e.g. approval delay),
    #    prohibitions, obligations
    # 4. reversibility: irreversible actions -> NEEDS_HUMAN (Y.3173-style), human-in-loop stub
    #    auto-approves after configured delay in batch mode; real click in UI mode
    # 5. return Verdict(decision, rule_ids, clause_ids, explanation)
```

`policy/engine.py` **must not import** anything from `llm/`. Add a test that fails if it does. Support `mode: advisory | blocking` per pack (the India register's flagged P-node gap) [Certain, register exists]: in advisory mode, violations are logged but the action still executes.

### 5.5 Properties (what "harm" means: replaces confidence intervals)

Each is a boolean invariant checked over the run, with a measured margin in illustrative units.

| ID | Property | Measured as |
|---|---|---|
| P1 | During any suspension, relief/emergency traffic in affected cells stays reachable | min % of affected cells with priority slice up |
| P2 | No irreversible action executes on an unauthenticated (forged) order | count of executions traced to `authentic=False` |
| P3 | Every affected area (incl. across the border) gets a public alert within T_alert of the warning, in a local language | max delay (min); areas missed |
| P4 | Disaster roaming active in affected circles within T_roam of landfall | max delay (min) |

Thresholds live in `scenarios/*.yaml` and are stated as **illustrative** in the report. A failure = property violated.

### 5.6 Gap classification (deterministic, defensible)

For each violation, walk the ledger backwards:
- **Policy gap:** no rule in the pack permits/obliges the action that would have prevented it (e.g. no standing roaming trigger; no authentication requirement on orders).
- **Coordination gap:** a rule permits it, but the empowered agent did not receive the needed fact in time (bus delay/visibility).
- **Execution gap:** rule permitted it and the fact arrived, but the agent did not act (LLM or rule-agent choice).

Output a `GapFinding` with responsible clause ID(s), the evidence run ID, and **cross-pack result**: does the same seed pass under Bangladesh pack / FCC-MDRI pack? That gives the "global + neighbouring example" the rubric calls critical [Certain].

Gaps must be phrased **domain-first, country as instance** (brief note [Certain]): "Emergency telecom: no standing cross-border roaming trigger. Instance: India–Bangladesh. Comparator: FCC MDRI (US)."

### 5.7 Fuzzing (rule-based twins only)

`fuzz/machine.py` defines a Hypothesis `RuleBasedStateMachine` whose rules are mutations applied to the base scenario:
- `shift_event(event_id, dt)`; `delay_channel(a, b, dt)`; `inject_rumour(area, t)`; `inject_forged_order(issuer_claimed, action, t)`; `escalate_damage(area, t)`.
After each step, run the sim with **rule-based agents** and assert P1–P4. Hypothesis shrinks failures. Save each minimal failure as a `FailureCard` (seed, mutation list, violated property, gap class, clause IDs). Budget: `max_examples=300` per pack for the demo. Then **replay the top 3 failure cards with LLM agents** for the showcase and record whether LLM agents fail the same way (interesting either way: report it honestly).

---

## 6. Schemas (`chakravyuh/schemas.py`): implement exactly

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum

class Clause(BaseModel):
    clause_id: str            # e.g. "IN.TA2023.s20.2"
    instrument: str           # "Telecommunications Act 2023"
    jurisdiction: str         # "IN" | "BD" | "US" | "INTL"
    section: str
    text_verbatim: str
    source_url: str
    sha256: str               # of text_verbatim, normalised whitespace
    retrieved_at: str

class Rule(BaseModel):
    rule_id: str
    clause_ids: list[str]     # must exist in clause store; compiler checks hash
    actor_role: str
    action_type: str
    effect: Literal["permit", "oblige", "prohibit"]
    conditions: dict = {}     # simple DSL: {"event_seen": "LANDFALL", "area_in": "affected"}
    approval_delay_min: int = 0
    deadline_min: Optional[int] = None
    requires_authenticated_order: bool = False
    reversible: bool = True

class PolicyPack(BaseModel):
    pack_id: str; jurisdiction: str; version: str
    mode: Literal["advisory", "blocking"] = "blocking"
    rules: list[Rule]

class Event(BaseModel):
    event_id: str; t_minutes: int; type: str
    area: Optional[str] = None
    payload: dict = {}
    visible_to: list[str]
    delay_by_role: dict[str, int] = {}
    authentic: bool = True
    claimed_issuer: Optional[str] = None

class Proposal(BaseModel):
    proposal_id: str; t_minutes: int; actor_role: str
    action_type: str          # or "ASK" / "NOOP"
    params: dict = {}
    cited_rule_ids: list[str] = []
    reasoning: str            # stored as CoT trace
    triggered_by_event_ids: list[str] = []

class Decision(str, Enum):
    ALLOW="ALLOW"; BLOCK="BLOCK"; NEEDS_HUMAN="NEEDS_HUMAN"

class Verdict(BaseModel):
    proposal_id: str; decision: Decision
    rule_ids: list[str]; clause_ids: list[str]
    explanation: str
    mode: Literal["advisory", "blocking"]

class LedgerEntry(BaseModel):
    seq: int; prev_hash: str; hash: str
    t_minutes: int
    kind: Literal["EVENT","DELIVERY","PROPOSAL","VERDICT","EFFECT","LLM_TRACE","ADVISER_QA","PROPERTY"]
    payload: dict

class FailureCard(BaseModel):
    failure_id: str; pack_id: str; seed: int
    mutations: list[dict]
    violated_property: str
    margin: float
    gap_class: Literal["policy","coordination","execution"]
    responsible_clause_ids: list[str]
    passes_under_packs: list[str]   # cross-pack comparison
    replay_cmd: str
```

---

## 7. Audit and tracing

- `audit/ledger.py`: `append(kind, payload)` computes `hash = sha256(prev_hash + canonical_json(payload))`. `verify(path)` recomputes the chain. Tamper test: edit one line, `verify` must fail.
- Every LLM call writes an `LLM_TRACE` entry: model, prompt sha256, retrieved chunk IDs, raw output, parsed `Proposal`, latency, tokens. Prompts themselves stored in `traces/<sha>.txt`.
- `llm/client.py` record/replay: mode `record` writes `cache/<sha>.json`; mode `replay` reads it and fails loudly on a miss. **The demo runs in replay mode** so it is identical every time and immune to Wi-Fi.

---

## 8. Standards alignment artefacts (generated, not hand-typed)

1. `y3172.py` provides `@node("PP")` decorator; `scripts/gen_y3172_map.py` walks modules and writes `y3172_map.md` (node → module → function). Nodes used: SRC, C, PP, M, P, D, SINK [Certain: Y.3172 node vocabulary].
2. AI Readiness 2.0 dimensions [Certain, from report]: primary **D10 "AI & Policies"** (defined as policy simulation), **D4 Contextualization and Regional Impact**, **D8 Collaboration with AI**, **D3 Cross-domain Correlation Analysis**, **D11 AI for Inclusion**, **D13 Digital Infrastructure**. (Do **not** label open source as D1; D1 is Data/model Marketplace. Open source is a *factor*.)
3. Brief's 8 perspectives, one line each in README:
   open data/open source (repo + clause KB published) · GenAI content ecosystem (synthetic rumours labelled per IT Rules 2026 amendment; verify the exact clause) · contextualisation (Indian acts, Odisha/WB, Bengali alerts) · cross-domain (telecom × disaster × cyber × data protection) · human supervision (NEEDS_HUMAN on irreversible acts) · policy opportunity identification (gap register) · social inclusion (alerts in Bengali/Odia for coastal communities on both sides of the border) · digital infrastructure & energy (rule twins for fuzzing; tokens and wall-time per run reported).

---

## 9. Evaluation (small, honest, measured)

### 9.1 KB report
`kb_report.md`: clauses per instrument, % clauses with source URL + hash (target 100%), compiler pass rate (every rule's clause IDs resolve and hash-match).

### 9.2 Retrieval eval (scores "KB quality")
30 hand-labelled questions → gold `clause_id`s (e.g. "Who can order temporary suspension and for how long?" → Suspension Rules 2024 clauses). Compare **BM25 | vector (ITU Chroma) | hybrid RRF | hybrid+rerank | tree (P2)**. Report recall@5 and MRR. Pick the best for the Adviser. Expected **[Guessing]**: hybrid > either alone on statute text because section numbers and defined terms are lexical.

### 9.3 Adviser eval (scores "agent capability")
20 mid-scenario questions with a 4-point rubric: correct clause cited, correct actor/mandate, flags uncertainty when KB lacks an answer, no invented clause. LLM-as-judge (different model from the Adviser) + the team hand-checks all 20 (Anthropic lesson: humans catch what judges miss). Report the table and every disagreement.

### 9.4 Simulation results
- Baseline run (India pack, no mutations): properties pass/fail, timeline.
- Fuzz: # unique minimal failures per pack, breakdown by gap class.
- Cross-pack: for each India failure, which packs pass the same seed.
- **Limits section (mandatory):** synthetic world; thresholds illustrative; packs are encodings of selected clauses, not legal advice; LLM behaviour shown for 3 replayed cases only.

---

## 10. Build order with acceptance tests (follow in order; stop at each gate)

| Phase | Hours | Deliverable | Acceptance test (pytest) |
|---|---|---|---|
| P0 | 1 | Repo, schemas, ledger, LLM client w/ replay | `test_ledger_tamper_detected`, `test_replay_cache_miss_raises` |
| P1 | 3 | Clause store from ~40 hand-picked clauses (IN, BD, US-FCC, Tampere) + ITU Chroma ingest of full docs | every clause has URL+hash; `kb.get_clause(id)` exact; Chroma query returns results |
| P2 | 3 | Policy compiler + engine + 3 packs | `test_engine_has_no_llm_import`; unknown clause id → compile error; ultra vires → BLOCK |
| P3 | 3 | World state + dynamics + events + bus + Game Master + rule agents; baseline run | same seed → identical ledger hash twice |
| P4 | 2 | Properties + gap classifier | hand-built forged-order scenario → P2 violated, gap_class=policy |
| P5 | 2 | Hypothesis fuzz + failure cards + cross-pack compare | ≥1 minimal failure found; replay_cmd reproduces it |
| P6 | 3 | LLM agents (6 roles) + Adviser with hybrid retrieval | adviser answers a known question citing the gold clause |
| P7 | 2 | Evals 9.2, 9.3; gap_register.csv; y3172_map.md | files generated by scripts, not by hand |
| P8 | 2 | Streamlit: Timeline · Ask the Adviser · Failure Atlas · Ledger/Audit | demo runs fully offline in replay mode |
| P9 | 1 | README, report numbers, limits, record 7-min video | — |

**Cut line if behind:** drop P2-level tree index, reranker, MCP, neighbour LLM agent (keep it rule-based). **Never cut:** Adviser, ledger, properties, gap register, cross-pack comparison.

---

## 11. Jev (TypeSafe AI): does it fit?

**What it is** [Certain that these are the published facts; the performance numbers are vendor-reported only]:
- A "System One" model, not an LLM. Input: a block of state (text/JSON) plus typed questions. Output: typed answers with per-option probabilities and a confidence, in one parallel pass. Three primitives: **Choice**, **Score**, **Noul** (yes/no probability). It cannot return a value outside the schema.
- Trained with "Reinforcement Learning for Calibrated Decisions" (RLCD). Architecture and weights are proprietary.
- Early access behind a waitlist since **15 Sep 2026**; HTTP API (`POST https://api.typesafe.ai/v1/systemone`), Python/JS SDKs, a LangChain wrapper. Version jev-1.13.0.
- Vendor claims: 70–500 ms latency; $0.042 per million input tokens, output free; 67.8% on TypeSafe's own 4-workflow benchmark, roughly matching a frontier model at ~290× lower cost. **No independent benchmark exists yet**, and TypeSafe itself flags possible bias.
- Vendor-documented weaknesses: arithmetic, **date comparisons**, numeric precision; reads instructions literally and **mishandles negations**; degrades with irrelevant context; 17.3 points behind the best model on multi-document reconciliation. **No natural-language rationale.**

**Fit, component by component:**

| Component | Fit? | Reason |
|---|---|---|
| Policy engine (P node) | **Never** | Must be deterministic code. And legal logic is exactly Jev's documented weak spot: deadlines (dates), approval delays (arithmetic), prohibitions ("shall not" = negation) |
| Showcase LLM agents | **No** | No reasoning text, so no chain-of-thought trace. That fails the brief's mandatory CoT tracing and the Auditability criterion |
| Gap classifier | **No** | Already deterministic by design |
| Adviser citation check ("does clause X support claim Y?") | **Maybe** | Noul fits, but negation weakness on statute text is a real risk; keep the code check (cited ID ∈ retrieved set) as the gate |
| **Fuzzing agents** | **Yes, the one real fit** | Fuzzing needs thousands of cheap, fast, typed decisions per role. Rule twins are cheap but rigid; LLMs are realistic but cost ~15× chat tokens per run. Jev sits between: each role becomes a Choice question over its allowed actions, given its inbox as state |

**If (and only if) you get API access before the build window**, implement `agents/jev_agents.py`:
- One Choice question per role per tick: options = that role's allowed `action_type`s plus `NOOP`/`ASK`. State = the role's inbox (same as the LLM agent sees).
- Determinism: take argmax, or sample with `numpy.random.default_rng(seed)` from the returned probabilities. Store the full probability vector in the ledger as `JEV_TRACE`. That is auditable data, but **say plainly in the report that it is not a reasoning trace**.
- Route through the same record/replay cache so the demo works offline and is identical every time.
- Run it as a third tier: rule twins → Jev agents → LLM agents (top 3 failure cards only).

**The measurable difference it could make** (report this table; it's the only claim worth making):

| Agent tier | Fuzz runs completed | Unique minimal failures | Wall time | API cost |
|---|---|---|---|---|
| Rule twins | | | | |
| Jev agents | | | | |
| LLM agents (3 cards replayed) | | | | |

If Jev finds failures that rule twins miss at a fraction of LLM cost, that's a real result for the "digital infrastructure and energy" perspective and the Judges' prize. If it finds nothing new, report that honestly.

**Risks:**
1. Waitlist: you may not have a key by 9 Oct [Certain it's waitlist-gated]. **Do not make any MVP feature depend on it.**
2. Runs outside the ITU Sandbox; the brief centres the Sandbox and the reference stack.
3. Three weeks old, vendor-only numbers. Judges may read it as hype; frame it as an experiment with a measured result, not a selling point.

**Build priority: P3** (after everything in §10, before the video). Cut it first if behind.

*Note: an earlier version of this file assumed "jev" meant Meta's JEPA models. JEPA (V-JEPA 2, LLM-JEPA) does not fit either: a learned latent world model would undercut the explicit-simulator claim, and LLM-JEPA requires fine-tuning.*

---

## 12. Prompts (templates; keep short, schema-first)

**Institutional agent (system):**
```
You are {role_name}. Mandate: {mandate}.
You may ONLY propose these actions: {allowed_actions}.
You see only the messages below; you do NOT know anything else about the world.
Legal powers you hold (rule_id: summary): {rules_for_role}
Return JSON matching this schema: {Proposal schema}. Cite rule_ids that authorise your action.
If information is missing, return action_type="ASK" with params.to and params.question.
Do not claim outcomes; you only propose. Keep reasoning under 120 words.
```

**Adviser (system):**
```
You are the Policy & Legal Adviser. Answer using ONLY the clauses provided.
Every claim must cite a clause_id from the context. If the clauses do not answer the question,
say so and name what is missing; this is a gap, report it as GAP: <description>.
Output: answer, cited_clause_ids, gaps[], confidence (high|medium|low).
```
Post-check in code: every cited `clause_id` must be in the retrieved set and exist in the clause store; otherwise reject and re-ask once, then return "insufficient evidence".

---

## 13. Future work (put in report, do NOT build now)
Backtest against documented Amphan timelines; expert panel review; more neighbour packs (NP, LK, BT, MV); Bhashini integration for live translation; CAP XML emission conformant to X.1303; A2A/MCP-based inter-agent protocol; Jev agent tier if not built (§11); failure-card format proposed to ITU-T SG13 via TEC/NWG-13.

---

## 14. Fixes carried over from the proposal review (apply in report + packs)
- DPDP disaster-time processing is **s.7(h)**, not 7(g) [Certain]. 7(g) = epidemics/public health.
- Tampere Convention party status of IN/LK/PK/NP/BD/BT/MV: **verify on UN Treaty Collection before encoding** [unverified].
- IT Rules 2026 amendment "3-hour takedown": verify exact clause from the MeitY PDF before citing [unverified].
- Replace Petri/Bloom/HealthBench references with Y.3172, Y.3181, FG-AINN PoC report, FG-AI4NDM, Concordia.
- Frame related work as "extends the ITU reference what-if mode", not as criticism of ITU's tools or recent winners.

---

## 15. Sources
- Build-a-thon 5.0 brief: https://aiforgood.itu.int/event/build-a-thon-5-0-creating-innovative-agents-in-5g/
- AI for Good Lab Hackathon UAE (FAQ: accuracy not scored): https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/
- ITU AI Ready Report 2.0: https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf
- India AI Regulatory Landscape (ITU Sandbox): https://github.com/CrashingGuru/Sandbox_Training/blob/main/Dataset/India/India_AI_Regulatory_Landscape.md
- Anthropic, multi-agent research system: https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, contextual retrieval: https://www.anthropic.com/news/contextual-retrieval
- Cognition, Don't Build Multi-Agents: https://cognition.com/blog/dont-build-multi-agents
- OpenAI, A practical guide to building agents (summary): https://ibl.ai/blog/openai-a-practical-guide-to-building-agents.md
- PageIndex assessment: https://rubinlake.com/en/technology-radar/ai-and-data-engineering/pageindex
- Concordia (DeepMind): https://arxiv.org/abs/2312.03664
- Jev (Wikipedia): https://en.wikipedia.org/wiki/Jev_(AI_model)
- Jev explained (DataCamp): https://www.datacamp.com/blog/system-one-models-jev
- Jev in an agent harness (Width.ai): https://www.width.ai/post/what-is-jev-ai-typesafe
- Jev failure modes (TypeSafe docs): https://docs.typesafe.ai/model-jaggedness/jev-1.13
- LLM-JEPA: https://arxiv.org/abs/2509.14252
- V-JEPA 2 coverage: https://the-decoder.com/metas-latest-model-highlights-the-challenge-ai-faces-in-long-term-planning-and-causal-reasoning/
- Hypothesis stateful testing: https://hypothesis.readthedocs.io/en/latest/stateful.html
- DPDP Act s.7: https://www.dpdpa.com/dpdpa2023/chapter-2/section7.html
- FG-AINN PoC report: https://www.itu.int/en/ITU-T/focusgroups/ainn/Documents/Proof-of-Concept_activities_2.pdf
