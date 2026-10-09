# CHAKRAVYUH: what real data exists, mapped to the rubric

Prepared 9 Oct 2026. Tags: **[Certain]** checked against the file or official text; **[Likely]** from secondary reporting; **[Gap]** data that does not exist publicly. Say so in the report.

---

## 1. The uncomfortable part first

1. **ITU's own India dataset does not contain the instruments CHAKRAVYUH depends on.** [Certain] `CrashingGuru/Sandbox_Training/Dataset/India` has 18 files: 8 are B6GA (Bharat 6G Alliance) material, 4 are AI governance or LLM-related. It has the Telecom Act 2023 and DPDP Act 2023. It has **none** of these:
   - Temporary Suspension Rules 2024
   - Telecom Cyber Security Rules 2024
   - CERT-In Directions 2022
   - DM Act 2005
   - the DoT disaster SOP
   - any NDMA plan
   - any cyclone or outage data

   Your knowledge base has to add these. That is a real contribution, not padding.
2. **One ITU file is mislabelled.** [Certain] `11_IT_Rules_Amendment_2026_SGI_MeitY.pdf` is a 1-page MeitY **notice dated 30 March 2026** inviting comments on a *different* draft amendment (compliance with Ministry advisories and digital-media oversight). It is **not** the synthetic-content labelling rules. Anything in your proposal citing "IT Amendment Rules 2026, 3-hour takedown" is unsupported by the ITU file. Drop it or source the actual notified SGI rules.
3. **ITU's reference KB for KSA/UAE is partly empty shells.** [Certain] Of 80 HTML "policy" files, 12 contain fewer than 50 words of text. Four KSA files are byte-identical CST website navigation pages, including `5.4_CST_Telecom_Business_Continuity_Regulation.html`. Four UAE files are another identical page. Judges who built this know the gap; a KB that is verifiably real stands out.
4. **ITU's reference ingest is not clause-aware.** [Certain] `ITUAIReadiness/simulation/server/knowledge/ingest.py`:
   - splits text into ~256-word chunks on paragraph boundaries
   - infers country and source type from the filename
   - records no section number, page or hash

   ITU's own India README asks for the opposite ("**Chunk clause-wise for the Acts (10, 11, 15a)** — Indian statute text is section-numbered; preserve section boundaries"). Doing exactly that is the cheapest "KB quality" win available.
5. **The network layer will stay synthetic.** [Gap] There is no public cell-site-level outage dataset for any Indian cyclone, and DoT intra-circle roaming (ICR) activations are announced through press coverage, not published orders. Use real aggregate numbers (§4) to calibrate the simulator, and state plainly that the network is simulated.

---

## 2. Seed KB already built from real files (attached)

`kb_seed/telecom_act_2023.jsonl` (62 sections) and `kb_seed/dpdp_act_2023.jsonl` (44 sections). Both counts match the Acts. [Certain]

- **Built from:** the ITU-provided eGazette PDFs, split at section boundaries.
- **Each record:** `clause_id`, `section`, `page`, `text_verbatim`, `sha256` (of the text) and `source_pdf_sha256`, plus the official URL taken from ITU's own register (§7 of `India_AI_Regulatory_Landscape.md`).
- **Spot checks:**
  - `IN.TA2023.s20`, p.9: "(1) On the occurrence of any public emergency, including disaster management… (b) provide for appropriate mechanism to ensure that messages of a user or group of users authorised for response and recovery during public emergency are routed on priority."
  - `IN.TA2023.s27`, p.11: regulatory sandboxes.
  - `IN.DPDP2023.s7` contains "(h) for taking measures to ensure safety of, or provide assistance or services to, any individual during any disaster, or any breakdown of public order."
- **Known noise:** gazette margin notes ("Amendments to certain Acts.") sometimes leak into the text. Clean before the final submission, or keep and document. The hash still pins exactly what was ingested.

Script: `build_clauses.py <pdf> <id> <name> <url> <out.jsonl>`. Reuse it for every other gazette PDF you download.

---

## 3. Real data, criterion by criterion

### 3.1 Knowledge base quality (completeness, accuracy, structure; retrieval under query)

The shell here cannot reach `.gov.in` sites, so **you download these** and drop them into `Dataset/India/` in the same naming scheme as ITU's (`NN_Title.pdf`).

