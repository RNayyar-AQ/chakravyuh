# CHAKRAVYUH — animated showcase brief

**Self-contained.** Every number below is measured, not estimated, and is reproduced here so an
animation can be built without opening the repository. Regenerate them all with one command:
`python scripts/showcase.py`.

Target: **6:30–7:00**, matching the Build-a-thon optional video limit.
Event: ITU AI for Good Sandbox Build-a-thon 5.0, New Delhi, 10 Oct 2026. Team: Quantum QAI.

**Tone instruction for the whole piece:** this is an engineering result, not a pitch. Where a
layer is synthetic or a record unverified, the animation *says so on screen*. The credibility of
the strong claims depends on the weak ones being visible. Do not animate away the caveats.

**Palette:** PASS `#1b7f4f` · FAIL `#b3261e` · constructed/synthetic `#8a8a8a` italic ·
neutral ink `#1a1a1a` on off-white `#faf8f5`. One accent only: `#c75000` for the cyclone track.

---

## Scene 1 — The question (0:00–0:40)

**On screen, one line at a time:**
> A cyclone is 104 hours away.
> The law that governs the response is already written.
> **Does it fire in time?**

**Then the logline:**
> CHAKRAVYUH stress-tests disaster telecom policy before the cyclone does.

**Motion:** cyclone track sweeps the Bay of Bengal toward the Sundarbans; a clock counts
104:45:00 down. Freeze at the question.

---

## Scene 2 — The data (0:40–1:40) · criterion: **Knowledge base**

**Animate this table building row by row. Total must read 157.**

| Provenance | Records | What the text is |
|---|---|---|
| `gazette_pdf` | 106 | The Act's **own words**, split section-by-section from the official eGazette PDF |
| `gazette_pdf_subsection` | 4 | Genuine substrings: s.20(1), s.20(2), s.7(g), s.7(h) |
| `secondary_source` | 18 | Summary, attributed to a named source |
| `model_written` | 29 | Summary, nothing checked |

**Headline number: 110 of 157 = 70.1 % carry the instrument's own words.**
Telecom Act 2023 → **62 sections**. DPDP Act 2023 → **44 sections**. Both counts match the Acts.

**Then zoom into one record** (this is the money shot — animate the four fields landing):
```
IN.TA2023.s20.1
"...messages of a user or group of users authorised for response and recovery
 during public emergency are routed on priority..."
page 9  ·  sha256 a7f3c2…  ·  PDF sha256 4deb2398…
https://egazette.gov.in/WriteReadData/2023/250880.pdf
```
**Caption:** *Every answer points to a clause you can check against the gazette in one click.*

**Scene 2b — what verifying caught (hold 8 s, this is a real finding):**
> We cited **`IN.TA2023.s24`** for a priority-routing obligation.
> Real s.24 is **"Establishment of Digital Bharat Nidhi"** — the USO fund.
> It says nothing about routing.
> ~~s.24~~ → **s.20(1)(b)**. A regression test now keeps s.24 out of that rule.

**And:** *Zero of the Act's 62 sections mention roaming.* Animate a search across 62 section
cards returning **0 hits** — that absence becomes evidence for finding P4 later.

---

## Scene 3 — The agents (1:40–2:40) · criterion: **Agent capability**

**Six nodes in a ring. Animate each one's blind spot as a grey cone it cannot see through.**

| Agent | Can do | **Cannot see** |
|---|---|---|
| `competent_authority` | declare disaster, order suspension, order roaming | cell telemetry — can order, never operate |
| `sdma_alerts` | issue CAP alert, request cross-border alert | network telemetry; **cannot compel an operator** |
| `tsp_network` | suspend, enable roaming, prioritise relief, restore sites | weather warnings; **cannot verify an order is genuine** |
| `cert_in` | flag a forged order | everything but incident reports — finds out *afterwards* |
| `neighbour_authority` | act on its own powers | the other State's orders · **75-min channel latency** |
| `adviser` | answer questions, cite clauses | — holds **zero powers**, proposes nothing |

**Key caption, hold it:**
> **The blind spots are the design.** The authority can order but not see.
> The operator can see but not verify. CERT-In verifies, but only afterwards.

