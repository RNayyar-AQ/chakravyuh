#!/usr/bin/env python3
"""Generate docs/ai_readiness_map.md from ITU's own dimensions.json. Y.3172 node: SINK."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DIMENSIONS = Path("data/sources/INTL/02_ITU_AI_Readiness_dimensions.json")
OUT = Path("docs/ai_readiness_map.md")

CLAIMS: dict[int, dict[str, str]] = {
    10: {"rank": "primary",
         "claim": "The whole system is a policy simulator: three jurisdictions' instruments are "
                  "compiled into executable packs and the same cyclone is replayed under each, so "
                  "a policy's effect is measured rather than argued.",
         "evidence": "data/packs/*.yaml, app/chakravyuh/policy/engine.py, outputs/comparison.json"},
    4:  {"rank": "primary",
         "claim": "Contextualised to the actual region and event: real IMD Amphan timings, the "
                  "real warned districts of Odisha and West Bengal, Khulna across the border, and "
                  "alerts that only count when they are in that district's own language.",
         "evidence": "data/scenarios/amphan_2020.yaml, app/chakravyuh/fuzz/properties.py (P3)"},
    3:  {"rank": "primary",
         "claim": "One rulebook spans telecom, disaster management, cyber incident reporting and "
                  "data protection, so a conflict between two regimes surfaces as a verdict "
                  "rather than being filed under a different ministry.",
         "evidence": "data/clauses/clauses.jsonl, docs/kb_report.md"},
    8:  {"rank": "primary",
         "claim": "Agents only propose; deterministic code decides. Irreversible actions return "
                  "NEEDS_HUMAN and wait at a gate that records whether the approval was a human's "
                  "or the batch timer's, per ITU-T Y.3173.",
         "evidence": "app/chakravyuh/sim/game_master.py (HumanGate), app/chakravyuh/policy/engine.py"},
    11: {"rank": "primary",
         "claim": "Inclusion is scored, not asserted: P3 fails if an affected district is alerted "
                  "only in English, and each CAP envelope's info/language is the district's own "
                  "language tag (or-IN, bn-IN, bn-BD across the border).",
         "evidence": "app/chakravyuh/alerts/cap.py, app/chakravyuh/fuzz/properties.py (P3)"},
    13: {"rank": "secondary",
         "claim": "Site power is modelled as the thing that sets outage duration -- battery drain "
                  "runs only while mains power is actually lost -- and the register carries the "
                  "finding that no instrument states a numeric backup requirement.",
         "evidence": "app/chakravyuh/world/dynamics.py, outputs/gap_register.csv (G5)"},
    2:  {"rank": "secondary",
         "claim": "Generated content is handled as an adversary, not a feature: the rumour and the "
                  "forged suspension order are labelled synthetic in the scenario and the forged "
                  "order is what property P2 exists to catch.",
         "evidence": "data/scenarios/amphan_2020.yaml, app/chakravyuh/fuzz/properties.py (P2)"},
    6:  {"rank": "secondary",
         "claim": "The human interface is the audit trail: every action in the UI opens to the "
                  "reasoning, the rule, the clause text, its hash and its gazette URL.",
         "evidence": "app/ui/streamlit_app.py, outputs/audit_sample.jsonl"},
    1:  {"rank": "secondary",
         "claim": "The clause store is a reusable artefact in its own right: one record per "
                  "clause with verbatim text, SHA-256, page and source URL, which is the metadata "
                  "ITU's reference ingest does not record.",
         "evidence": "data/clauses/clauses.jsonl, docs/kb_report.md"},
}

NOT_ADDRESSED: dict[int, str] = {
    5:  "Measures AI's integration into an organisation's workflows. This is a simulator, not a "
        "deployment inside a telecom operator or regulator, so there is no workflow to measure.",
    7:  "Measures alignment with a national AI strategy. We encode telecom and disaster law, not "
        "AI strategy documents, and we hold no text for India's AI strategy.",
    9:  "Measures the effect of AI integration on people in an organisation. Out of scope: no "
        "human subject is involved anywhere in this system.",
    12: "Measures how granularly national priorities are expressed. Not something a simulator "
        "can evidence.",
}


def main() -> int:
    if not DIMENSIONS.exists():
        print(f"missing {DIMENSIONS}; see data/sources/INTL/PROVENANCE.md", file=sys.stderr)
        return 2
    raw = json.loads(DIMENSIONS.read_text(encoding="utf-8"))
    dims = raw["dimensions"]
    factors = {f["id"]: f["name"] for f in raw["factors"]}

    unknown = set(CLAIMS) | set(NOT_ADDRESSED)
    ids = {d["id"] for d in dims}
    if unknown - ids:
        print(f"claims reference dimensions ITU's file does not define: {sorted(unknown - ids)}",
              file=sys.stderr)
        return 1
    uncovered = sorted(ids - unknown)
    if uncovered:
        print(f"dimensions neither claimed nor explained: {uncovered}", file=sys.stderr)
        return 1

    lines = [
        "# ITU AI Readiness 2.0 mapping (generated by app/scripts/gen_ai_readiness_map.py -- do not edit)",
        "",
        f"Framework: **{raw['framework_version']}** — {raw['framework_source']}",
        "",
        "Every dimension id, name, short name and factor below is read at generation time from",
        f"`{DIMENSIONS.as_posix()}`, ITU's own file "
        f"(provenance: `data/sources/INTL/PROVENANCE.md`). The **claim** column is ours and is "
        f"the only authored text in the table.",
        "",
        f"All {len(dims)} dimensions are accounted for: {len(CLAIMS)} claimed "
        f"({sum(1 for c in CLAIMS.values() if c['rank'] == 'primary')} primary), "
        f"{len(NOT_ADDRESSED)} explicitly not addressed.",
        "",
        "## Factors (ITU's labels)",
        "",
        "| Factor id | Name |", "|---|---|",
    ]
    lines += [f"| `{fid}` | {name} |" for fid, name in factors.items()]

    lines += ["", "## Dimensions we address", "",
              "| D | ITU dimension | Factors | Metrics | Rank | Our claim | Evidence |",
              "|---|---|---|---|---|---|---|"]
    by_id = {d["id"]: d for d in dims}
    for did, claim in sorted(CLAIMS.items(), key=lambda kv: (kv[1]["rank"] != "primary", kv[0])):
        d = by_id[did]
        lines.append(
            f"| **D{did}** | {d['name']} (`{d['short_name']}`) "
            f"| {', '.join(d['mapped_factors'])} | {len(d.get('metrics', []))} "
            f"| {claim['rank']} | {claim['claim']} | `{claim['evidence']}` |")

    lines += ["", "## Dimensions we do not address, and why", "",
              "| D | ITU dimension | Why not |", "|---|---|---|"]
    for did, why in sorted(NOT_ADDRESSED.items()):
        d = by_id[did]
        lines.append(f"| D{did} | {d['name']} (`{d['short_name']}`) | {why} |")

    lines += [
        "",
        "## One correction worth recording",
        "",
        "An earlier draft of our own proposal described dimension D1 as *Open Source*. ITU's file",
        "says `\"id\": 1, \"name\": \"Data/Model Marketplace\"`; open source is a **factor**",
        "(`opensource`), which several dimensions map to. Reading the labels from the file instead",
        "of retyping them is what caught it, and is why this document has no hand-typed ITU label",
        "in it at all.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}: {len(dims)} ITU dimensions, {len(CLAIMS)} claimed, "
          f"{len(NOT_ADDRESSED)} not addressed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