| # | Instrument | Official source | Status | Why it's needed |
|---|---|---|---|---|
| A | Telecommunications Act 2023 | eGazette 250880.pdf / India Code A2023-44 | **In ITU dataset; clause-split done** [Certain] | s.20 emergency powers and priority routing; s.27 sandbox |
| B | DPDP Act 2023 | eGazette 248045.pdf | **In ITU dataset; clause-split done** [Certain] | s.7(h) disaster processing; s.16 cross-border |
| C | Telecommunications (Temporary Suspension of Services) Rules 2024 | eGazette, notified **22 Nov 2024** | **Missing — download** [Certain it exists] | Content [Likely, SCC Online]: orders by competent authority or a JS-rank officer if not feasible; JS-issued order lapses unless confirmed within 24 h; forwarded to the review committee within 24 h; committee meets within 5 days; max **15 days**; order must state reasons, area, service; published |
| D | Telecommunications (Telecom Cyber Security) Rules 2024 | eGazette, notified **21 Nov 2024** | **Missing — download** | Incident report within **6 h** of awareness; details within **24 h**. **Nothing on authenticating orders** [Likely] → your P2 gap |
| E | CERT-In Directions under IT Act s.70B(6), 28 Apr 2022 | cert-in.org.in | **Missing — download** | 6-hour incident reporting by service providers |
| F | DoT SOP-2020 for Telecommunication Services for responding to Disasters | dated **14 Dec 2020** (5 MB; mirrored on dehradun.nic.in). Earlier editions 2015, 2017 | **Missing — download** [Certain it exists] | National committee chaired by Member (T), circle committees, TSP nodal officers, damage-assessment teams, ICR **via MoUs between TSPs** |
| G | DoT advisory to TSPs, **8 May 2025** | press coverage | **Find the DoT letter** [Likely] | All TSPs to test ICR; ICR activation requests go to the DoT disaster official; keep BTS within 100 km of the border up; EOC connectivity |
| H | DM Act 2005 (Act 53 of 2005) | India Code | **Missing — download** | Defines "disaster" (DPDP s.7(h) refers to it); NDMA/SDMA powers |
| I | National Disaster Management Plan (NDMP) 2019, telecom/communication responsibilities | ndma.gov.in | **Missing — download** | Who issues warnings, who coordinates telecom |
| J | Bangladesh Standing Orders on Disaster (SOD) 2019 | ADRC mirror PDF | **Download; extract pp. 240–246** (PTD, BTRC, BTCL) plus Appendix 3 cyclone signals p. 374 [Certain about the table of contents] | Neighbour pack |
| K | Bhutan SOP for Telecommunication Services during Disaster | tech.gov.bt PDF | **Download** [Certain it exists] | Neighbour pack. **No roaming provision; no numeric timelines; daily reporting only** |
| L | US 47 CFR §4.17 Mandatory Disaster Response Initiative | eCFR / Cornell LII | **Download** [Certain] | Global comparator: roaming under disaster arrangements when triggered by ESF-2/DIRS; mutual aid; **annual roaming tests**; reports within 60 days |
| M | ITU-D Guidelines for National Emergency Telecommunication Plans (2020) | itu.int D-HDB-EMER | **Download** [Certain] | Global benchmark; ITU target that every country has an NETP |
| N | Tampere Convention text + status | UN Treaty Collection, ITU page | **Verify status before encoding** (ITU page: 50 ratifications, Saudi Arabia the latest, 3 June 2025; per-country status not listed there) | Cross-border relief equipment |
| O | ITU-T X.1303 (CAP 1.2); E.106; Q.3057/Q.3062/Q.3063 (CLI authentication) | itu.int/rec | **Cite by number** | Standards mapping and the order-authentication gap |

**Retrieval evidence for this criterion:** write 30 questions against A–M with gold `clause_id`s, then report recall@5 for BM25, the ITU Chroma reference, and a hybrid of the two. That table is the proof of "ability to retrieve relevant policy context under query".

### 3.2 Agent capability during simulated error scenarios

Use a **real event timeline**, not invented ticks. These are the events your injector releases.

**Amphan 2020 (IMD RSMC press release)** [Certain]

| IST | Event (IMD message) | Hours to landfall |
|---|---|---|
| 16 May 08:45 | Pre-cyclone watch | 104 |
| 16 May 20:30 | Cyclone watch | 92 |
| 17 May 08:40 | Cyclone alert (yellow) | 80 |
| 18 May 08:45 | Cyclone warning (orange) | 56 |
| 18 May ~11:30 (06 UTC) | Super cyclonic storm; peak 240–250 km/h, gusting 275 | — |
| 19 May 23:30 | Post-landfall outlook (red) | 17 |
| 20 May 15:30–17:30 | **Landfall**, Sundarbans, ~21.65°N 88.30°E (WB–Bangladesh coast), 155–165 km/h gusting 185 | 0 |
| 20 May | Kolkata Dum Dum 130 km/h; surge up to 4.6 m in N/S 24 Parganas, East Medinipur | — |

