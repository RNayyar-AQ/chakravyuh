# CHAKRAVYUH: Rubric Showcase Runbook (for Claude Code)

> **Context for the agent.** This repo already implements `CHAKRAVYUH_IMPLEMENTATION.md`. This file does **not** add features. It makes every rubric criterion **visibly provable** in the demo, the report and the repo, using **real data only**.
> Event: ITU AI for Good Sandbox Build-a-thon 5.0, New Delhi, 10 Oct 2026.
> Work through the phases in order. After each phase, append results to `docs/rubric_status.md`.

---

## 0. Ground rules (read first, never violate)

1. **No invented legal text.** Every clause in the KB must come from a source file in `data/sources/` and carry `sha256` + `source_url` + `page`. If a source file is missing, mark dependent rules `status: PENDING_SOURCE`, exclude them from the demo, and list them in `docs/rubric_status.md`. Do **not** paraphrase a rule from memory.
2. **Corrections already known. Apply them everywhere (code, packs, README, report):**
   - DPDP disaster-time processing is **s.7(h)**, not 7(g). 7(g) covers epidemics.
   - Do **not** cite "IT Amendment Rules 2026, 3-hour takedown". ITU's file `11_IT_Rules_Amendment_2026_SGI_MeitY.pdf` is a 1-page MeitY **notice dated 30 Mar 2026** about a different draft (compliance with Ministry advisories). Cite it only as what it is, or not at all.
   - AI Readiness dimension **D1 = Data/model Marketplace**. Open source is a *factor*, not D1.
   - Tampere Convention party status per country: unverified. Do not encode it unless the user supplies the UN Treaty Collection page.
3. **Network layer = simulated, calibrated to real aggregates.** Label it so in the UI and the report.
4. **Demo runs in replay mode** (LLM cache) so it is identical and works offline.
5. Accuracy is **not** a scoring criterion (UAE sister-hackathon FAQ). Don't add accuracy claims or confidence intervals.

---

## Phase 1: Audit what exists (30 min)

Create `scripts/rubric_audit.py` that checks and prints PASS/FAIL for each line below, then writes `docs/rubric_status.md`.

| ID | Check | Criterion |
|---|---|---|
| A1 | `data/clauses/clauses.sqlite` exists; every row has non-empty `text_verbatim`, `sha256`, `source_url`, `page` | KB |
| A2 | Re-hashing every `text_verbatim` reproduces its stored `sha256` | KB / Audit |
| A3 | Every `Rule.clause_ids` in `data/packs/*.yaml` resolves to a clause row; no rule uses an ID with status `PENDING_SOURCE` in a demo run | KB |
| A4 | Chroma collection built via the ITU reference ingest (`kb_main`) has > 0 chunks from India sources | KB / ITU alignment |
| A5 | `data/eval/retrieval_qa.jsonl` has ≥ 30 rows, each with ≥ 1 gold `clause_id` that exists | KB |
| A6 | `scripts/eval_retrieval.py` outputs a table with recall@5 + MRR for ≥ 3 retrievers | KB |
| B1 | `data/scenarios/amphan_2020.yaml` exists with events from §2.3 (real IMD times) | Agent capability |
| B2 | Events have per-role `visible_to` and `delay_by_role`; ≥ 1 event reaches two roles at different times | Agent capability (brief: chunked, uneven) |
| B3 | Adviser answers mid-run and every cited `clause_id` ∈ retrieved set ∩ clause store | Agent capability |
| B4 | Forged-order event exists (`authentic: false`) and the run log shows the Game Master verdict on it | Agent capability / Gap |
| B5 | `policy/engine.py` imports nothing from `llm/` (test exists and passes) | Audit |
| C1 | `outputs/gap_register.csv` exists with columns in §4; ≥ 5 rows; every row has India + neighbour-or-"none found" + global example + evidence run ID or doc citation | Gap |
| D1 | Ledger hash chain verifies; tamper test fails as expected | Audit |
| D2 | Every `PROPOSAL` ledger entry has `reasoning`, `cited_rule_ids`, `cited_clause_ids`; every LLM call has an `LLM_TRACE` entry | Audit |
| E1 | `docs/y3172_map.md` is generated from code (`@node` decorators), covering SRC, C, PP, M, P, D, SINK | ITU alignment |
| E2 | `docs/ai_readiness_map.md` uses labels read from ITU's `dimensions.json` (§6) | ITU alignment |
| E3 | README has the 8-perspective table (§6) | ITU alignment |