**Then the architecture line — animate the one-way arrow:**
> Agents **propose**. Deterministic code **decides**.
> The policy engine is a pure function. It cannot reach a model —
> an import-graph test proves it on every run.

---

## Scene 4 — One tick (2:40–3:20)

**Animate the five-step loop once, slowly, then speed it to a blur for 501 ticks.**

```
1. RELEASE   scenario events due at t
2. DELIVER   per-role latency → the same fact lands in different inboxes at different times
3. PROPOSE   each agent reads ONLY its own inbox
4. RESOLVE   policy engine → ALLOW · BLOCK · NEEDS_HUMAN
5. STEP      battery drain, suspensions expire, damage spreads
```

**The engine's order of checks — animate as a descending gate sequence:**
```
ultra vires?        → BLOCK
authenticated?      → BLOCK        ← the India pack has NO such rule. Remember this.
prohibited?         → BLOCK
any permit/oblige?  → BLOCK if none, naming the unmet condition
irreversible?       → NEEDS_HUMAN  (ITU-T Y.3173)
                    → ALLOW
```

**Counter in the corner:** `501 ticks · 0.55 s · 0 tokens`.

---

## Scene 5 — The timeline (3:20–4:00)

**15 events on a 125-hour track. SEVEN IN BLACK, EIGHT IN GREY ITALIC.**

| | Event | T+ | Real? |
|---|---|---|---|
| imd01 | Pre-cyclone watch | 0 | **IMD** |
| imd02–04 | Watch → alert → warning, districts named | 705 / 1435 / 2880 | **IMD** |
| sim01 | Sites down | 4155 | *constructed* |
| imd05 | Post-landfall outlook | 4725 | **IMD** |
| sim02 | Rumour | 5595 | *constructed* |
| **sim03** | **Forged suspension order** | **5715** | *constructed — adversarial test* |
| imd06 | **LANDFALL, Sundarbans** | **6285 = 104.75 h** | **IMD** |
| sim04–08 | Damage, power loss | 6375–6600 | *constructed* |

**Caption that must appear:**
> The 7 black events are IMD's own bulletins at IMD's own times.
> The 8 grey ones are **ours**. No public dataset records cell-site outage
> for any Indian cyclone. The forged order never happened —
> it is an adversarial test, not history.

**Landfall beat:** T+6285 min = **104.75 h**, matching the IMD release's stated lead time exactly.

---

## Scene 6 — The result (4:00–5:00) · criterion: **Gap identification** ← strongest

**Build this grid cell by cell. Same storm, same seed, same agents. Only the law changes.**

| | P1 relief survives | P2 no act on forged order | P3 alerted in time | P4 roaming active |
|---|---|---|---|---|
| **India (current)** | **FAIL −60 %** | **FAIL −1** | **FAIL −7140 min** | **FAIL −855 min** |
| **Bangladesh** | PASS +40 | PASS 0 | PASS +345 | **FAIL −855 min** |
| **US 47 CFR 4.17** | PASS +40 | PASS 0 | PASS +345 | **PASS +345** |

**Then isolate the P4 column and show the single line of law that moves it:**
```yaml
# India                                  # United States
effect: permit                           effect: oblige
approval_delay_min: 120                  # standing trigger — fires on the event
```
**Caption:** *Nothing changed but the legal construction.*

**Then the Bangladesh cell — this is the subtlest finding, give it 10 s:**
> Bangladesh fails P4 too, but for a **different reason**.
> Sites went down in Balasore. **Only the operator knew.**
> Under both packs, only the authority can trigger roaming — and nothing told it.
> That is a **coordination** gap, not a policy one.
> A single all-seeing agent could never have produced it.

**Register summary:** **11 gaps** — 4 reproduced by a replayable run, 7 read from the
instruments. By type: **policy 7 · coordination 2 · standards 1 · execution 1.**
Every row carries an Indian clause, a neighbour, and a global example.

---

## Scene 7 — Audit (5:00–5:40) · criterion: **Auditability**

**Animate the five-step trace expanding from one clicked action:**
```
what the agent could see  →  what it proposed + why  →  which rule decided
     →  the verbatim clause + hash + gazette URL  →  what changed in the world
```