Warned districts:
- **Odisha:** Jagatsinghpur, Kendrapara, Bhadrak, Balasore, Mayurbhanj
- **West Bengal:** East/West Medinipur, N/S 24 Parganas, Howrah, Hooghly, Kolkata

The RSMC archive has every advisory and bulletin as a separate dated PDF, which matches the brief's "chunked, progressively released" requirement exactly.

**Alternative backtest: Remal, May 2024.** [Likely] It crossed the same WB–Bangladesh coast and has better Bangladesh-side data (below). RSMC bulletins exist too.

**Real telecom impact numbers (calibrate the simulator; cite as reported):**

| Event | Figure | Source |
|---|---|---|
| Amphan, 22 May 2020 (day 3) | Networks at **65–70%** capacity in Kolkata and N/S 24 Parganas; target 85–90% by 24 May. Area has ~**8,500 towers / ~36,000 base stations**. One operator logged **100 fibre cuts in an hour**. Causes: grid power, fibre cuts, blocked roads | COAI via Deccan Herald [Likely] |
| Amphan, ~24 May 2020 | Network at **85%** capacity | Deccan Herald follow-up [Likely] |
| Remal, Bangladesh, 26–28 May 2024 | **>26,000 towers down** (headline 27,000); **30,000** without grid power; ~3,000 on generators; ~**80%** of sites down in Rangamati, Meherpur, Gopalganj, Madaripur, Barisal, Barguna (BTRC) | Dhaka Tribune [Likely] |
| Remal, Bangladesh | **>55%** of towers dysfunctional; tower batteries last **4–8 h** | The Daily Star [Likely] |

