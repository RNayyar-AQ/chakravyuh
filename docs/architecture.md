# Architecture

## The one rule everything else follows

> **Agents propose. Deterministic code decides.**

An agent — LLM or rule-based — can only emit a `Proposal`. It cannot change the world, grant
itself a power, or invent a clause. Legality is decided by `app/chakravyuh/policy/engine.py`, a pure
function over the compiled policy pack with no I/O, no randomness and **no model**. That last
property is enforced by a test that walks the whole import graph on every run, not by convention.

A proposal that exceeds a role's powers is **not filtered out** — it goes to the Game Master and
is BLOCKed as `ultra_vires` and logged. *A filtered overreach is a finding destroyed; a blocked
one is a finding recorded.*

## Y.3172 node map

```
 SRC ─────────► C ──────► PP ──────► M ──────► P ──────► D ──────► SINK
 scenarios/   sim/bus   kb/         agents/   policy/   world/    audit/
 data/        events    ingest      6 roles   engine    dynamics  ledger
 sources      delivery  retrieve    adviser   (PURE)    game_     app/ UI
                        clause_                         master    analysis/
                        store                                     gap_register
```

Node membership is declared by an `@node("P")` decorator on every entry point;
[`y3172_map.md`](y3172_map.md) is **generated from that registry**, so it cannot drift from the
code. `Y.3181` (ML sandbox) is the whole simulated network plus the replay mechanism: the point
of this system is pre-deployment testing of a policy, which is what that recommendation
describes.

## One tick, 15 simulated minutes

```
1. RELEASE   scenario events due at t enter the world and the bus
2. DELIVER   the bus applies per-role latency and per-event delay
             → the same fact lands in different inboxes at different times
3. PROPOSE   each agent reads ONLY its own inbox and proposes
4. RESOLVE   Game Master → policy engine → ALLOW · BLOCK · NEEDS_HUMAN
             approved effects apply; derived events go back on the bus
5. STEP      battery drain, suspensions expire, damage propagates
```

501 ticks per run. Three packs replay in **0.55 s** and **0 tokens**.

## The engine's order of checks

```
0. non-action (ASK / NOOP)      → ALLOW
1. ultra vires?                 → BLOCK   does this role hold this power at all?
2. authenticated order?         → BLOCK   only if a matching rule demands one
3. prohibited?                  → BLOCK
4. any permit / oblige holds?   → BLOCK if none, naming the unmet condition
5. irreversible?                → NEEDS_HUMAN, held at a gate (ITU-T Y.3173)
                                → ALLOW
```

Step 2 is where property P2 lives: the India pack contains **no** rule requiring an
authenticated order, so a forged direction reaches step 4 and is permitted like any other.

## The six agents and their blind spots

| Agent | Can do | Cannot see |
|---|---|---|
| `competent_authority` | declare disaster, order suspension, order roaming | cell telemetry — it can order, never operate, and cannot verify a report |
| `sdma_alerts` | issue CAP 1.2 alerts, request cross-border alerting | network telemetry; cannot compel an operator |
| `tsp_network` | suspend, enable roaming, prioritise relief, restore sites | weather warnings; **cannot verify an order is genuine** |
| `cert_in` | flag a forged order | everything but incident reports — it finds out afterwards |
| `neighbour_authority` | act on its own powers across the border | the other State's orders; **75-minute channel latency** |
| `adviser` | answer questions with citations | — holds **zero powers**, proposes nothing |

**The blind spots are the design.** A single omniscient agent cannot have a coordination
failure, and the Bangladesh P4 finding is exactly that: sites went down in Balasore, only the
operator knew, and only the authority could trigger roaming.

## Data flow for one finding

```
eGazette PDF ──► pdftotext ──► clause record  (text, page, sha256, PDF sha256, source URL)
                                      │
                           compiled into ──► pack rule  (effect, conditions, delays)
                                      │
   scenario event ──► agent proposal ──► ENGINE ──► verdict ──► world effect
                                                        │
                                              property check (P1–P4)
                                                        │
                                            gap classifier ──► register row
                                              (confidence computed from
                                               the provenance of the
                                               clauses the row cites)
```

Every arrow is appended to a hash-chained ledger:
`sha256(prev_hash | seq | t | kind | canonical_json(payload))`. Same seed ⇒ same head hash.

## Where a model may and may not go

| Component | Model? |
|---|---|
| Policy engine (node P) | **Never.** Enforced by an import-graph test. |
| Clause store, properties, gap classifier, fuzzer, Game Master | No. |
| Agent twins (default tier) | No. |
| Agent LLM tier (`--tier llm`) | Optional. Proposals only; every call writes an `LLM_TRACE`. |
| Adviser | Optional. Default is extractive: quotes retrieved clauses, generates nothing. |
| Vector retrieval | A sentence embedder, not an LLM. Affects ranking only. |

Every result in this submission was produced with **zero LLM calls**.
