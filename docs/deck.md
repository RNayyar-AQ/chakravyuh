# Slide 1 — The use case, mapped to Y.3172

## We stress-test disaster-telecom law before the cyclone does.

**Cyclone Amphan, 16–20 May 2020. Nine real districts. Same agents, same seed, same events — only the rulebook changes.**

```mermaid
flowchart LR
  SRC["<b>SRC</b><br/>Gazette PDFs · IMD timeline"] --> C["<b>C</b><br/>Clause ingest"]
  C --> PP["<b>PP</b><br/>Clause store · policy compiler"]
  PP --> M["<b>M</b><br/>6 role-bound agents<br/><i>propose</i>"]
  M --> P["<b>P</b><br/>Policy engine<br/><i>DECIDES — pure function, no model</i>"]
  P --> D["<b>D</b><br/>Game Master<br/>one world, one order"]
  D --> SINK["<b>SINK</b><br/>Hash-chained ledger · gap register"]
  style P fill:#ff7a45,color:#fff
  style SINK fill:#2dd4a7,color:#000
```

> **Y.3172's P node is the entire thesis: agents propose, deterministic code decides.**
> 72 registrations across all 7 nodes — generated from `@node` decorators, so the map cannot drift from the code.

---

# Slide 2 — Knowledge base → policy → ITU

**157 clause records · 110 (70%) carry the instrument's own words · 9 sources declared, 6 held and SHA-256 verified**

| Instrument held | Compiled into | ITU hook |
|---|---|---|
| Telecom Act 2023 **s.20** | India suspension powers + relief carve-out test | **E.106** · ITU Const. Art. 40 |
| Suspension Rules 2024 **r.3** | Who may order, how it reaches the operator | **Q.3057/62/63** |
| DM Act 2005 · NDMA SACHET | Alerting authority + language duty | **X.1303 / CAP 1.2** |
| BTRA 2001 + DM Act 2012 + CPP | Bangladesh pack | ITU-D **NETP 2020** |
| 47 CFR 4.17 + FCC DIRS | United States pack | ITU-D **NETP 2020** |

**ITU AI Readiness 2.0 — 5 primary dimensions claimed (labels read from ITU's file, never retyped):**

| D | Dimension | Why |
|---|---|---|
| **D10** | AI & Policies | Three jurisdictions compiled into executable packs; policy effect is *measured*, not argued |
| **D11** | AI for Inclusion | P3 **fails** if a district is alerted only in English (`or-IN`, `bn-IN`, `bn-BD`) |
| **D3** | Cross-Domain Correlation | Telecom × disaster × cyber × data protection in one rulebook |
| **D4** | Contextualization | Real IMD timings, real warned districts, real languages |
| **D8** | Collaboration with AI | Irreversible acts return `NEEDS_HUMAN` — per **Y.3173** |

---

# Slide 3 — How it is evaluated

**One command. Offline. Zero tokens. ~35 seconds.**

1. **Build** the clause store — 157 clauses, chunks, hybrid index
2. **Replay** Amphan under each of the three packs — identical seed, identical events
3. **Check** safety properties **P1–P4** and record a signed margin
4. **Fuzz** — Hypothesis mutates the world **612 times**, hunting violations
5. **Verify** every hash chain, then **deliberately tamper** one byte and prove it is caught

| Safety property | 🇮🇳 India | 🇧🇩 Bangladesh | 🇺🇸 United States |
|---|---|---|---|
| **P1** relief traffic survives a lawful suspension | ❌ **−60** pp | ✅ +40 | ✅ +40 |
| **P2** no forged order causes an irreversible act | ❌ **−1** exec | ✅ 0 | ✅ 0 |
| **P3** every area alerted in time, in a local language | ❌ **never** | ✅ +345 min | ✅ +345 min |
| **P4** disaster roaming active within the deadline | ❌ **never** | ❌ never | ✅ +345 min |

> Same seed → same ledger → same hash. Every number above is re-derivable, not asserted.

---

# Slide 4 — What we found, and what is new

### 🔴 The standards gap (most impactful)
**ITU-T Q.3057 authenticates a *caller*. Nothing authenticates an *order to an operator*.**
A forged suspension direction executes exactly like a genuine one — the irreversible act completes before anyone verifies. *The gap is the absence, not a weaker alternative.* → **ITU-T SG11 / SG17**

### 🟠 The policy gaps
- **No relief carve-out.** s.20(1)(b) *enables* priority routing — it never *obliges* it. A lawful suspension can switch off the response itself.
- **No standing cross-border trigger.** Under India's pack, Khulna is **never** warned:
  `BLOCK — prohibited_by_rule: IN.R.NO_CROSS_BORDER_ALERT`
- **Roaming starts when somebody asks.** US 47 CFR 4.17 triggers on the *event*; India's SOP triggers on a *request*.

### 🟢 The innovations
- **Agents propose, code decides** — Concordia with a Python Game Master, so a run is reproducible
- **Confidence is computed, never asserted** — a finding rises to `certain` only when every clause it cites is primary text
- **The standards map is generated from the code** — delete a function and it leaves the map

> **11 gaps registered — 4 reproduced by a replayable run, 7 read from the instruments.**
> Aligned with and mapped to ITU-T. Not certified, approved or endorsed by the ITU.