Then fix FAILs in phase order below. Do not start Phase 7 until A1–E3 are PASS or explicitly waived in `rubric_status.md` with a reason.

---

## Phase 2: Knowledge base quality (real data)

### 2.1 Source files: user places these in `data/sources/IN/`, `data/sources/BD/`, `data/sources/BT/`, `data/sources/US/`, `data/sources/INTL/`

Already in ITU's Sandbox repo (`CrashingGuru/Sandbox_Training/Dataset/India`):
- `15a_Telecommunications_Act_2023_Egazette.pdf`, source `https://egazette.gov.in/WriteReadData/2023/250880.pdf`
- `10_DPDP_Act_2023_Egazette.pdf`, source `https://egazette.gov.in/WriteReadData/2023/248045.pdf`
- `12_TRAI_Recommendations_AI_BigData_Telecom_2023.pdf`
- `01_IndiaAI_Governance_Guidelines_MeitY_Nov2025.pdf`

To download (the user does this in a browser; the agent must not fabricate them):

| File name to save as | What | Where |
|---|---|---|
| `IN/20_Telecom_Temporary_Suspension_Rules_2024.pdf` | Telecommunications (Temporary Suspension of Services) Rules, 2024 (notified 22 Nov 2024) | eGazette / dot.gov.in |
| `IN/21_Telecom_Cyber_Security_Rules_2024.pdf` | Telecommunications (Telecom Cyber Security) Rules, 2024 (notified 21 Nov 2024) | eGazette / dot.gov.in |
| `IN/22_DoT_SOP_2020_Telecom_Disasters.pdf` | DoT SOP-2020 for Telecommunication Services for responding to Disasters (14 Dec 2020) | dot.gov.in/disaster-management or dehradun.nic.in mirror |
| `IN/23_CERT-In_Directions_28Apr2022.pdf` | CERT-In Directions under IT Act s.70B(6) | cert-in.org.in |
| `IN/24_DM_Act_2005.pdf` | Disaster Management Act, 2005 | indiacode.nic.in |
| `IN/25_IMD_Amphan_PressRelease_2020.pdf` | RSMC press release on Amphan | `https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_d7b2af_press%20release%20amphan.pdf` |
| `BD/01_Bangladesh_SOD_2019.pdf` | Standing Orders on Disaster 2019 (use pp. 240–246 PTD/BTRC/BTCL; p. 374 cyclone signals) | `https://www.adrc.asia/documents/dm_information/BGD_SOD2019_English_FINAL.pdf` |
| `BT/01_Bhutan_Telecom_Disaster_SOP.pdf` | Bhutan SOP for Telecom Services during Disaster | `https://tech.gov.bt/wp-content/uploads/2024/09/Final-SoP-for-Telecom-service-during-Disaster.pdf` |
| `US/01_47CFR_4_17_MDRI.html` | 47 CFR §4.17 Mandatory Disaster Response Initiative | `https://www.law.cornell.edu/cfr/text/47/4.17` |
| `INTL/01_ITU_NETP_Guidelines_2020.pdf` | ITU Guidelines for National Emergency Telecommunication Plans | `https://www.itu.int/pub/D-HDB-EMER` |

### 2.2 Build the clause store

- Acts and Rules: split on section/rule numbers. A working splitter exists as `build_clauses.py` (provided alongside this file; it produced 62 sections for the Telecom Act and 44 for DPDP, both matching the Acts). Adapt the regex for Rules (`^\d+\.` rule numbers) and SOPs (numbered headings like `5.2.16`).
- Strip gazette margin notes (e.g. "Amendments to certain Acts.") where they leak into text. Log how many were stripped.
- `clause_id` scheme: `{JUR}.{INSTR}.{s|r|para}{number}`, e.g. `IN.TA2023.s20`, `IN.DPDP2023.s7`, `US.CFR47.4_17`, `BT.TSOP.ch2`.
- Also ingest every source through the **ITU reference ingest** into Chroma `kb_main` (brief requirement), adding metadata `clause_id`, `instrument`, `jurisdiction`, `page`, `sha256` to each chunk. ITU's ingest records none of these; adding them is our visible improvement.

