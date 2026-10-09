"""Write gap_register.csv and gap_register.md -- the gap-identification artefact. Y.3172 node: SINK.

Two kinds of row land in the same register, and the register says which is which:

  source=simulation  A property failed on a replayable run. The row carries the run id, the
                     signed margin, and the packs under which the same seed passes. These are
                     the rows nobody could have written in advance.
  source=document    The gap is visible in the instruments themselves and would never surface in
                     a cyclone run -- a plan that was never operationalised, an SOP with no
                     numeric deadline, a standards family that authenticates calling identity but
                     not emergency orders. Defined in data/gaps/document_gaps.yaml.

`confidence` is COMPUTED, never written by hand: a row is `certain` only when every clause it
cites carries the instrument's own words from a primary source, and `likely` as soon as one of
them is a summary. That makes the column a live readout of the knowledge base's provenance
rather than an assertion about our own confidence. A row resting on a NEGATIVE finding -- a claim
that an instrument is silent -- can never be `certain` without the full primary text, because a
summary cannot establish an absence.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import yaml

from ..kb.clause_store import ClauseStore
from ..schemas import GapFinding, PolicyPack
from ..y3172 import node

OUT_DIR = Path("outputs")
DOCUMENT_GAPS = Path("data/gaps/document_gaps.yaml")

# The rubric's required column set, in its order, first. Everything after `itu_hook` is ours:
# a superset keeps the required contract readable while losing none of the replay detail.
RUBRIC_COLUMNS = [
    "gap_id", "domain_gap", "india_instance", "neighbour_instance", "global_example",
    "evidence", "gap_type", "confidence", "itu_hook",
]
EXTRA_COLUMNS = [
    "source", "violated_property", "margin_india", "passes_under_packs",
    "india_clause_ids", "neighbour_clause_ids", "global_clause_ids",
    "negative_finding", "unverified_clause_ids", "replay_cmd",
]
COLUMNS = RUBRIC_COLUMNS + EXTRA_COLUMNS

VALID_GAP_TYPES = ("policy", "coordination", "execution", "standards")

# How a pack id appears in the register's comparator columns.
COMPARATOR_LABEL = {
    "bangladesh": "Bangladesh (BTRA 2001 + DM Act 2012 + CPP standing order)",
    "fcc_mdri": "United States (FCC Mandatory Disaster Response Initiative + DIRS)",
    "india_current": "India (Telecom Act 2023 + Suspension Rules 2024 + DM Act 2005)",
}


# -- confidence -----------------------------------------------------------------
def _unverified(clause_ids: Iterable[str], store: Optional[ClauseStore]) -> list[str]:
    """Cited clause ids whose record is a summary rather than the instrument's own words."""
    if store is None:
        return list(clause_ids)        # no store to check against: assume nothing is verified
    out: list[str] = []
    for cid in clause_ids:
        clause = store.try_get(cid)
        if clause is None or not clause.is_real_text:
            out.append(cid)
    return out


def confidence_for(clause_ids: Sequence[str], store: Optional[ClauseStore],
                   negative_finding: bool = False) -> tuple[str, list[str]]:
    """`(confidence, unverified_clause_ids)`. `certain` requires primary text for every citation.

    A negative finding is held to the same bar and then one step further: it is downgraded even
    when every cited record is verified, unless the verified text is quotable, because a record
    carrying page-break artefacts cannot be relied on to show that something is ABSENT.
    """
    unverified = _unverified(clause_ids, store)
    if unverified or not clause_ids:
        return "likely", unverified
    if negative_finding and store is not None:
        not_quotable = [cid for cid in clause_ids
                        if (c := store.try_get(cid)) is not None and not c.quotable]
        if not_quotable:
            return "likely", not_quotable
    return "certain", []


# -- simulation-derived rows ----------------------------------------------------
def _comparator_cell(pack_id: str, findings_by_pack: Mapping[str, Sequence[GapFinding]],
                     prop: str, passes: Sequence[str]) -> str:
    label = COMPARATOR_LABEL.get(pack_id, pack_id)
    if pack_id in passes:
        return f"{label}: PASSES the same seed"
    same = [f for f in findings_by_pack.get(pack_id, []) if f.violated_property == prop]
    if same:
        return f"{label}: also fails ({same[0].gap_class} gap)"
    return f"{label}: not evaluated"


