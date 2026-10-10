"""Export the pipeline's artefacts as one JSON bundle for the web UI. Y.3172 node: SINK."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.agents.roles import ROLE_ORDER, ROLES
from chakravyuh.audit.ledger import read, verify
from chakravyuh.fuzz.properties import PROPERTY_TEXT
from chakravyuh.policy.compiler import compile_all
from chakravyuh.y3172 import DESCRIPTIONS, REGISTRY

OUT = ROOT / "app" / "web" / "public" / "data"
RUNS = ROOT / "runs"
OUTPUTS = ROOT / "outputs"
DOCS = ROOT / "docs"
SCENARIO = "amphan_2020"

PACK_LABELS = {
    "india_current": ("India", "Current Indian law as it stands"),
    "bangladesh": ("Bangladesh", "BTRA 2001 + DM Act 2012 + CPP standing order"),
    "fcc_mdri": ("United States", "FCC Mandatory Disaster Response Initiative + DIRS"),
}


def _load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def _yaml_scenario() -> dict:
    import yaml
    doc = yaml.safe_load((ROOT / "data" / "scenarios" / f"{SCENARIO}.yaml").read_text())
    return {
        "scenario_id": doc.get("scenario_id", SCENARIO),
        "title": doc.get("title", ""),
        "description": " ".join((doc.get("description") or "").split()),
        "horizon_min": doc.get("horizon_min"),
        "tick_min": doc.get("tick_min"),
        "areas": doc.get("areas", []),
    }


def packs_meta() -> list[dict]:
    out = []
    for pid, pack in sorted(compile_all().items()):
        label, blurb = PACK_LABELS.get(pid, (pid, ""))
        out.append({
            "pack_id": pid, "label": label, "blurb": blurb,
            "jurisdiction": pack.jurisdiction, "version": pack.version,
            "mode": pack.mode, "rule_count": len(pack.rules),
        })
    return out


def roles_meta() -> list[dict]:
    out = []
    for rid in ROLE_ORDER:
        r = ROLES[rid]
        out.append({
            "role_id": r.role_id, "name": r.name, "analogue": r.analogue,
            "mandate": " ".join(r.mandate.split()),
            "boundaries": " ".join(r.boundaries.split()),
            "inbox_types": list(r.inbox_types),
            "priority": r.priority,
            "channel_latency_min": r.channel_latency_min,
        })
    return out


def scorecard(comparison: dict) -> dict:
    """P x pack matrix. Margin sign is the verdict; the number is how far from the line."""
    cells: dict[str, dict] = {}
    for d in comparison.get("divergences", []):
        pid = d["property_id"]
        cells[pid] = {
            "property_id": pid,
            "text": PROPERTY_TEXT.get(pid, ""),
            "margins": d.get("margins", {}),
            "passes_under": d.get("passes_under", []),
            "fails_under": d.get("fails_under", []),
        }
    return {"properties": [cells[p] for p in sorted(cells)]}


def gap_rows() -> list[dict]:
    path = OUTPUTS / "gap_register.csv"
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def fuzz_cards(summary: list) -> dict:
    """Campaign results, minus the two numbers a randomised search cannot reproduce.

    `runs_completed` counts shrink attempts as well as generated examples, and Hypothesis bounds
    shrinking by wall clock, so both it and `wall_seconds` differ between two runs of the same
    command on the same machine. They are honest measurements and they stay in
    outputs/fuzz_summary.json; they do not belong in a bundle whose whole justification is that
    it reproduces byte for byte. What the page reports instead is the declared budget, and the
    counterexamples themselves -- which do converge, because shrinking converges.
    """
    runs, cards = [], []
    for s in summary or []:
        asserted = s.get("asserted_properties", [])
        runs.append({
            "pack_id": s.get("pack_id"),
            "asserted_properties": asserted,
            "excluded_at_baseline": s.get("excluded_at_baseline", []),
            "baseline": s.get("baseline", {}),
            "max_examples": s.get("max_examples"),
            "examples_budgeted": s.get("max_examples", 0) if asserted else 0,
            "unique_minimal_failures": s.get("unique_minimal_failures"),
            "found": s.get("hypothesis_found_counterexample"),
        })
        for c in s.get("cards", []):
            cards.append({**c, "pack_id": s.get("pack_id")})
    seen, unique = set(), []
    for c in cards:
        key = (c.get("failure_id"), c.get("pack_id"))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return {"runs": runs, "cards": unique}


def ledger_meta() -> dict:
    entries = []
    for path in sorted(RUNS.glob(f"{SCENARIO}__*.jsonl")):
        ok, msg = verify(path)
        rows = [e for e in read(path)]
        kinds = Counter(getattr(e, "kind", "?") for e in rows)
        head = getattr(rows[-1], "hash", "") if rows else ""
        entries.append({
            "run_id": path.stem, "path": f"runs/{path.name}",
            "verified": ok, "message": msg, "entries": len(rows),
            "head_hash": head, "kinds": dict(sorted(kinds.items())),
        })
    tamper = []
    for path in sorted((OUTPUTS / "tamper").glob("*.jsonl")):
        ok, msg = verify(path)
        tamper.append({"run_id": path.stem, "verified": ok, "message": msg})
    return {"runs": entries, "tamper": tamper}


def _import_all_modules() -> None:
    """@node() registers on import, so an un-imported module is an invisible node."""
    import importlib
    import pkgutil

    import chakravyuh
    skipped: list[str] = []
    for mod in pkgutil.walk_packages(chakravyuh.__path__, "chakravyuh."):
        try:
            importlib.import_module(mod.name)
        except ImportError as exc:
            skipped.append(f"{mod.name} ({exc})")
    if skipped:
        print(f"note: {len(skipped)} module(s) not imported, so their nodes are not counted:")
        for line in skipped:
            print(f"  - {line}")


def y3172_map() -> list[dict]:
    _import_all_modules()
    out = []
    for node_id, desc in DESCRIPTIONS.items():
        key = node_id.value if hasattr(node_id, "value") else str(node_id)
        members = sorted(REGISTRY.get(node_id, []))
        out.append({"node": key, "description": desc, "count": len(members), "members": members})
    return out


def kb_stats() -> dict:
    from chakravyuh.kb.clause_store import ClauseStore
    store = ClauseStore()
    try:
        clauses = list(store.all_clauses())
        prov = Counter(getattr(c, "provenance", "") or "unknown" for c in clauses)
        status = Counter(getattr(c, "verbatim_status", "") or "unknown" for c in clauses)
        juris = Counter((getattr(c, "clause_id", "") or "").split(".")[0] for c in clauses)
        return {
            "total": len(clauses),
            "provenance": dict(sorted(prov.items())),
            "verbatim_status": dict(sorted(status.items())),
            "jurisdiction": dict(sorted(juris.items())),
        }
    finally:
        store.close()


def sources_meta() -> list[dict]:
    import yaml
    doc = yaml.safe_load((ROOT / "data" / "sources" / "MANIFEST.yaml").read_text()) or {}
    rows = doc.get("sources", doc) if isinstance(doc, dict) else doc
    out = []
    for s in (rows if isinstance(rows, list) else []):
        out.append({
            "id": s.get("id"),
            "instrument": s.get("instrument", ""),
            "gazette": s.get("gazette", ""),
            "status": s.get("status"),
            "url": s.get("url"),
            "sha256": (s.get("sha256") or "")[:16],
            "jurisdiction": s.get("jurisdiction", ""),
            "official": bool(s.get("official")),
            "pages": s.get("pages"),
            "feeds": s.get("feeds", []),
            "reason": s.get("partial_reason") or s.get("wanted_from")
                      or s.get("blocks") or "",
        })
    return out


TIMELINE_KINDS = {"EVENT", "PROPOSAL", "VERDICT", "EFFECT", "PROPERTY"}


def timeline_for(path: Path) -> dict:
    """Condense one ledger into a renderable timeline, joining verdicts onto their proposals."""
    rows = [e for e in read(path)]
    proposals: dict[str, dict] = {}
    items: list[dict] = []
    header, footer = {}, {}
    for e in rows:
        kind, p = e.kind, e.payload
        if kind == "EVENT" and p.get("kind") == "RUN_HEADER":
            header = p
            continue
        if kind == "EVENT" and p.get("kind") == "RUN_FOOTER":
            footer = p
            continue
        if kind not in TIMELINE_KINDS:
            continue
        if kind == "PROPOSAL":
            item = {
                "seq": e.seq, "t": e.t_minutes, "kind": "PROPOSAL",
                "proposal_id": p.get("proposal_id"), "role": p.get("actor_role"),
                "action": p.get("action_type"), "params": p.get("params", {}),
                "reasoning": p.get("reasoning", ""),
                "rule_ids": p.get("cited_rule_ids", []),
                "clause_ids": p.get("cited_clause_ids", []),
                "decision": None, "explanation": "",
            }
            proposals[item["proposal_id"]] = item
            items.append(item)
        elif kind == "VERDICT":
            target = proposals.get(p.get("proposal_id"))
            if target is not None:
                target["decision"] = p.get("decision")
                target["explanation"] = p.get("explanation", "")
                target["verdict_rule_ids"] = p.get("rule_ids", [])
                target["verdict_clause_ids"] = p.get("clause_ids", [])
        elif kind == "EVENT":
            ev = p.get("event") or p
            items.append({
                "seq": e.seq, "t": e.t_minutes, "kind": "EVENT",
                "event_id": ev.get("event_id", ""),
                "event_type": ev.get("type") or ev.get("kind") or "EVENT",
                "area": ev.get("area") or "",
                "payload": ev.get("payload", {}),
                "synthetic": bool(ev.get("synthetic")),
                "authentic": ev.get("authentic", True),
                "claimed_issuer": ev.get("claimed_issuer") or "",
                "delay_by_role": ev.get("delay_by_role", {}),
            })
        elif kind == "EFFECT":
            items.append({
                "seq": e.seq, "t": e.t_minutes, "kind": "EFFECT",
                "action": p.get("action_type"), "role": p.get("actor_role"),
                "area": p.get("area", ""),
                "cap_identifier": p.get("cap_identifier", ""),
                "cap_language": p.get("cap_language", ""),
                "cap_shape_ok": p.get("cap_shape_ok"),
                "detail": {k: v for k, v in p.items() if k not in
                           ("action_type", "actor_role", "area", "proposal_id", "t")},
            })
        elif kind == "PROPERTY":
            items.append({
                "seq": e.seq, "t": e.t_minutes, "kind": "PROPERTY",
                "property_id": p.get("property_id"), "holds": p.get("holds"),
                "margin": p.get("margin"), "description": p.get("description", ""),
            })
    items.sort(key=lambda i: i["seq"])
    counts = Counter(i["kind"] for i in items)
    decisions = Counter(i.get("decision") for i in items if i["kind"] == "PROPOSAL")
    return {
        "run_id": path.stem,
        "header": {k: header.get(k) for k in
                   ("pack_id", "scenario_id", "seed", "agent_tier", "tick_min",
                    "horizon_min", "pack_mode", "thresholds", "roles")},
        "footer": {k: footer.get(k) for k in
                   ("verdicts", "blocks_by_reason", "forged_executions", "human_gate",
                    "undelivered_at_horizon", "latency_by_role", "properties", "world")},
        "counts": dict(counts),
        "decisions": {k: v for k, v in decisions.items() if k},
        "items": items,
    }


# Shipped so a deployed build can verify a hash chain live instead of reporting a number baked
# in at build time. Only the India pair: it is the run the site foregrounds, and at ~1.1 MB the
# two files cost a fraction of what all five would.
SHIPPED_LEDGERS = (
    RUNS / f"{SCENARIO}__india_current__rule__seed0.jsonl",
    OUTPUTS / "tamper" / f"{SCENARIO}__india_current__rule__seed0.tampered.jsonl",
)


def copy_ledgers() -> None:
    """Copy the verifiable ledger pair into the bundle, byte for byte."""
    dest_dir = OUT / "ledgers"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for stale in dest_dir.glob("*.jsonl"):
        stale.unlink()
    for src in SHIPPED_LEDGERS:
        if src.exists():
            (dest_dir / src.name).write_bytes(src.read_bytes())
            print(f"wrote {dest_dir / src.name}")


def fingerprint() -> str:
    """Head hash of the India run: identifies this bundle's content, and is reproducible."""
    path = RUNS / f"{SCENARIO}__india_current__rule__seed0.jsonl"
    if not path.exists():
        return ""
    rows = list(read(path))
    return getattr(rows[-1], "hash", "") if rows else ""


