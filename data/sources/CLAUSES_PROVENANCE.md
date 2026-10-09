# Clause provenance — read before citing anything

Last updated 9 Oct 2026, after the real gazette corpus landed.

## The corpus is now MIXED. Know which half you are quoting.

| Provenance | Records | `verbatim_status` | What the text is |
|---|---|---|---|
| `gazette_pdf` | 106 | `verified` / `verified_with_artifacts` | **The instrument's own words**, split from the official eGazette PDF |
| `gazette_pdf_subsection` | 4 | same | A genuine substring of the above, for a cited subsection |
| `secondary_source` | 18 | `unverified_summary` | Model-written summary, but the *content claim* is attributed to a named secondary source (SCC Online, eCFR, an ITU page) |
| `model_written` | 29 | `unverified_summary` | Model-written summary, **nothing checked** |
| **Total** | **157** | 70.1% real text, 52.9% quotable | |

`out/kb_report.md` prints these numbers on every build. `out/source_check.md` checks every URL.

## The real half (106 + 4 records)

**Source:** `data/telecom_act_2023.jsonl` (62 sections) and `data/dpdp_act_2023.jsonl` (44 sections),
produced by `data/build_clauses.py` from the eGazette PDFs in ITU's India dataset. Section counts
match the Acts exactly.

Both source URLs were verified to return HTTP 200 with `application/pdf`:
- Telecommunications Act 2023 → <https://egazette.gov.in/WriteReadData/2023/250880.pdf>
- DPDP Act 2023 → <https://egazette.gov.in/WriteReadData/2023/248045.pdf>

**Chain of custody.** Each record carries `page`, `sha256` (of the cleaned text), `sha256_raw`
(of exactly what `pdftotext` produced), and `source_pdf_sha256` — the hash of the PDF itself. The
last one is what pins the document: even if the link rots, the hash identifies precisely which
file produced the text. A test asserts no record can claim real text without it.

**Known artifact: interpolated marginal headings.** The Gazette prints section headings in the
margin, and `pdftotext` reads them into the flow, so a page break inside a section leaves this:

> ...or relating to any particular subject, brought for **Provisions for public emergency or public
> safety.** `[PART II—` transmission by, or transmitted or received by...

Structural debris (`[PART II—`, `CHAPTER VII`, `SEC. 1]`, running heads, marginal statute
references like `53 of 2005.`) **is** removed. The interpolated heading **is not**, deliberately: a
heuristic that lifts "the capitalised phrase before the marker" is right about two-thirds of the
time — it correctly extracts the heading from s.20, but also swallows real statutory text such as
*"Act or the rules made thereunder."* Mangling a statute at 65% accuracy is worse than a visible
artifact, so 27 affected records are flagged `verified_with_artifacts`, carry a
`marginal_note_candidate`, and are **excluded from `quotable`**. Clearing them is a per-record
human task.

## What the real data caught in the old fabricated corpus

This is the strongest argument for having done it.

| Record | Fabricated claim | What the gazette actually says |
|---|---|---|
| `IN.TA2023.s24` | "operator shall establish priority routing for specified users during a public emergency" | **"Establishment of Digital Bharat Nidhi"** — the USO Fund. Nothing about routing. The India pack cited it for a priority-routing obligation; **the rule was wrong and is fixed** to `IN.TA2023.s20.1`. |
| roaming | assumed a licence/Act basis | **Zero of the Act's 62 sections mention roaming.** It rests on the DoT SOP-2020 and licence conditions — which is *why* there is no standing trigger. The P4 finding is now evidenced, not asserted. |
| `IN.TA2023.s20.1` / `.s20.2` | paraphrase | Both now real text. s.20(1)(b) is the only priority-routing provision; s.20(2) is the suspension power. The P1/P2 split turns on this distinction. |
| `IN.DPDP2023.s7.h` | paraphrase, s.7(h) for disaster | **Confirmed correct**, and now quotable real text, with the Explanation pointing at DM Act 2005 s.2(d). |
| `IN.ITRULES.TAKEDOWN` | "3-hour takedown under IT Amendment Rules 2026" | **DROPPED.** The ITU file said to support this is a one-page MeitY notice of 30 Mar 2026 inviting comments on a *different* draft. The claim had nothing behind it. |
| `US.FCC.MDRI.*` | cited an FCC news page | **Renamed** to `US.CFR47.4.17.*`, the MDRI's actual regulatory home. |