**Spot-check assertions (add as tests):**
- `IN.TA2023.s20` text contains "messages of a user or group of users authorised for response and recovery during public emergency are routed on priority"
- `IN.TA2023.s27` text contains "regulatory sandboxes"
- `IN.DPDP2023.s7` text contains "(h) for taking measures to ensure safety of, or provide assistance or services to, any individual during any disaster"

### 2.3 KB report (demo evidence)

`scripts/kb_report.py` → `docs/kb_report.md`:
- table: instrument | jurisdiction | clauses | % with hash+URL+page (must be 100%) | source file sha256
- count of `PENDING_SOURCE` rules (target 0 for demo packs)
- one paragraph: "ITU reference ingest chunks at ~256 words with no section metadata; we add clause-level records with verbatim text and hashes, as ITU's own India README recommends ('chunk clause-wise for the Acts')."

### 2.4 Retrieval eval (demo evidence)

- Write 30 questions in `data/eval/retrieval_qa.jsonl`, each with gold `clause_id`s, **taken from the actual text**. Examples:
  - "Who may take temporary possession of a telecom network during a public emergency?" → `IN.TA2023.s20`
  - "Can personal data be processed without consent during a disaster?" → `IN.DPDP2023.s7`
  - "What triggers roaming obligations for US wireless providers in a disaster?" → `US.CFR47.4_17`
  - "Does Bhutan's telecom disaster SOP require roaming?" → `BT.TSOP.*` (expected answer: no provision found)
  - include ≥ 3 questions whose honest answer is "not in the KB" (tests abstention)
- Run BM25 | ITU Chroma vector | hybrid RRF (+ rerank if time). Output `docs/retrieval_eval.md` with recall@5, MRR, abstention correctness.

**Demo moment (KB, ~60 s):** open `kb_report.md`, then click one clause in the UI and show text, page, hash and the official URL side by side. Say: *"Every answer the system gives points to a clause you can check against the gazette in one click."*

---

## Phase 3: Agent capability in simulated error scenarios

### 3.1 Real scenario file `data/scenarios/amphan_2020.yaml`

Use these **real** IMD times (source: IMD RSMC Amphan press release). Times IST, `t_minutes` relative to 16 May 2020 08:45.

| event_id | IST | type | content (from IMD) | visible_to (initial) | delays |
|---|---|---|---|---|---|
| E1 | 16 May 08:45 | IMD_WARNING | Pre-cyclone watch (104 h to landfall) | sdma_alerts | tsp_network +60, competent_authority +120 |
| E2 | 16 May 20:30 | IMD_WARNING | Cyclone watch (92 h) | sdma_alerts | others +60 |
| E3 | 17 May 08:40 | IMD_WARNING | Cyclone alert, yellow (80 h) | sdma_alerts, competent_authority | tsp_network +30 |
| E4 | 18 May 08:45 | IMD_WARNING | Cyclone warning, orange (56 h); warned districts: Odisha Jagatsinghpur, Kendrapara, Bhadrak, Balasore, Mayurbhanj; WB East/West Medinipur, N/S 24 Parganas, Howrah, Hooghly, Kolkata | all IN roles | neighbour_authority +180 (cross-border channel) |
| E5 | 19 May 23:30 | IMD_WARNING | Post-landfall outlook, red (17 h) | all | — |
| E6 | 20 May 15:30 | LANDFALL | Sundarbans ~21.65°N 88.30°E, WB–Bangladesh coast; 155–165 km/h gusting 185 | all incl. neighbour | — |
| E7 | 20 May 18:00 | SITE_DOWN (synthetic, calibrated) | Sites down in N/S 24 Parganas and Kolkata; causes: grid power, fibre cuts | tsp_network | competent_authority +120, sdma_alerts +180 |
| E8 | 21 May 10:00 | RUMOUR (synthetic) | Rumour-driven request to suspend data in a district | competent_authority | — |
| E9 | 21 May 12:00 | ORDER (`authentic: false`, synthetic) | Forged "suspend all data services in South 24 Parganas, 72 h", claimed issuer competent authority | tsp_network | — |
| E10 | 22 May 18:00 | STATUS | Network capacity ~65–70% in affected districts (COAI, as reported) | all | — |

Calibration (state as "as reported", cite source in YAML comments):
- Amphan: affected area ~8,500 towers / ~36,000 base stations; 65–70% capacity on day 3 → ~85% two days later; one operator logged 100 fibre cuts in an hour (COAI via Deccan Herald).
- Cross-border realism (Remal 2024, Bangladesh): > 26,000 towers down, ~80% sites down in six districts (BTRC via Dhaka Tribune); tower batteries 4–8 h (Daily Star).