# --------------------------------------------------------------------------- rubric

def rubric_status() -> dict:
    """The audit's own JSON. Written by app/scripts/rubric_audit.py, never asserted here."""
    data = _load_json(OUTPUTS / "rubric_status.json", None)
    if not data:
        return {"source": "", "command": "python app/scripts/rubric_audit.py",
                "totals": {"pass": 0, "waived": 0, "fail": 0, "checks": 0}, "checks": []}
    return data


# ------------------------------------------------------------------------- clauses

def clause_index(ids: set[str]) -> dict[str, dict]:
    """Full records for the clauses the page quotes, so a citation can be read in place."""
    from chakravyuh.kb.clause_store import ClauseNotFound, ClauseStore
    store = ClauseStore()
    out: dict[str, dict] = {}
    try:
        for cid in sorted(ids):
            try:
                c = store.get_clause(cid)
            except ClauseNotFound:
                continue
            out[cid] = {
                "clause_id": c.clause_id, "instrument": c.instrument, "section": c.section,
                "jurisdiction": c.jurisdiction, "text": c.text_verbatim,
                "source_url": c.source_url, "sha256": c.sha256[:16], "page": c.page,
                "provenance": c.provenance, "verbatim_status": c.verbatim_status,
                "quotable": bool(c.quotable),
            }
    finally:
        store.close()
    return out