**Real alert format:** SACHET publishes CAP 1.2 feeds [Likely]:
- national feed: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`; state feeds use the same path
- area is a district-level `cap:polygon` in **lat,lon** order (swap to lon,lat for GeoJSON)
- authors include IMD, NDMA, SDMAs, INCOIS

Download 2–3 real IMD CAP XMLs from a browser and use them as templates for the SDMA agent's output.

### 3.3 Policy, strategy and standards gap identification (critical: global + neighbouring examples)

Every gap below rests on a real document. Write each domain-first.

| Gap (domain) | India instance (real) | Neighbour instance (real) | Global example (real) | Rubric hook |
|---|---|---|---|---|
| **No standing disaster-roaming trigger** | SOP-2020: ICR by MoU between TSPs; 2015 DoT permission "15 days" on mutually agreed terms; 2025 advisory: activation *requested* via DoT [Likely] | Bhutan SOP: no roaming provision at all [Certain] | US §4.17: roaming obligation triggered automatically by ESF-2/DIRS activation, plus annual testing [Certain] | P4 |
| **No national emergency telecom plan in practice** | SOP-2020 exists (committees, nodal officers) | Bangladesh: NETS initiative since Sep 2022, no plan two years on, funds unused [Likely, Daily Star] | ITU NETP Guidelines 2020; ITU target that every country has an NETP [Certain] | Coordination |
| **Orders are not cryptographically authenticated** | Suspension Rules: order communicated "electronically" by an SP-rank officer to the nodal officer; Cyber Security Rules: incident reporting but no order authentication [Likely] | — | ITU-T Q.3057/Q.3062/Q.3063 certificate-based CLI authentication shows ITU already standardises signed identity in signalling [Certain]; the analogous mechanism for orders is absent | P2, standards gap |
| **Suspension orders carry no carve-out for response traffic** | Act s.20(1)(b) *enables* priority routing for responders, but the suspension safeguards (s.20(2) + Rules 2024) as reported contain no mandatory carve-out; IFF's analysis of the draft lists none [Likely] | — | EU EECC Art. 110 public warning (verify text before citing) | P1 |
| **Power backup sets the outage clock** | Amphan: grid loss was the main cause [Likely] | Bangladesh: 4–8 h batteries [Likely] | US §4.17 mutual aid and asset sharing [Certain] | Execution |
| **Timelines not numeric** | SOP-2020 numeric timelines: verify | Bhutan SOP: "immediately" and daily reporting only [Certain] | US §4.17: report within 60 days [Certain] | Unclear responsibilities |

### 3.4 Auditability

No external data is needed. Every agent output stores:
- the `clause_id`s it cites, matching §2 records
- the `sha256` of each cited clause
- the IDs of the retrieved chunks
- its reasoning text

The ledger is hash-chained. Real clause hashes are what make "every action traces to a clause" checkable by a judge on the spot.

### 3.5 Alignment with ITU standards

The real documents are already in hand:
- **Y.3172:** `ITUAIReadiness/simulation/server/knowledge/InputDocs/AI_Use_Cases/T-REC-Y.3172-201906-I!!PDF-E.pdf` [Certain]
- **AI Readiness Report 2.0:** `InputDocs/AI_Strategies/AI_Ready_Framework_2025.pdf`
- **AI Readiness dimensions:** `simulation/data/framework/dimensions.json`. Use it directly so the mapping cites ITU's own machine-readable labels.

---

## 4. What does not exist publicly (say this in the report's limits section)

- Cell-site-level outage logs for any Indian cyclone. Only operator or COAI aggregates exist.
- DoT ICR activation orders as documents. Activations appear in press and PIB coverage.
- A central public register of suspension orders with reasons, despite the publication requirement. Third-party trackers (SFLC.in) exist.
- Real forged-order incidents. The forged-order scenario is a constructed adversarial test, not a historical replay.

---

## 5. Tonight's collection list (in this order)

1. Suspension Rules 2024 (eGazette, 22 Nov 2024)
2. Telecom Cyber Security Rules 2024 (eGazette, 21 Nov 2024)
3. DoT SOP-2020 for Telecommunication Services for responding to Disasters (14 Dec 2020)
4. CERT-In Directions, 28 Apr 2022
5. Amphan RSMC press release plus 6–8 dated bulletins (one per message level)
6. Bangladesh SOD 2019, pp. 240–246 and p. 374
7. US 47 CFR §4.17
8. Bhutan telecom disaster SOP
9. ITU NETP Guidelines 2020

Run `build_clauses.py` on each Act or Rules PDF. For the SOPs and SOD, split on their own numbered headings. Then re-run retrieval eval.

---

## Sources
- ITU Sandbox dataset (India/KSA/UAE): https://github.com/CrashingGuru/Sandbox_Training
- ITU reference simulation + ingest code: https://github.com/CrashingGuru/ITUAIReadiness
- Build-a-thon 5.0 brief: https://aiforgood.itu.int/event/build-a-thon-5-0-creating-innovative-agents-in-5g/
- Suspension Rules 2024 (SCC Online): https://www.scconline.com/blog/post/2024/11/25/government-notifies-telecommunications-temporary-suspension-of-services-rules
- Telecom Cyber Security Rules 2024 (SCC Online): https://scconline.com/blog/?p=335732
- PRS review of draft rules: https://prsindia.org/billtrack/prs-products/rules-and-regulations-review-1732267200
- IFF analysis of draft suspension rules: https://internetfreedom.in/telecom-suspension-rules-2024-analysis/
- DoT SOP-2020 (district mirror): https://dehradun.nic.in/document/standard-operating-proceduresop-2020-for-telecommunications-services-for-responding-to-disasters/
- SOP-2020 summary: https://journalsofindia.com/standard-operating-procedure-released-for-providing-telecommunication-services-during-disasters/
- SOP-2020 coverage (Communications Today): https://www.communicationstoday.co.in/dot-issues-updated-sop-2020-in-disaster-response/
- DoT 2015 ICR permission: https://tele.net.in/dot-permits-intra-circle-roaming-facilities-by-operators-for-15-days-in-disaster-affected-areas/
- DoT May 2025 advisory: https://www.angelone.in/news/market-updates/govt-directs-telcos-disaster-preparedness-network-security
- IMD Amphan press release: https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_d7b2af_press%20release%20amphan.pdf
- COAI Amphan capacity: https://www.deccanherald.com/amp/story/india%2Fcyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844.html
- Amphan 85% capacity: https://www.deccanherald.com/amp/story/india%2Ftelecom-network-working-at-85-capacity-in-amphan-hit-areas-of-west-bengal-841824.html
- Remal Bangladesh towers: https://www.dhakatribune.com/amp/bangladesh/347696/cyclone-remal-27-000-cell-phone-towers-down
- Bangladesh NETS gap: https://www.thedailystar.net/news/bangladesh/news/mobile-service-during-disasters-no-contingency-system-despite-available-funds-3686476
- Bangladesh SOD 2019: https://www.adrc.asia/documents/dm_information/BGD_SOD2019_English_FINAL.pdf
- Bhutan telecom disaster SOP: https://tech.gov.bt/wp-content/uploads/2024/09/Final-SoP-for-Telecom-service-during-Disaster.pdf
- US 47 CFR 4.17: https://www.law.cornell.edu/cfr/text/47/4.17
- ITU NETP Guidelines: https://www.itu.int/pub/D-HDB-EMER
- Tampere Convention (ITU): https://www.itu.int/en/ITU-D/Emergency-Telecommunications/Pages/TampereConvention.aspx
- CAP in India (SACHET feeds): https://thejeshgn.com/2025/05/28/common-alerting-protocol-cap-in-the-indian-context/
- ITU certificate-based CLI authentication: https://www.itu.int/hub/2025/11/secure-telephone-networks-combating-fraud-using-digital-certificates/