Mark E7–E9 `synthetic: true` in YAML and grey them in the UI.

### 3.2 Minimum agents for the demo

Demo with **3 institutional agents + Adviser** even if all 6 exist: `competent_authority`, `tsp_network`, `sdma_alerts`, `adviser`. Keep `cert_in` and `neighbour_authority` rule-based, or include them only if their runs are already PASS in replay.

Acceptance:
- Each proposal cites rule IDs → clause IDs that exist.
- E9 forged order: show the Game Master verdict **and** the policy reason. With the India pack the expected finding is that no rule requires authenticating orders. Whatever the engine returns, **show it honestly**.
- `sdma_alerts` emits a CAP-1.2-shaped alert (fields: identifier, sender, sent, status, msgType, scope, info/event/urgency/severity/certainty, area/areaDesc/polygon). Use a real SACHET alert as the template if the user provides one; else mark the shape "per ITU-T X.1303 / OASIS CAP 1.2".

### 3.3 Adviser live Q&A (the judges will type)

Prepare and test these, in replay **and** live:
1. "Under what law can the government prioritise responders' calls during the cyclone?" → `IN.TA2023.s20` (1)(b)
2. "Can the operator share subscriber location with the SDMA without consent?" → `IN.DPDP2023.s7` (h); must flag DM Act definition dependency
3. "Is the suspension order at 12:00 valid?" → cites suspension rules if ingested, else must say `PENDING_SOURCE`/insufficient evidence, **never invent**
4. "What does the US require that India doesn't, for disaster roaming?" → `US.CFR47.4_17`
5. One question with no answer in the KB → must abstain and output `GAP:`

**Demo moment (Agent capability, ~2 min):** play the timeline to E6, pause, let a judge ask the Adviser a question, resume to E9 and show the forged-order verdict.

---

## Phase 4: Gap identification (strongest criterion; brief calls global examples "critical")

Write `outputs/gap_register.csv` with columns:
`gap_id, domain_gap (domain-first wording), india_instance (clause_id or doc), neighbour_instance, global_example, evidence (run_id or doc+page), gap_type (policy|coordination|execution|standards), confidence (certain|likely), itu_hook`

Seed rows (every row rests on a real document; verify each against the downloaded file before marking `certain`):

| gap_id | domain_gap | india_instance | neighbour_instance | global_example | gap_type | itu_hook |
|---|---|---|---|---|---|---|
| G1 | Emergency telecom: no standing, automatically triggered disaster-roaming obligation | DoT SOP-2020: ICR via MoUs between TSPs; 2015 DoT permission "15 days", mutually agreed terms; May 2025 advisory: activation requested via DoT | Bhutan telecom disaster SOP: no roaming provision | US 47 CFR §4.17: roaming under disaster arrangements triggered by ESF-2/DIRS; annual roaming tests; reports within 60 days | policy | ITU NETP Guidelines |
| G2 | Emergency telecom: national emergency telecom plan not operational | SOP-2020 exists (committees, nodal officers) | Bangladesh: NETS initiative since Sep 2022, no plan two years on, funds available (Daily Star) | ITU NETP Guidelines 2020; ITU target: every country with an NETP | coordination | ITU-D |
| G3 | Orders to operators are not cryptographically authenticated | Suspension Rules: order communicated electronically to nodal officer; Telecom Cyber Security Rules: incident reporting, no order authentication (verify in text) | none found | ITU-T Q.3057/Q.3062/Q.3063 standardise certificate-based authentication of calling identity in signalling; no equivalent for emergency orders | standards | ITU-T SG11, SG17 X.509 |
| G4 | Suspension safeguards lack a mandatory carve-out for response/relief traffic | Act s.20(1)(b) enables responder priority; s.20(2) + Rules 2024 safeguards contain no carve-out (verify in Rules text) | none found | verify EU EECC Art. 110 public warning before citing | policy | E.106 emergency preference |
| G5 | Power backup determines outage duration; no numeric backup obligation | Amphan outages driven by grid loss (COAI) | Bangladesh tower batteries 4–8 h (Daily Star) | US §4.17 mutual aid and asset sharing | execution | ITU NETP |
| G6 | Disaster telecom SOPs lack numeric timelines | SOP-2020: verify for numeric deadlines | Bhutan SOP: "immediately" + daily reports only | US §4.17: 60-day reporting; annual tests | policy | — |
| G7 | Cross-border alerting: no defined path for CAP alerts across the WB–Bangladesh border | SACHET CAP feeds are national/state | Bangladesh SOD 2019 cyclone signals (BMD) | ITU-T X.1303 CAP supports multilingual, area-polygon alerts | coordination | X.1303 |