# --------------------------------------------------------------------- derivations

PROPERTY_FORMULA = {
    "P1": ("margin = min %% of affected cells reachable for relief - threshold",
           "worst suspension window", "min_pct_relief_cells"),
    "P2": ("margin = threshold - irreversible executions on an unauthenticated order",
           "executions traced to authentic=False", "max_forged_executions"),
    "P3": ("margin = T_alert - worst delay from warning to a valid local-language alert",
           "worst delay", "t_alert_min"),
    "P4": ("margin = T_roam - worst delay from landfall to disaster roaming active",
           "worst delay", "t_roam_min"),
}


def _p1(detail: dict, _horizon: int) -> tuple[float, float, float, str, list[dict]]:
    threshold = float(detail.get("threshold_pct", 0.0))
    observed = float(detail.get("min_pct_observed", 100.0))
    terms = [{"label": k.split("@")[0], "value": v.get("pct_relief_reachable"),
              "note": f"suspension {k.split('@')[-1]}, T+{v['window'][0]}..T+{v['window'][1]}"
                      f"{'' if v.get('exempt_priority_slice') else ', no priority slice exempted'}"}
             for k, v in sorted(detail.get("per_area", {}).items())]
    note = (f"{detail.get('suspensions_examined', 0)} suspension(s) examined; the margin takes "
            "the worst of them.")
    return observed, threshold, round(observed - threshold, 2), note, terms


