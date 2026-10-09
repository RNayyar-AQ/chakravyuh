# `data/sources/INTL/` — primary source files fetched from their publisher

| File | What it is | Fetched from | Fetched on |
|---|---|---|---|
| `02_ITU_AI_Readiness_dimensions.json` | ITU AI Readiness 2.0 framework: 6 factors, the dimension list with ids, names, short names, descriptions, mapped factors and metrics | `https://raw.githubusercontent.com/CrashingGuru/ITUAIReadiness/main/simulation/data/framework/dimensions.json` | 2026-10-09 |

`dimensions.json` declares `"framework_version": "2.0"` and
`"framework_source": "ITU AI Ready - Analysis Towards a Standardized Readiness Framework,
Report 2.0, January 2026"`.

**Why the file is committed rather than the labels retyped.** `scripts/gen_ai_readiness_map.py`
reads every dimension name out of this file at generation time. Retyping a label is how
"D1 = Open Source" got into an earlier draft of our own proposal; the file says
`"id": 1, "name": "Data/Model Marketplace"`, and open source is a *factor*
(`"id": "opensource"`), not a dimension. The map cannot drift from ITU's labels because it
never contains a label we wrote.