Generate `docs/gap_register.md` from the CSV (no hand-editing). For any gap the simulation reproduces, link the run ID and ledger seq numbers.

**Demo moment (Gap, ~90 s):** show G1 and G3. For G1, the same E6–E10 window under the India pack vs a "standing trigger" variant pack (US-style): show the time to roaming active. For G3, replay E9. Say: *"Every gap names an Indian clause, a neighbour's practice and a global example, as the brief asks."*

---

## Phase 5: Auditability

- `scripts/verify_ledger.py <run>` → OK. Then a tamper demo: copy the ledger, edit one character, re-verify → FAIL with the broken `seq`.
- UI tab **"Why?"**: click any agent action → reasoning text, cited rule IDs, cited clause IDs (with hash), retrieved chunk IDs, model, prompt hash, verdict + rule.
- Export `outputs/audit_sample.jsonl` (first 50 ledger entries of the demo run) for the submission.

**Demo moment (~45 s):** click the forged-order action → full trace → run tamper test live.

---

## Phase 6: Alignment with ITU standards

### 6.1 Y.3172

Generate `docs/y3172_map.md` from `@node` decorators:
SRC (sources + scenario) → C (ITU reference ingest + clause builder) → PP (policy compiler, verbatim/hash check) → M (agents) → P (deterministic policy engine, no LLM) → D (bus + Game Master) → SINK (ledger, gap register, UI).
Note in the doc: ITU's own Y.3172 PDF is in their repo at `ITUAIReadiness/simulation/server/knowledge/InputDocs/AI_Use_Cases/T-REC-Y.3172-201906-I!!PDF-E.pdf`.

### 6.2 AI Readiness 2.0

Read labels from ITU's file `ITUAIReadiness/simulation/data/framework/dimensions.json` (clone `https://github.com/CrashingGuru/ITUAIReadiness`). Do not retype them. Map:
- **D10 AI & Policies** (policy simulation): primary
- **D4** Contextualization and Regional Impact
- **D8** Collaboration with AI (human approval on irreversible actions)
- **D3** Cross-domain Correlation Analysis (telecom × disaster × cyber × data protection)
- **D11** AI for Inclusion (Odia/Bengali alerts, both sides of the border)
- **D13** Digital Infrastructure (power/backup, rule-based fuzz agents for energy)

### 6.3 Brief's 8 perspectives (README table, one line each with the file that proves it)

open data/open source · GenAI content ecosystem (synthetic rumour/forged-order events labelled `synthetic: true`) · contextualisation · cross-domain · human supervision (`NEEDS_HUMAN`) · policy opportunity identification (`gap_register.csv`) · social inclusion · digital infrastructure & energy (tokens and wall time per run in `docs/run_stats.md`).

---

## Phase 7: Demo assets

### 7.1 Live demo flow (7 minutes, matches the optional video limit)

| min | Show | Criterion |
|---|---|---|
| 0:00–0:40 | Problem + one line: "We stress-test disaster telecom policy before the cyclone does." | — |
| 0:40–1:40 | KB report + click-through to a clause with hash and gazette URL; retrieval eval table | KB |
| 1:40–3:40 | Amphan timeline E1→E6 (real IMD times, staggered delivery per agent), Adviser answers a judge question, E9 forged order and verdict | Agent capability |
| 3:40–5:10 | Gap register G1 (India vs standing-trigger pack) and G3 (forged order, Q.3057 link); neighbour + global columns | Gap |
| 5:10–5:55 | "Why?" trace + live ledger tamper test | Audit |
| 5:55–6:35 | Y.3172 map + AI Readiness map from ITU's own dimensions.json | ITU alignment |
| 6:35–7:00 | Limits (synthetic network layer, illustrative thresholds) + next steps (more packs, fuzzing at scale, PoC with DoT) | — |

### 7.2 Fallbacks

- No internet: replay mode + local Chroma.
- LLM failure: replay cache; if a question isn't cached, the Adviser runs on local Ollama `qwen2.5:14b` (ITU reference stack).
- Record the full video tonight as a backup.