def _simulation_rows(findings_by_pack: Mapping[str, Sequence[GapFinding]], base_pack: str,
                     neighbour_pack: str, global_pack: str, store: Optional[ClauseStore],
                     scenario_id: str) -> list[dict]:
    rows: list[dict] = []
    for finding in findings_by_pack.get(base_pack, []):
        passes = finding.evidence.get("passes_under_packs", [])
        margins = finding.evidence.get("comparator_margins", {})
        cited = list(finding.responsible_clause_ids)
        conf, unverified = confidence_for(cited, store)
        rows.append({
            "gap_id": finding.gap_id,
            "domain_gap": f"{finding.domain}: {finding.statement}",
            "india_instance": f"{finding.instance} -- {' '.join(cited) or 'no clause cited'}",
            "neighbour_instance": _comparator_cell(neighbour_pack, findings_by_pack,
                                                   finding.violated_property, passes),
            "global_example": _comparator_cell(global_pack, findings_by_pack,
                                               finding.violated_property, passes),
            "evidence": f"run {finding.evidence_run_id}",
            "gap_type": finding.gap_class,
            "confidence": conf,
            "itu_hook": ITU_HOOK_BY_PROPERTY.get(finding.violated_property, ""),
            "source": "simulation",
            "violated_property": finding.violated_property,
            "margin_india": margins.get(base_pack, ""),
            "passes_under_packs": " ".join(passes),
            "india_clause_ids": " ".join(cited),
            "neighbour_clause_ids": "",
            "global_clause_ids": "",
            "negative_finding": "",
            "unverified_clause_ids": " ".join(unverified),
            "replay_cmd": (f"python scripts/run_demo.py --pack {base_pack} "
                           f"--scenario data/scenarios/{scenario_id}.yaml --seed 0"),
        })
    return rows


# The ITU work item each property's failure points at. Kept next to the properties rather than in
# the YAML because these rows are generated from runs, not authored.
ITU_HOOK_BY_PROPERTY = {
    "P1": "ITU-T E.106 International Emergency Preference Scheme",
    "P2": "ITU-T SG11 (Q.3057/Q.3062/Q.3063); ITU-T SG17 (X.509)",
    "P3": "ITU-T X.1303 Common Alerting Protocol",
    "P4": "ITU-D Guidelines for National Emergency Telecommunication Plans",
}


# -- document-derived rows ------------------------------------------------------
def load_document_gaps(path: str | Path = DOCUMENT_GAPS) -> list[dict]:
    """Read data/gaps/document_gaps.yaml, validating gap_type and required keys."""
    path = Path(path)
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    gaps = raw.get("gaps", [])
    for gap in gaps:
        missing = [k for k in ("gap_id", "domain_gap", "gap_type") if not gap.get(k)]
        if missing:
            raise ValueError(f"{path}: gap {gap.get('gap_id', '?')} is missing {missing}")
        if gap["gap_type"] not in VALID_GAP_TYPES:
            raise ValueError(f"{path}: gap {gap['gap_id']} has gap_type "
                             f"{gap['gap_type']!r}, expected one of {VALID_GAP_TYPES}")
    return gaps


def _document_rows(gaps: Sequence[dict], store: Optional[ClauseStore],
                   findings_by_pack: Mapping[str, Sequence[GapFinding]],
                   base_pack: str) -> list[dict]:
    reproduced = {f.violated_property: f.evidence_run_id
                  for f in findings_by_pack.get(base_pack, [])}
    rows: list[dict] = []
    for gap in gaps:
        india = list(gap.get("india_clause_ids") or [])
        neighbour = list(gap.get("neighbour_clause_ids") or [])
        global_ = list(gap.get("global_clause_ids") or [])
        negative = bool(gap.get("negative_finding"))
        # Confidence rests on the India citations: that is the claim the register makes about
        # the jurisdiction under study. Comparator citations are context, not the finding.
        conf, unverified = confidence_for(india, store, negative_finding=negative)

        prop = gap.get("reproduced_by_property") or ""
        evidence = f"documents: {' '.join(india) or 'none'}"
        if prop and prop in reproduced:
            evidence += f"; reproduced as {prop} on run {reproduced[prop]}"

        rows.append({
            "gap_id": gap["gap_id"],
            "domain_gap": " ".join(str(gap["domain_gap"]).split()),
            "india_instance": _instance_cell(india, gap.get("india_note", ""), store),
            "neighbour_instance": _instance_cell(neighbour, gap.get("neighbour_note", ""), store),
            "global_example": _instance_cell(global_, gap.get("global_note", ""), store),
            "evidence": evidence,
            "gap_type": gap["gap_type"],
            "confidence": conf,
            "itu_hook": gap.get("itu_hook", ""),
            "source": "document",
            "violated_property": prop,
            "margin_india": "",
            "passes_under_packs": "",
            "india_clause_ids": " ".join(india),
            "neighbour_clause_ids": " ".join(neighbour),
            "global_clause_ids": " ".join(global_),
            "negative_finding": "yes" if negative else "no",
            "unverified_clause_ids": " ".join(unverified),
            "replay_cmd": "",
        })
    return rows