**Then the tamper demo. Run it live, on screen:**
```
1. verify the original     : OK   928 entries, head d6577e52…
2. changed one VERDICT from BLOCK to ALLOW
3. verify the altered copy : FAIL payload tampered at seq 45: hash mismatch
   the original is untouched and still verifies.
```
**Caption:** `hash = sha256(prev | seq | t | kind | canonical_json(payload))` — one character,
and the chain names the broken entry.

---

## Scene 8 — ITU alignment (5:40–6:10)

**Y.3172 pipeline — animate the seven nodes lighting in order:**
```
SRC → C → PP → M → P → D → SINK
```
**Caption:** generated from the `@node` decorators in the source, so the map cannot drift
from the code.

**AI Readiness 2.0 — all 13 ITU dimensions, 9 claimed / 4 explicitly not.**
Primary: **D10** AI & Policies · **D4** Contextualization · **D3** Cross-Domain · **D8**
Collaboration with AI · **D11** AI for Inclusion.

**The correction beat:**
> An earlier draft of our proposal called **D1 "Open Source."**
> ITU's own `dimensions.json` says D1 is **"Data/Model Marketplace."**
> Open source is a *factor*, not a dimension.
> We read the labels from their file instead of retyping them. That is how we caught it.

---

## Scene 9 — Limits, then close (6:10–7:00)

**Do not rush this. Put it on screen in full.**

| What | Status |
|---|---|
| IMD timeline, warned districts, landfall | **real** |
| Legal text | **110 of 157 records real; 47 labelled summaries** |
| Per-cell network state | **synthetic**, scaled from COAI aggregates |
| Property thresholds | **illustrative** — cells, minutes, percentages. No money, no casualties |
| LLM agent tier | wired, **never measured against a live model** |

**The weakest joint, said out loud:**
> Three findings rest on a claim that an instrument is **silent** on something.
> **P2 depends on one of them.**
> Proving a silence needs the full notified text — and what we hold is secondary reporting.
> That is why the gap register's `confidence` column is **computed from clause provenance**,
> and why **all 11 rows read `likely`, not `certain`.**

**Final card:**
```
157 clauses · 11 gaps · 3 legal regimes · 501 ticks · 0.55 s · 0 tokens
140 tests · 16/18 rubric checks PASS, 2 waived with reasons, 0 FAIL

python scripts/showcase.py
```

---

## Numbers an animator may need, all in one place

```
CLAUSES        157 total · 110 real (70.1%) · 106 gazette_pdf · 4 subsection
               · 18 secondary_source · 29 model_written
ACTS           Telecom Act 2023 = 62 sections · DPDP Act 2023 = 44 sections
SCENARIO       15 events (7 IMD, 8 constructed) · 9 districts · 224 cells
               · horizon 7500 min · 15-min ticks · landfall T+6285 = 104.75 h
RUN            501 ticks/pack · 0.551 s for all three · 0 LLM calls · 0 tokens
GAPS           11 (4 simulation, 7 document) · policy 7, coordination 2,
               standards 1, execution 1 · confidence: 11 likely, 0 certain
RETRIEVAL      bm25 r@5 .979 MRR .907 sep .921 | vector .979 / .894 / .921
               | hybrid .979 / .908 / .956  ← best | tree .312 / .299 / .792
LEDGER         928 entries (India run) · 11/11 ledgers verify · tamper caught at seq 45
TESTS          140 passed · ruff clean · UI 5 tabs, 0 exceptions
RUBRIC         16 PASS · 2 WAIVED (with printed reasons) · 0 FAIL  of 18
URLS           26 reachable · 2 blocked (bot protection) · 2 timeout · 0 dead
```

## Three things the animation must not do

1. **Do not show a harm number.** There are none. Margins are in cells, minutes and
   percentages, and saying otherwise invents a claim the system does not make.
2. **Do not render the constructed events in the same style as the IMD ones.** Grey italic,
   always, with the caption. This is the single most important honesty cue in the piece.
3. **Do not imply an LLM is driving the decisions.** It is not. Zero LLM calls in every result
   shown. The intelligence is in the encoding and the search, and the engine is provably
   model-free.