### 7.3 Judge Q&A prep (`docs/judge_qa.md`)

- *"Is the network data real?"* No. It's simulated, calibrated to reported aggregates (COAI Amphan, BTRC Remal). The timeline and legal text are real.
- *"Where do harm numbers come from?"* We report property violations and delays, not harm estimates; thresholds are illustrative and configurable.
- *"Why multi-agent?"* The brief requires different mandates and uneven information. Agents only propose; deterministic code decides, so there are no conflicting world states.
- *"How is this reusable for the 2027 multi-country exercise?"* Policy packs are per-jurisdiction YAML over the same clause schema; adding a country means adding sources + a pack.
- *"What did you find that's new?"* Lead with G1 and G3.

---

## Phase 8: Submission checklist

- [ ] GitHub repo public (or essential parts public; README says which)
- [ ] `docs/rubric_status.md` all PASS (or waived with reasons)
- [ ] KB: `data/clauses/*.jsonl` + Chroma export + `docs/kb_report.md` + `docs/retrieval_eval.md`
- [ ] `outputs/gap_register.csv` + `docs/gap_register.md`
- [ ] `outputs/audit_sample.jsonl`, `docs/y3172_map.md`, `docs/ai_readiness_map.md`
- [ ] Technical report ≤ 5 pages. Sections (from the UAE FAQ, same template family): intro; use case; requirements; Y.3172 mapping; AI Readiness 2.0 mapping; requirements mapped to local policies; evaluation scenario (technical + policy); policy/standards gaps
- [ ] Demo video ≤ 7 min
- [ ] Limits paragraph present; corrections in §0 applied everywhere (`grep -ri "7(g)\|3-hour" .` returns nothing relevant)

---

## Sources for citations in the repo
- Build-a-thon 5.0 brief: https://aiforgood.itu.int/event/build-a-thon-5-0-creating-innovative-agents-in-5g/
- UAE AI for Good Lab Hackathon (FAQ, template): https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/
- ITU Sandbox data: https://github.com/CrashingGuru/Sandbox_Training
- ITU reference code + dimensions.json: https://github.com/CrashingGuru/ITUAIReadiness
- IMD Amphan press release: https://rsmcnewdelhi.imd.gov.in/uploads/archive/21/21_d7b2af_press%20release%20amphan.pdf
- COAI Amphan capacity: https://www.deccanherald.com/amp/story/india%2Fcyclone-amphan-telecom-networks-operating-at-65-70-capacity-in-affected-districts-says-coai-840844.html
- Remal Bangladesh towers: https://www.dhakatribune.com/amp/bangladesh/347696/cyclone-remal-27-000-cell-phone-towers-down
- Bangladesh NETS gap: https://www.thedailystar.net/news/bangladesh/news/mobile-service-during-disasters-no-contingency-system-despite-available-funds-3686476
- Suspension Rules 2024 summary: https://www.scconline.com/blog/post/2024/11/25/government-notifies-telecommunications-temporary-suspension-of-services-rules
- Telecom Cyber Security Rules 2024 summary: https://scconline.com/blog/?p=335732
- DoT SOP-2020: https://dehradun.nic.in/document/standard-operating-proceduresop-2020-for-telecommunications-services-for-responding-to-disasters/
- DoT ICR 2015: https://tele.net.in/dot-permits-intra-circle-roaming-facilities-by-operators-for-15-days-in-disaster-affected-areas/
- DoT advisory May 2025: https://www.angelone.in/news/market-updates/govt-directs-telcos-disaster-preparedness-network-security
- US 47 CFR 4.17: https://www.law.cornell.edu/cfr/text/47/4.17
- Bhutan SOP: https://tech.gov.bt/wp-content/uploads/2024/09/Final-SoP-for-Telecom-service-during-Disaster.pdf
- Bangladesh SOD 2019: https://www.adrc.asia/documents/dm_information/BGD_SOD2019_English_FINAL.pdf
- ITU NETP Guidelines: https://www.itu.int/pub/D-HDB-EMER
- ITU CLI authentication: https://www.itu.int/hub/2025/11/secure-telephone-networks-combating-fraud-using-digital-certificates/
- SACHET CAP feeds: https://thejeshgn.com/2025/05/28/common-alerting-protocol-cap-in-the-indian-context/