def _p2(detail: dict, _horizon: int) -> tuple[float, float, float, str, list[dict]]:
    threshold = float(detail.get("threshold", 0))
    observed = float(detail.get("count", 0))
    terms = [{"label": f"{e.get('action_type')} in {e.get('area')}",
              "value": e.get("at_t"),
              "note": f"ordered by event {e.get('order_event_id')}"}
             for e in detail.get("executions", [])]
    note = ("Every execution here was traced back to an order the world marks authentic=False. "
            "No agent can read that flag.")
    return observed, threshold, float(threshold - observed), note, terms


def _worst_delay(per_area: dict) -> float:
    return max((float(v["delay_min"]) for v in per_area.values() if v.get("delay_min") is not None),
               default=0.0)


def _p3(detail: dict, horizon: int) -> tuple[float, float, float, str, list[dict]]:
    threshold = float(detail.get("threshold_min", 0))
    per_area = detail.get("per_area", {})
    worst = _worst_delay(per_area)
    missed = detail.get("areas_missed", [])
    bases = detail.get("warning_baseline_by_area", {})
    if missed:
        unserved = max((horizon - int(bases.get(a, 0)) for a in missed), default=0)
        observed = max(worst, float(unserved))
        note = (f"{', '.join(missed)} never received a valid local-language alert, so the delay "
                f"is counted to the horizon (T+{horizon}) rather than left undefined.")
    else:
        observed = float(detail.get("max_delay_min", worst))
        note = "Every affected area was alerted; the margin takes the slowest."
    terms = [{"label": a,
              "value": v.get("delay_min") if v.get("alert_t") is not None
                       else horizon - int(bases.get(a, 0)),
              "note": (f"alerted at T+{v['alert_t']}" if v.get("alert_t") is not None
                       else v.get("reason", "never alerted"))}
             for a, v in sorted(per_area.items())]
    return observed, threshold, float(threshold - observed), note, terms


def _p4(detail: dict, horizon: int) -> tuple[float, float, float, str, list[dict]]:
    threshold = float(detail.get("threshold_min", 0))
    per_area = detail.get("per_area", {})
    worst = _worst_delay(per_area)
    if detail.get("areas_missed"):
        elapsed = float(detail.get("elapsed_min", 0))
        observed = max(worst, elapsed)
        note = (f"{', '.join(detail['areas_missed'])} never had disaster roaming, so the delay is "
                f"counted from landfall (T+{detail.get('landfall_t')}) to the horizon "
                f"(T+{horizon}).")
    else:
        observed = float(detail.get("max_delay_min", worst))
        note = "Roaming reached every affected circle; the margin takes the slowest."
    terms = [{"label": a,
              "value": v.get("delay_min") if v.get("roaming_t") is not None
                       else int(horizon - int(detail.get("landfall_t", 0))),
              "note": (f"roaming active at T+{v['roaming_t']}" if v.get("roaming_t") is not None
                       else "roaming never became active")}
             for a, v in sorted(per_area.items())]
    return observed, threshold, float(threshold - observed), note, terms


RECOMPUTE = {"P1": _p1, "P2": _p2, "P3": _p3, "P4": _p4}


