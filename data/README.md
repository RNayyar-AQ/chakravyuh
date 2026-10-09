# `data/` — inputs only

Everything here is an **input**. Nothing in this folder is produced by a run, and nothing a run
produces is kept here. The derived clause store (`data/clauses/`) and the vector index
(`data/chroma/`) are rebuilt from these files by `python app/scripts/build_kb.py` in about four
seconds, byte-identically, and are not committed. We commit sources, not derivatives.

| Path | What it is | Who reads it |
|---|---|---|
| `sources/MANIFEST.yaml` | Every primary source document: official URL, SHA-256, page count, the strings only the real instrument contains, and its verification status | `app/scripts/fetch_sources.py` |
| `sources/IN/telecom_act_2023.jsonl` | **62 sections** of the Telecommunications Act 2023, split from the official eGazette PDF. Verbatim text, page, text hash, source-PDF hash | `app/chakravyuh/kb/real_sources.py` |
| `sources/IN/dpdp_act_2023.jsonl` | **44 sections** of the DPDP Act 2023, same treatment | `app/chakravyuh/kb/real_sources.py` |
| `sources/clause_seed.jsonl` | The 47 records we hold only as summaries, each with a named source URL and `provenance` saying so | `app/chakravyuh/kb/ingest.py` |
| `sources/INTL/02_ITU_AI_Readiness_dimensions.json` | ITU's own framework file. The AI Readiness map is generated from it so no ITU label is ever retyped by us | `app/scripts/gen_ai_readiness_map.py` |
| `sources/CLAUSES_PROVENANCE.md` | Chain of custody: what is verbatim, what is a summary, what each unverified record blocks | — |
| `packs/*.yaml` | The three legal regimes, encoded as executable rules. **Loaded by glob**, so a pack is live the moment it is added | `app/chakravyuh/policy/compiler.py` |
| `scenarios/amphan_2020.yaml` | The real IMD Amphan timeline. Eight constructed events carry `synthetic: true` | `app/chakravyuh/sim/events.py` |
| `scenarios/amphan_like.yaml` | A short synthetic scenario so the test suite runs in 33 s instead of minutes | `tests/conftest.py` |
| `gaps/document_gaps.yaml` | G1–G7: gaps read from the instruments rather than reproduced by a run | `app/chakravyuh/analysis/gap_register.py` |
| `eval/retrieval_qa.jsonl` | 53 questions — 48 answerable with gold clause ids, 5 whose honest answer is that the KB cannot say | `app/scripts/eval_retrieval.py` |
| `eval/adviser_cases.jsonl` | 23 hand-labelled Adviser cases | `app/scripts/eval_adviser.py` |

**Not committed, by design:** the source PDFs themselves (`kb_raw/`). Several have licence terms
we have not cleared, and all are re-fetchable from their official URL with
`python app/scripts/fetch_sources.py`, which checks each one against the hash and the required
strings in `sources/MANIFEST.yaml`. A PDF that downloads is not the same as the right PDF: one
source served a composite of two different instruments, and searching it for an absent term
would have confirmed a false finding.
