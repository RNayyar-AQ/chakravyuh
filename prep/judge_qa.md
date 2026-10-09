# Judge Q&A prep

Answers to the questions a judge is most likely to ask. Every answer names the file that backs
it. Where the honest answer is "we don't know" or "that's synthetic", it says so — a demo that
oversells one layer loses the credibility of the layers that are solid.

---

## "Is the network data real?"

**No, and it cannot be.** No public dataset records cell-site-level outage for any Indian
cyclone. The per-cell state in this simulator is synthetic, scaled from reported aggregates:
~8,500 towers / ~36,000 base stations in the affected districts and 65–70 % capacity on day 3
(COAI via Deccan Herald), with Bangladesh cross-border figures from Remal 2024 (BTRC via Dhaka
Tribune). Those eight constructed events are flagged `synthetic: true` in the scenario and are
**greyed in the UI's timeline** so they cannot be mistaken for history.

What *is* real: the IMD timeline (every `t_minutes` computed from the RSMC press release's own
IST timestamps — landfall lands at T+6285 min = 104.75 h, matching the release), the warned
districts, and the legal text.

- `data/scenarios/amphan_2020.yaml` (header separates REAL from SYNTHETIC)
- `docs/rubric_status.md` check B1

## "Where do the harm numbers come from?"

There are none. We report **property violations and signed margins in illustrative units** —
cells, minutes, percentages. No money, no casualties, no confidence intervals. P3's −7140
means an area went 7140 minutes past its own alerting deadline; it does not mean anyone was
harmed, and the thresholds (`t_alert_min`, `t_roam_min`) are configurable illustrations, not
legal or engineering standards.

Accuracy is also not a scoring criterion for this event, so we have added no accuracy claims.

- `chakravyuh/fuzz/properties.py`, `out/demo_report.md` ("Limits (read first)")

## "Why multi-agent? Isn't one model simpler?"

Because the brief requires different mandates and uneven information, and because a single
agent cannot *have* a coordination failure. Six role-bound agents only **propose**; a
deterministic Game Master resolves every proposal against one world state, so there are never
two conflicting worlds. The policy engine is a pure function with no model in it — enforced by
an import-graph test, not by convention.

The design earns its keep: the Bangladesh P4 failure is a **coordination** gap, not a policy
one. Sites went down in Balasore and only the operator knew; under both the Indian and the
Bangladeshi pack only the authority can trigger roaming, and nothing told it. A single agent
with full observability could not have produced that finding.

- `chakravyuh/sim/game_master.py`, `chakravyuh/policy/engine.py`
- `docs/rubric_status.md` check B5 (engine imports nothing from `llm/`)

## "How much of your legal text is actually verbatim?"

**110 of 157 clause records (70 %)** carry the instrument's own words, split section-by-section
from the official eGazette PDFs — the Telecommunications Act 2023 (62 sections) and the DPDP Act
2023 (44), both counts matching the Acts. Each carries its page, a SHA-256 of the text and a
SHA-256 of the source PDF, so the document stays pinned even if the link rots.

The remaining **47 are summaries**: 18 attributed to a named secondary source, 29 model-written.
They are labelled `provenance` and `verbatim_status` in every layer, excluded from `quotable`,
and listed in priority order for collection. We do not paraphrase a rule from memory and present
it as text.

- `out/kb_report.md`, `data/sources/CLAUSES_PROVENANCE.md`

## "What did verifying the text actually catch?"

Three things worth naming:

1. **`IN.TA2023.s24` was cited for a priority-routing obligation. Real s.24 is "Establishment
   of Digital Bharat Nidhi"** — the USO fund, which says nothing about routing. The Act's only
   priority-routing provision is **s.20(1)(b)**. A regression test now keeps s.24 out of that
   rule.
2. **Zero of the Act's 62 sections mention roaming.** P4's "no standing trigger" finding is
   therefore evidenced by absence in the full text, not assumed.
3. A claimed **"3-hour takedown under the IT Amendment Rules 2026" was dropped**: the ITU file
   said to support it is a one-page MeitY notice about a different draft.

## "What's the weakest part of this?"

Three findings rest on **negative records** — a claim that an instrument is *silent* on
something. `IN.TCSR2024.no_order_auth` is one of them and **property P2 depends on it**.
Proving a silence needs the full notified text, and what we hold is secondary reporting plus our
reading of it. That is why the gap register's `confidence` column is **computed from clause
provenance** and why all 11 rows currently read `likely`, not `certain`.

The other honest limits: the network layer is permanently synthetic; LLM agent behaviour has
never been measured against a live model (the demo runs the deterministic twins); and the
Adviser eval's C2/C3 criteria are unjudged with the `human_check` column deliberately empty.

- `out/gap_register.md` ("What would raise confidence")

## "Why does the retrieval eval look saturated?"

Because it is, on recall@5 — four of five modes tie at 0.979 over 48 questions, and on 157
lexically distinctive clauses that metric has almost no room to discriminate. We report it
anyway and say so.

The column that *does* discriminate is **abstention separability**: hybrid RRF reaches 0.956
against BM25's and vector's 0.921, measured over five questions whose honest answer is that the
KB cannot say. Each of those five asks about something the gap register records as genuinely
absent — battery backup, restoration deadlines, Tampere party status, EU EECC Art. 110,
per-cell outage data. That is the real reason to prefer hybrid here, and recall@5 hides it
completely.

- `out/retrieval_eval.md`

## "How is this reusable for the 2027 multi-country exercise?"

A jurisdiction is **source documents + one YAML pack** over the same clause schema. Nothing in
the engine knows about India. Adding a country means adding its instruments to the clause store
and writing a pack whose rules cite them; the same scenario and seed then replay under it and
the comparison table grows a column. Three packs already exercise exactly that path, and one of
them (`fcc_mdri`) is a different legal family entirely.

- `data/packs/*.yaml`, `chakravyuh/policy/compiler.py`, `out/comparison.json`

## "What did you find that's new?"

Lead with two:

- **G1 / P4 — no standing roaming trigger.** Same scenario, same seed, three regimes: under
  47 CFR 4.17 roaming is a standing obligation on a provider whose network is impaired and the
  property passes at +345 min. Under the Indian and Bangladeshi packs it must be requested, and
  both fail at −855 min. The difference is the legal construction, nothing else.
- **G3 / P2 — orders are not authenticated.** A forged suspension direction executes exactly
  like a genuine one, and the irreversible act is complete before any verification occurs.
  ITU-T Q.3057/Q.3062/Q.3063 standardise certificate-based authentication of calling *identity*;
  there is no equivalent for an emergency *order*. That is a standards gap with an owner:
  ITU-T SG11 and SG17.

## "Can I break it?"

Yes, please. Two live demonstrations:

```bash
# 1. The ledger cannot be edited without detection.
python scripts/verify_ledger.py --tamper-demo runs/amphan_2020__india_current__rule__seed0.jsonl

# 2. The same seed replays to the same head hash, every time.
python scripts/run_demo.py --seed 0 && python scripts/verify_ledger.py --all
```

The tamper demo copies a verified ledger, flips one `BLOCK` to `ALLOW`, and the chain names the
broken `seq`. The original is never touched and still verifies.

## "What if the Wi-Fi dies?"

Everything in the demo runs offline. The agent twins and the policy engine need no model at
all; the Adviser runs extractively, or from the replay cache, or on local Ollama
`qwen2.5:14b` (the ITU reference stack). No API key is required for any part of the demo path.

- `README.md` § API keys, `chakravyuh/llm/client.py`