def derivations() -> list[dict]:
    """Recompute each margin from the operands the run recorded, and say whether it agrees.

    This is the answer to "where does that number come from". Nothing here is read off the
    scorecard: the arithmetic is redone from the property's own detail block and compared with
    the margin the run wrote, so a disagreement would show rather than hide.
    """
    out: list[dict] = []
    for path in sorted(RUNS.glob(f"{SCENARIO}__*.jsonl")):
        rows = list(read(path))
        header = next((e.payload for e in rows
                       if e.kind == "EVENT" and e.payload.get("kind") == "RUN_HEADER"), {})
        pack_id = header.get("pack_id") or path.stem
        horizon = int(header.get("horizon_min") or 0)
        thresholds = header.get("thresholds", {})
        for e in rows:
            if e.kind != "PROPERTY":
                continue
            p = e.payload
            pid = p.get("property_id")
            fn = RECOMPUTE.get(pid)
            if fn is None:
                continue
            detail = p.get("detail") or {}
            if "note" in detail and not detail.get("per_area"):
                out.append({
                    "pack_id": pack_id, "property_id": pid, "applicable": False,
                    "note": detail["note"], "margin": p.get("margin"), "passed": p.get("passed"),
                    "unit": p.get("unit", ""), "formula": PROPERTY_FORMULA[pid][0],
                    "arithmetic": "", "observed": None, "observed_label": "",
                    "threshold": None, "threshold_name": PROPERTY_FORMULA[pid][2],
                    "agrees": True, "terms": [], "seq": e.seq,
                })
                continue
            observed, threshold, recomputed, note, terms = fn(detail, horizon)
            recorded = float(p.get("margin"))
            out.append({
                "pack_id": pack_id,
                "property_id": pid,
                "applicable": True,
                "unit": p.get("unit", ""),
                "formula": PROPERTY_FORMULA[pid][0],
                "observed_label": PROPERTY_FORMULA[pid][1],
                "observed": observed,
                "threshold": threshold,
                "threshold_name": PROPERTY_FORMULA[pid][2],
                "threshold_from": thresholds.get(PROPERTY_FORMULA[pid][2]),
                "arithmetic": _arith(pid, observed, threshold, recomputed),
                "margin": recorded,
                "recomputed": recomputed,
                "agrees": abs(recomputed - recorded) < 1e-6,
                "passed": bool(p.get("passed")),
                "note": note,
                "terms": terms,
                "seq": e.seq,
            })
    return out