## The unverified half (47 records)

Still model-written summaries. Instruments not yet obtained, per
`data/CHAKRAVYUH_REAL_DATA.md` §3.1: Suspension Rules 2024, Telecom Cyber Security Rules 2024,
CERT-In Directions 2022, DM Act 2005, DoT SOP-2020, NDMP 2019, Bangladesh SOD 2019, Bhutan SOP,
47 CFR §4.17, ITU NETP Guidelines, Tampere Convention, the ITU Recommendations.

Nine of these are **negative findings** — records asserting that an instrument is *silent* on
something (`IN.TCSR2024.no_order_auth`, `BT.TELSOP.no_roaming`, `BD.NETS.gap`). Their text says so
explicitly. A negative finding needs the full notified text to confirm, so they are the highest
risk in the corpus and are labelled accordingly.

### Verification priority (descending blast radius)

| # | Records | Why first |
|---|---|---|
| 1 | `IN.SUSP2024.*` (6) | Carry P2, the forged-order finding. Get the eGazette notification of 22 Nov 2024. |
| 2 | `IN.TCSR2024.*` (2) | The **negative finding** that no authentication duty exists. Needs the full notified text of 21 Nov 2024. |
| 3 | `IN.DOTSOP2020.*` (2) | Carry P4. Get SOP-2020 of 14 Dec 2020. |
| 4 | `US.CFR47.4.17.*` (3) | The global comparator. eCFR text is freely available. |
| 5 | `IN.DMA2005.*` (5) | DPDP s.7(h) depends on its definition of "disaster". |
| 6 | `BT.TELSOP.no_roaming`, `BD.*` | Neighbour comparators. |
| 7 | `INTL.TAMPERE1998.*` (3) | Party status for IN/BD unverified; cited for content only. Keep it that way. |

Procedure per record: open the instrument → confirm the section number → paste the exact text →
set `verbatim_status: "verified"`, `provenance: "gazette_pdf"`, record `page` and
`source_pdf_sha256` → leave `sha256` as `""` (recomputed on build) →
`python app/scripts/build_kb.py && python app/scripts/check_sources.py`. If a provision turns out to say
something different, **fix the rule** and re-run `app/scripts/run_demo.py`; the gap register changing
is the system working.

## URLs

`python app/scripts/check_sources.py` checks every URL in the store. Current: **27/31 reachable,
2 blocked (403, bot protection), 2 timed out, 0 dead.** A timeout is not a dead link — curl
resolves both SCC Online URLs with a 301.

One oddity: `https://dot.gov.in/unified-licnse` **resolves**, misspelling and all. That is DoT's
own spelling. Do not "fix" it.

## What results do and do not support

**Supported.** Every number in `out/` is a true statement about the encoded packs, and the India
pack's P1/P2 findings now cite real statutory text for the provisions that exist.

**Not yet supported.** Any claim resting on a `model_written` or `secondary_source` record —
above all the three negative findings. "The Telecom Cyber Security Rules 2024 impose no
authentication duty" is currently *secondary reporting plus a model's reading of it*, not a
confirmed reading of the notified text. Say so, or get the text.

### This is now enforced, not just documented

`app/chakravyuh/analysis/gap_register.py` computes the gap register's `confidence` column from the
provenance of the clauses each row cites. A row is `certain` only when every Indian clause it
cites carries the instrument's own words from a primary source, and `likely` the moment one is a
summary. A **negative finding** — a claim that an instrument is silent — is held one step
further: it cannot reach `certain` even on verified text unless that text is `quotable`, because
a record carrying page-break artefacts cannot establish an absence.

The current result is uniform and worth stating plainly: **all 11 rows read `likely`**. Not one
finding in the register rests entirely on primary text. `docs/gap_register.md` ends with the
starred clause ids that are holding each row back, and a hand-written `confidence` in
`data/gaps/document_gaps.yaml` has no effect — a test asserts the field is absent, because a
declared confidence would silently disagree with the clause store.

## The packs

`data/packs/*.yaml` are encodings of selected clauses **for simulation, not legal advice**, and not
a complete statement of any jurisdiction's law. The comparator packs (`bangladesh`, `fcc_mdri`) are
shaped to isolate specific design differences — counterfactual legal designs, not summaries of
Bangladeshi or US law.
