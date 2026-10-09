# Limits

Everything this system does not know, in one place. Nothing here is hedging: each item changes
how a specific claim should be read, and the strong claims depend on these being visible.

## 1. The network layer is simulated

| Real | Simulated |
|---|---|
| The IMD timeline — every `t_minutes` computed from the RSMC press release's own IST timestamps. Landfall lands at T+6285 min = **104.75 h**, matching the release. | Per-cell state: which of 224 cells is up, damaged, suspended or out of battery. |
| The warned districts (Odisha and West Bengal lists, and Khulna across the border). | The forged suspension order, the rumour, and all per-role delivery delays. |
| Aggregate impact figures, as reported: ~8,500 towers / ~36,000 base stations in the affected districts, 65–70 % capacity on day 3 (COAI via Deccan Herald); Remal 2024 cross-border figures (BTRC via Dhaka Tribune). | Cell counts per district, scaled from those aggregates. |

**No public dataset records cell-site-level outage for any Indian cyclone.** Eight of the fifteen
scenario events are our construction. They carry `synthetic: true` in the scenario file and are
**greyed in the UI timeline**. The forged order never happened — it is an adversarial test.

## 2. 47 of 157 clause records are summaries, not the instrument's words

| Provenance | Records | What the text is |
|---|---|---|
| `gazette_pdf` | 106 | The Act's own words, section-split from the official eGazette PDF |
| `gazette_pdf_subsection` | 4 | Genuine substrings of the above |
| `secondary_source` | 18 | Summary, attributed to a named source |
| `model_written` | 29 | Summary, nothing checked |

Every record carries its `provenance` and `verbatim_status`; summaries are excluded from
`quotable` and are marked with a `*` wherever the gap register cites them.

**Three primary sources are still missing, and each blocks a finding** — tracked with its
blocking reason in [`data/sources/MANIFEST.yaml`](../data/sources/MANIFEST.yaml):

| Missing document | Blocks |
|---|---|
| **Complete** Telecom Cyber Security Rules 2024 | P2, G3. The only copy obtained is a composite containing rules 4–8 only. Searching it for authentication terms returns 0 hits — a result that is **worthless as evidence of absence**, because most of the instrument is not in the file. |
| Telecom Cyber Security **Amendment** Rules 2025 (G.S.R. 771(E), 22 Oct 2025) | P2, G3. Found by accident inside that composite. Our records describe the 2024 Rules as notified and take no account of this amendment, which concerns directions to suspend a telecommunication identifier. |
| DoT SOP-2020 | P4, G1, G2, G5, G6. Official DoT copy not located; an NIC mirror exists and may be a scan. |

## 3. Three findings rest on an instrument being *silent* — and P2 is one of them

A negative finding is the hardest kind to support, because proving an absence needs the full
text rather than a summary of it. This is enforced, not merely disclosed: the gap register's
`confidence` column is **computed** from the provenance of each row's citations, and a negative
finding cannot reach `certain` even on verified text unless that text is `quotable`.

**All 11 rows currently read `likely`. Not one finding rests entirely on primary text.**

What the real text has already changed: the G3 finding was *"no instrument requires
authentication."* The official Suspension Rules r.4(2) say an order shall be communicated
*"in writing or through a secure electronic communication… by an officer not below the rank of
Superintendent of Police."* So the gap is sharper than the summary suggested — the Rules
specify **who may send** and **how it travels**, but prescribe **no mechanism the receiving
nodal officer can verify**, and `authenticat*` returns 0 hits across the instrument.

Likewise Bhutan's SOP: `roam` occurs **once**, in an equipment capability list on p.11, not as a
provision. The absence claim is true but must be worded as exactly that.

## 4. Units are illustrative

Property margins are in **cells, minutes and percentages**. P3's −7140 means an area went 7140
minutes past its own alerting deadline. It does not mean anyone was harmed.

**No money. No casualties. No confidence intervals. No accuracy claims.** Thresholds
(`t_alert_min`, `t_roam_min`) are configurable illustrations, not legal or engineering standards.
There is no ground truth to calibrate against, so none is claimed.

## 5. The policy packs are encodings, not law

`data/packs/*.yaml` encode **selected clauses for simulation**. They are not legal advice and
not a complete statement of any jurisdiction's law. The comparator packs (`bangladesh`,
`fcc_mdri`) are shaped to isolate specific design differences — counterfactual legal designs,
not summaries of Bangladeshi or US law.

## 6. The LLM tier has never been measured

Every result shown was produced with **zero LLM calls**. The LLM agent tier (`--tier llm`) and
the generative Adviser are wired and traced, but their behaviour has **not** been evaluated
against a live model. We make no claim about how well an LLM plays these roles.

A non-LLM neural model *is* active: ChromaDB's `all-MiniLM-L6-v2` embedder, used for vector
retrieval. It affects ranking only — no legality decision passes through it, because the policy
engine fetches clauses by exact ID from the structured store, never by similarity.

## 7. Evaluation is small, and partly internal

| Set | n | Authored by | Result |
|---|---|---|---|
| Adviser cases | 23 | **us** — internal | 19/23 gold clause recovered; **23/23 never cited a clause outside the retrieved set** |
| Retrieval QA | 53 (48 answerable + 5 abstention) | **us** — internal | best mode `hybrid`: recall@5 0.979, MRR 0.908, abstention separability 0.956 |
| External gold set | **0** | — | **not done.** No outside party has authored questions against this KB. |

recall@5 is **saturated** — four of five modes tie at 0.979, and on 157 lexically distinctive
clauses that metric has almost no room to discriminate. The column that does discriminate is
abstention separability. Treat the table as a smoke test of the retrieval path, not a validated
comparison of methods.

## 8. Known unknowns

- The official dot.gov.in URL for SOP-2020 was not located.
- Whether further amendments to the Telecom Cyber Security Rules exist after October 2025.
- Bangladesh's NETS text is not public; the register records the gap from secondary reporting.
- Tampere Convention **party status per country is never encoded** — we hold no UN Treaty
  Collection page, so the question is answered "the KB cannot say."
- SOD 2019 page ranges for BTRC duties are from secondary memory and unverified against the PDF.