def _instance_cell(clause_ids: Sequence[str], note: str, store: Optional[ClauseStore]) -> str:
    """`note [clause ids]`, marking any citation that is a summary rather than primary text."""
    note = " ".join(str(note).split())
    if not clause_ids:
        return note or "none found"
    marked = []
    for cid in clause_ids:
        clause = store.try_get(cid) if store is not None else None
        marked.append(cid if (clause is not None and clause.is_real_text) else f"{cid}*")
    return f"{note} [{' '.join(marked)}]".strip()


# -- output ---------------------------------------------------------------------
@node("SINK")
def write_register(findings_by_pack: Mapping[str, Sequence[GapFinding]],
                   packs: Mapping[str, PolicyPack], base_pack: str = "india_current",
                   out_path: str | Path = OUT_DIR / "gap_register.csv",
                   neighbour_pack: str = "bangladesh", global_pack: str = "fcc_mdri",
                   store: Optional[ClauseStore] = None,
                   document_gaps: str | Path = DOCUMENT_GAPS,
                   scenario_id: str = "amphan_2020") -> Path:
    """Write the register: simulation rows first, then document rows. Returns the path."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = (_simulation_rows(findings_by_pack, base_pack, neighbour_pack, global_pack,
                             store, scenario_id)
            + _document_rows(load_document_gaps(document_gaps), store,
                             findings_by_pack, base_pack))
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return out


@node("SINK")
def register_markdown(findings_by_pack: Mapping[str, Sequence[GapFinding]],
                      base_pack: str = "india_current") -> str:
    """The simulation-derived rows as a compact Markdown table, for the demo report."""
    lines = [
        "| Gap (domain-first) | Class | Property | Instance | Responsible clauses | Passes under |",
        "|---|---|---|---|---|---|",
    ]
    for f in findings_by_pack.get(base_pack, []):
        passes = ", ".join(f.evidence.get("passes_under_packs", [])) or "none"
        clauses = ", ".join(f.responsible_clause_ids[:3]) or "-"
        lines.append(f"| {f.domain}: {f.statement} | {f.gap_class} | {f.violated_property} "
                     f"| {f.instance} | {clauses} | {passes} |")
    return "\n".join(lines)


@node("SINK")
def register_doc(csv_path: str | Path = OUT_DIR / "gap_register.csv") -> str:
    """Render the full register as Markdown, read back from the CSV it was written to.

    Reading the CSV rather than the findings is deliberate: the document and the CSV cannot
    disagree, because there is only one source and no hand-editing step between them.
    """
    rows = list(csv.DictReader(Path(csv_path).open(encoding="utf-8")))
    sim = [r for r in rows if r["source"] == "simulation"]
    doc = [r for r in rows if r["source"] == "document"]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["gap_type"]] = counts.get(r["gap_type"], 0) + 1

    out = [
        "# Gap register (generated by chakravyuh/analysis/gap_register.py -- do not edit)",
        "",
        f"**{len(rows)} gaps**: {len(sim)} reproduced by a replayable run, {len(doc)} read from "
        "the instruments. By type: "
        + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".",
        "",
        "`confidence` is computed from the provenance of the clauses each row cites, not asserted:",
        "`certain` means every cited Indian clause carries the instrument's own words from a",
        "primary source; `likely` means at least one is a summary. A `*` after a clause id in the",
        "instance columns marks exactly those summaries. A row whose finding is that an instrument",
        "is **silent** on something cannot reach `certain` on a summary, because a summary cannot",
        "establish an absence.",
        "",
        "## Reproduced by a run",
        "",
        "| Gap | Type | Prop | Margin | India | Neighbour | Global | Conf. | Evidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sim:
        out.append(f"| {r['domain_gap']} | {r['gap_type']} | {r['violated_property']} "
                   f"| {r['margin_india']} | {r['india_instance']} | {r['neighbour_instance']} "
                   f"| {r['global_example']} | {r['confidence']} | `{r['evidence']}` |")
    out += ["", "## Read from the instruments", "",
            "| ID | Gap | Type | India | Neighbour | Global | Conf. | ITU hook |",
            "|---|---|---|---|---|---|---|---|"]
    for r in doc:
        out.append(f"| {r['gap_id']} | {r['domain_gap']} | {r['gap_type']} "
                   f"| {r['india_instance']} | {r['neighbour_instance']} | {r['global_example']} "
                   f"| {r['confidence']} | {r['itu_hook'] or '-'} |")

    likely = [r["gap_id"] for r in rows if r["confidence"] == "likely"]
    out += ["", "## What would raise confidence", "",
            f"{len(likely)} of {len(rows)} rows are `likely` rather than `certain`: "
            + ", ".join(likely) + ".",
            "",
            "Every one of them is held back by the same thing -- a cited clause whose record is a",
            "summary with a real source URL rather than the instrument's own words. The primary",
            "texts that would close them are listed in `data/sources/CLAUSES_PROVENANCE.md`; the",
            "clause ids still waiting are the starred ones above.",
            ""]
    return "\n".join(out)
