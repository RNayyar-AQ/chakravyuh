# Live demo flow — 7 minutes

Matches the optional video limit. Every minute has one claim and one artefact that proves it.
Run `python scripts/showcase.py` once before you start: everything below reads generated files,
so nothing has to compute on stage.

| Time | Show | Say | Criterion |
|---|---|---|---|
| **0:00–0:40** | Title slide, then the comparison table in `docs/demo_report.md` | "We stress-test disaster telecom policy before the cyclone does. Same storm, same seed, three legal regimes — and they disagree." | — |
| **0:40–1:40** | `docs/kb_report.md`, then the **Why?** tab: click any action → expand a clause → text, page, SHA-256, gazette URL side by side | "70 % of these records are the Act's own words, split from the official eGazette PDF. Every answer the system gives points to a clause you can check against the gazette in one click. The other 30 % are labelled summaries, and the label is in every layer." | KB |
| **1:40–3:40** | **Timeline** tab: play to landfall. Point at the greyed rows. Let a judge type a question into **Ask the Adviser**. Then show the forged-order verdict. | "Eight of these fifteen events are greyed because we constructed them — no public dataset records cell-site outage for an Indian cyclone. The seven black rows are IMD's own bulletins, at IMD's own times. … Now: the order at T+5715 is forged, and watch what the engine does with it." | Agent capability |
| **3:40–5:10** | `docs/gap_register.md`. Lead with **G1/P4** and **G3/P2**. Show the P4 row across the three packs. | "Under 47 CFR 4.17, roaming is a standing obligation on a provider whose network is impaired — passes at +345 minutes. Under the Indian and Bangladeshi packs it has to be requested — both fail at −855. Nothing changed but the legal construction. Every row names an Indian clause, a neighbour's practice and a global example, as the brief asks." | **Gap** |
| **5:10–5:55** | **Why?** tab on the forged order — the full five-step trace. Then run the tamper demo live. | "Reasoning, rule, clause, hash, source URL, and what it changed in the world. And the log cannot be edited: watch." | Audit |
| **5:55–6:35** | `docs/y3172_map.md` and `docs/ai_readiness_map.md` | "The pipeline map is generated from the `@node` decorators in the source, so it cannot drift from the code. The readiness map reads its labels from ITU's own `dimensions.json` — which is how we caught that D1 is the Data/Model Marketplace, not open source." | ITU alignment |
| **6:35–7:00** | `docs/rubric_status.html`, then the limits paragraph | "16 checks pass, two are waived with the reason printed. The network layer is synthetic, the thresholds are illustrative, and three findings rest on a claim that an instrument is silent — which needs the full notified text we don't yet hold. Next: collect those four documents, more neighbour packs, a PoC with DoT." | — |

---

## The one command

```bash
python scripts/showcase.py          # everything, ~4 min
streamlit run app/streamlit_app.py  # the UI the demo drives
```

## The two live moments

Both are safe to run on stage; neither needs a network.

```bash
# The ledger cannot be edited without detection. Names the broken seq.
python scripts/verify_ledger.py --tamper-demo runs/amphan_2020__india_current__rule__seed0.jsonl

# The same seed replays to the same head hash.
python scripts/run_demo.py --seed 0 && python scripts/verify_ledger.py --all
```

## Fallbacks

| If | Then |
|---|---|
| No internet | Everything in the demo path is offline already. The Adviser runs extractively or from the replay cache; the vector index is on disk. |
| ChromaDB missing | Retrieval degrades to BM25 and the eval table says so in its own Note column. Nothing else changes. |
| An LLM question isn't cached | The Adviser falls back to extractive mode — it quotes retrieved clauses and generates nothing. Or point it at local Ollama `qwen2.5:14b`, the ITU reference stack. No API key is needed anywhere. |
| Streamlit won't start | Every number on screen is also in `docs/`: `demo_report.md`, `gap_register.md`, `kb_report.md`, `rubric_status.md`. The demo can be given from the files. |
| A judge asks something unexpected | `docs/judge_qa.md`. |

## What not to oversell

Say these before you are asked — they are the questions a good judge will reach anyway:

- The network layer is **synthetic**, calibrated to reported aggregates. The timeline and the
  legal text are real.
- Property margins are in **illustrative units** — cells, minutes, percentages. No money, no
  casualties, no confidence intervals.
- Three findings rest on **negative records** (an instrument being *silent*), and **P2 depends
  on one of them**. That is why the gap register's `confidence` column reads `likely` on every
  row, and the column is computed from clause provenance rather than asserted.