def _n(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _arith(pid: str, observed: float, threshold: float, margin: float) -> str:
    if pid == "P1":
        return f"{_n(observed)} - {_n(threshold)} = {_n(margin)}"
    return f"{_n(threshold)} - {_n(observed)} = {_n(margin)}"


# ----------------------------------------------------------------------- retrieval

RRF_K = 60


def retrieval_example(retrieval: list[dict]) -> dict:
    """One question carried through every retriever, with the RRF arithmetic written out.

    Reconstructed from the per-question rankings the evaluation recorded. The engine fuses at
    chunk level and this reconstruction is at clause level, so the two can order ties
    differently -- `agrees_with_recorded` says whether they did.
    """
    by_mode = {r["mode"]: {q["qid"]: q for q in r.get("per_question", [])} for r in retrieval}
    if "bm25" not in by_mode or "vector" not in by_mode:
        return {}
    questions = {}
    qa = ROOT / "data" / "eval" / "retrieval_qa.jsonl"
    if qa.exists():
        for line in qa.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                questions[row["qid"]] = row

    # Pick the first question where BM25 and the vector index disagree on the top hit: that is
    # the only kind of question where showing the fusion teaches anything.
    qid = next((q for q in sorted(by_mode["bm25"])
                if by_mode["bm25"][q]["retrieved"][:1] != by_mode["vector"][q]["retrieved"][:1]),
               sorted(by_mode["bm25"])[0])

    ranks: dict[str, dict[str, int]] = {}
    for mode in ("bm25", "vector"):
        for rank, cid in enumerate(by_mode[mode][qid]["retrieved"], start=1):
            ranks.setdefault(cid, {})[mode] = rank

    fused = []
    for cid, r in ranks.items():
        parts = [{"mode": m, "rank": r[m], "contribution": round(1.0 / (RRF_K + r[m]), 6)}
                 for m in ("bm25", "vector") if m in r]
        fused.append({"clause_id": cid, "parts": parts,
                      "score": round(sum(x["contribution"] for x in parts), 6)})
    fused.sort(key=lambda f: (-f["score"], f["clause_id"]))
    for a, b in zip(fused, fused[1:], strict=False):
        a["tied_with_next"] = a["score"] == b["score"]
    if fused:
        fused[-1]["tied_with_next"] = False

    recorded = by_mode.get("hybrid", {}).get(qid, {}).get("retrieved", [])
    reconstructed = [f["clause_id"] for f in fused]
    gold = questions.get(qid, {}).get("gold_clause_ids", by_mode["bm25"][qid].get("gold", []))
    return {
        "qid": qid,
        "question": questions.get(qid, {}).get("question", ""),
        "gold_clause_ids": gold,
        "k": RRF_K,
        "formula": "score(d) = sum over rankings of 1 / (k + rank(d)),  k = 60",
        "rankings": [{"mode": m, "retrieved": by_mode[m][qid]["retrieved"],
                      "top_score": by_mode[m][qid].get("top_score"),
                      "first_gold_rank": by_mode[m][qid].get("first_gold_rank")}
                     for m in ("bm25", "vector", "hybrid", "hybrid_rerank", "tree")
                     if m in by_mode and qid in by_mode[m]],
        "fused": fused,
        "recorded_hybrid": recorded,
        "agrees_with_recorded": reconstructed[:len(recorded)] == list(recorded),
        "caveat": ("Fusion in the engine runs over chunks; this reconstruction runs over the "
                   "clause ids the evaluation recorded, so ties can order differently."),
    }


# ------------------------------------------------------------------ knowledge base

def kb_graph() -> dict:
    """What the knowledge base is shaped like: documents, clauses, chunks, two indexes."""
    from chakravyuh.kb.clause_store import ClauseStore
    store = ClauseStore()
    try:
        clauses = list(store.all_clauses())
    finally:
        store.close()

    by_instrument: dict[str, dict] = {}
    for c in clauses:
        row = by_instrument.setdefault(c.instrument, {
            "instrument": c.instrument, "jurisdiction": c.jurisdiction,
            "clauses": 0, "real_text": 0, "quotable": 0, "with_page": 0,
        })
        row["clauses"] += 1
        row["real_text"] += int(c.is_real_text)
        row["quotable"] += int(c.quotable)
        row["with_page"] += int(c.page is not None)

    chunks_path = ROOT / "data" / "clauses" / "chunks.jsonl"
    chunks = 0
    collections: Counter = Counter()
    chunk_fields: list[str] = []
    if chunks_path.exists():
        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            chunks += 1
            collections[row.get("collection", "?")] += 1
            if not chunk_fields:
                chunk_fields = sorted(row)
    return {
        "clauses": len(clauses),
        "chunks": chunks,
        "collections": dict(sorted(collections.items())),
        "chunk_metadata_fields": chunk_fields,
        "instruments": sorted(by_instrument.values(),
                              key=lambda r: (-r["clauses"], r["instrument"])),
        "quotable": sum(1 for c in clauses if c.quotable),
        "real_text": sum(1 for c in clauses if c.is_real_text),
        "with_pdf_hash": sum(1 for c in clauses if c.source_pdf_sha256),
    }


# ----------------------------------------------------------------------- the trace

TRACE_EVENTS = ("imd01", "sim03")


def _time_anchors(detail: dict) -> set[tuple[str, int]]:
    """(area, t) pairs a property's working actually turns on, e.g. when an alert landed."""
    anchors: set[tuple[str, int]] = set()
    for area, row in (detail.get("per_area") or {}).items():
        if not isinstance(row, dict):
            continue
        for key, value in row.items():
            if key.endswith("_t") and isinstance(value, int):
                anchors.add((area.split("@")[0], value))
    return anchors


def _touched_properties(rows, ids: set[str], effects: list[dict]) -> list[dict]:
    """Which property checks turn on something this event produced, and by what link.

    Two kinds of link, both structural. An id link means the property's own working names the
    suspension or the order by id. A moment link means the property turns on an (area, minute)
    that one of these effects created -- the alert this event led to is the alert P3 timed.
    """
    moments = {(e.get("area") or "", e.get("t")) for e in effects}
    out = []
    for e in rows:
        if e.kind != "PROPERTY":
            continue
        detail = e.payload.get("detail") or {}
        via = []
        named = sorted(i for i in ids if i in json.dumps(detail))
        if named:
            via.append({"kind": "id", "what": named[:3]})
        shared = sorted(moments & _time_anchors(detail))
        if shared:
            via.append({"kind": "moment",
                        "what": [f"{a} at T+{t}" for a, t in shared[:3]]})
        if via:
            out.append({"property_id": e.payload.get("property_id"),
                        "margin": e.payload.get("margin"),
                        "passed": bool(e.payload.get("passed")), "via": via})
    return out


def trace_for(rows, event_id: str) -> dict:
    """Follow one event from release to the number it ends up moving."""
    event, deliveries, proposals, verdicts, effects = None, [], [], {}, []
    for e in rows:
        p = e.payload
        if e.kind == "EVENT" and (p.get("event") or {}).get("event_id") == event_id:
            event = {"seq": e.seq, "t": e.t_minutes, **(p.get("event") or {})}
        elif e.kind == "DELIVERY" and p.get("event_id") == event_id:
            deliveries.append({"seq": e.seq, "role": p.get("role"),
                               "released_t": p.get("released_t"), "arrives_t": p.get("arrives_t"),
                               "latency_min": p.get("latency_min"),
                               "visible_payload": (p.get("visible") or {}).get("payload", {})})
        elif e.kind == "PROPOSAL" and event_id in (p.get("triggered_by_event_ids") or []):
            proposals.append({"seq": e.seq, "t": e.t_minutes,
                              "proposal_id": p.get("proposal_id"), "role": p.get("actor_role"),
                              "action": p.get("action_type"), "params": p.get("params", {}),
                              "reasoning": p.get("reasoning", ""),
                              "cited_rule_ids": p.get("cited_rule_ids", []),
                              "cited_clause_ids": p.get("cited_clause_ids", [])})
    pids = {x["proposal_id"] for x in proposals}
    for e in rows:
        p = e.payload
        if e.kind == "VERDICT" and p.get("proposal_id") in pids:
            verdicts[p["proposal_id"]] = {
                "seq": e.seq, "decision": p.get("decision"), "mode": p.get("mode"),
                "explanation": p.get("explanation", ""), "rule_ids": p.get("rule_ids", []),
                "clause_ids": p.get("clause_ids", [])}
        elif e.kind == "EFFECT" and p.get("proposal_id") in pids:
            effects.append({"seq": e.seq, "t": e.t_minutes, "action": p.get("action_type"),
                            "area": p.get("area", ""),
                            "detail": {k: v for k, v in sorted(p.items())
                                       if k not in ("action_type", "actor_role", "proposal_id")}})
    ids = {event_id} | pids | {f"susp-{x}" for x in pids}
    hidden = sorted((event or {}).get("payload", {}).get("truth", {}))
    return {
        "event_id": event_id,
        "event": event,
        "hidden_from_agents": hidden,
        "deliveries": sorted(deliveries, key=lambda d: (d["arrives_t"], d["role"])),
        "proposals": [{**x, "verdict": verdicts.get(x["proposal_id"])} for x in proposals],
        "effects": effects,
        "moves": _touched_properties(rows, ids, effects),
    }


def traces() -> list[dict]:
    path = RUNS / f"{SCENARIO}__india_current__rule__seed0.jsonl"
    if not path.exists():
        return []
    rows = list(read(path))
    return [trace_for(rows, eid) for eid in TRACE_EVENTS]


# ------------------------------------------------------------------------- the flow

def flow(bundle: dict, rows_by_pack: dict[str, Counter]) -> list[dict]:
    """The pipeline as stages, each one carrying the number it actually produced."""
    india = rows_by_pack.get("india_current", Counter())
    kb = bundle["kb_graph"]
    held = sum(1 for s in bundle["sources"] if s["status"] == "held")
    rules = sum(p["rule_count"] for p in bundle["packs"])
    fuzz_runs = sum(r.get("examples_budgeted") or 0 for r in bundle["fuzz"]["runs"])
    stages = [
        ("SRC", "Primary sources", "data/sources/MANIFEST.yaml",
         "python app/scripts/fetch_sources.py --check",
         f"{held} documents held", "sources pinned by sha256",
         "Every instrument is fetched once, hashed, and checked against strings only the real "
         "document carries. A source we do not hold says so, and names the finding it caps."),
        ("C", "Ingest", "chakravyuh/kb/ingest.py",
         "python app/scripts/build_kb.py",
         f"{kb['clauses']} clauses", f"{kb['real_text']} carry the instrument's own words",
         "Gazette PDFs are split clause by clause. Each record keeps its verbatim text, a "
         "sha256 of that text, the page, and the hash of the PDF it came from."),
        ("PP", "Structure and retrieval", "chakravyuh/kb/retrieve.py",
         "python app/scripts/eval_retrieval.py",
         f"{kb['chunks']} chunks", "BM25 + vector, fused by RRF",
         "One chunk per clause, each carrying clause_id, instrument, jurisdiction, page and "
         "source_url -- so a hit can be cited, not just quoted."),
        ("PP", "Policy packs", "chakravyuh/policy/compiler.py",
         "python app/scripts/run_demo.py --seed 0",
         f"{rules} rules", f"across {len(bundle['packs'])} rulebooks",
         "A rule that cites a clause the store does not hold, or whose text no longer hashes "
         "as recorded, does not compile. The simulator cannot run on invented law."),
        ("M", "Agents propose", "chakravyuh/agents/",
         "python app/scripts/run_demo.py --pack india_current",
         f"{india.get('PROPOSAL', 0)} proposals", f"from {len(bundle['roles'])} role-bound agents",
         "Each agent sees only its own inbox, delayed and redacted, and returns a typed proposal "
         "naming the rule it believes authorises it."),
        ("P", "The engine decides", "chakravyuh/policy/engine.py",
         "python -m pytest tests/test_p2_policy_engine.py",
         f"{india.get('VERDICT', 0)} verdicts", "ALLOW | BLOCK | NEEDS_HUMAN",
         "A pure function over (proposal, world, pack). No model appears anywhere in its import "
         "graph, and a test fails the build if one ever does."),
        ("D", "The Game Master resolves", "chakravyuh/sim/game_master.py",
         "python app/scripts/run_demo.py --seed 0",
         f"{india.get('EFFECT', 0)} effects", f"{india.get('DELIVERY', 0)} deliveries",
         "One world state, one rulebook, one fixed order: (t, role priority, proposal_id). "
         "This is what makes the same seed produce the same ledger head hash."),
        ("SINK", "Ledger and findings", "chakravyuh/audit/ledger.py",
         "python app/scripts/verify_ledger.py --all",
         f"{sum(r['entries'] for r in bundle['ledger']['runs'])} ledger entries",
         f"{len(bundle['gaps'])} registered gaps",
         "Every entry commits to the one before it. The four properties are checked against the "
         f"finished world, and a budget of {fuzz_runs:,} mutated worlds is searched for the "
         "minimal case."),
    ]
    return [{"node": n, "title": t, "module": m, "command": c,
             "measure": a, "measure_sub": b, "body": body}
            for n, t, m, c, a, b, body in stages]


def kind_counts() -> dict[str, Counter]:
    """Entries per kind per pack: the measured numbers the flow diagram reports."""
    out: dict[str, Counter] = {}
    for path in sorted(RUNS.glob(f"{SCENARIO}__*.jsonl")):
        rows = list(read(path))
        header = next((e.payload for e in rows
                       if e.kind == "EVENT" and e.payload.get("kind") == "RUN_HEADER"), {})
        out[header.get("pack_id") or path.stem] = Counter(e.kind for e in rows)
    return out


def cited_clause_ids(bundle: dict) -> set[str]:
    """Every clause the page can show in place, gathered from what the page actually cites."""
    ids: set[str] = set()
    for t in bundle["traces"]:
        for pr in t["proposals"]:
            ids.update(pr["cited_clause_ids"])
            ids.update((pr.get("verdict") or {}).get("clause_ids", []))
    for card in bundle["fuzz"]["cards"]:
        ids.update(card.get("responsible_clause_ids", []))
    ex = bundle.get("retrieval_example") or {}
    for r in ex.get("rankings", []):
        ids.update(r["retrieved"])
    ids.update(ex.get("gold_clause_ids", []))
    return {i for i in ids if i}


# Every section of the bundle comes from one of these. Export them absent and the page quietly
# loses a whole band -- which reads downstream as "the committed bundle is stale" rather than
# "the pipeline did not finish". Name them, and say which command writes each one.
REQUIRED = (
    ("data/clauses/clauses.sqlite", "python app/scripts/build_kb.py"),
    ("outputs/comparison.json", "python app/scripts/run_demo.py --seed 0"),
    ("outputs/gap_register.csv", "python app/scripts/run_demo.py --seed 0"),
    ("outputs/retrieval_eval.json", "python app/scripts/eval_retrieval.py"),
    ("outputs/adviser_eval.json", "python app/scripts/eval_adviser.py"),
    ("outputs/fuzz_summary.json", "python app/scripts/run_fuzz.py"),
    ("outputs/rubric_status.json", "python app/scripts/rubric_audit.py"),
)


def missing_artefacts() -> list[tuple[str, str]]:
    return [(rel, cmd) for rel, cmd in REQUIRED if not (ROOT / rel).exists()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="export anyway when a stage has not run; the result is not committable")
    args = ap.parse_args()

    # The clause store and the Chroma path are declared relative to the repository root, so an
    # export run from anywhere else silently reads an empty store and writes a degraded bundle.
    # Pin the working directory rather than trusting the caller's.
    os.chdir(ROOT)

    gaps = missing_artefacts()
    if gaps:
        print("the pipeline has not finished; these artefacts are missing:", file=sys.stderr)
        for rel, cmd in gaps:
            print(f"  {rel:<34} written by  {cmd}", file=sys.stderr)
        if not args.allow_incomplete:
            print("\nrefusing to write a partial bundle. Run `make artefacts`, or pass "
                  "--allow-incomplete for a local preview that must not be committed.",
                  file=sys.stderr)
            return 1
        print("\n--allow-incomplete: exporting without them. Do not commit this bundle.\n",
              file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    comparison = _load_json(OUTPUTS / "comparison.json", {}) or {}
    retrieval = _load_json(OUTPUTS / "retrieval_eval.json", []) or []
    adviser = _load_json(OUTPUTS / "adviser_eval.json", {}) or {}

    bundle = {
        "fingerprint": fingerprint(),
        "scenario": _yaml_scenario(),
        "packs": packs_meta(),
        "roles": roles_meta(),
        "properties": PROPERTY_TEXT,
        "scorecard": scorecard(comparison),
        "gaps": gap_rows(),
        "fuzz": fuzz_cards(_load_json(OUTPUTS / "fuzz_summary.json", []) or []),
        "ledger": ledger_meta(),
        "y3172": y3172_map(),
        "kb": kb_stats(),
        "kb_graph": kb_graph(),
        "sources": sources_meta(),
        "retrieval": [{k: v for k, v in r.items() if k != "per_question"} for r in retrieval],
        "retrieval_example": retrieval_example(retrieval),
        "adviser": adviser.get("summary", {}),
        "derivations": derivations(),
        "traces": traces(),
        "rubric": rubric_status(),
    }
    bundle["flow"] = flow(bundle, kind_counts())
    bundle["clauses"] = clause_index(cited_clause_ids(bundle))
    (OUT / "bundle.json").write_text(json.dumps(bundle, indent=1, sort_keys=True))
    print(f"wrote {OUT/'bundle.json'}")

    copy_ledgers()

    index = []
    for path in sorted(RUNS.glob(f"{SCENARIO}__*.jsonl")):
        tl = timeline_for(path)
        pack = tl["header"].get("pack_id") or path.stem
        dest = OUT / f"timeline.{pack}.json"
        dest.write_text(json.dumps(tl, separators=(",", ":"), sort_keys=True))
        index.append({"pack_id": pack, "file": dest.name, "items": len(tl["items"])})
        print(f"wrote {dest}  ({len(tl['items'])} items)")
    (OUT / "timelines.json").write_text(json.dumps(index, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
