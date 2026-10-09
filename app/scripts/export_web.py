"""Export the pipeline's artefacts as one JSON bundle for the web UI. Y.3172 node: SINK.

The frontend NEVER computes anything. It renders what the simulator, the policy engine and the
fuzzer already decided and already wrote to disk. This script is the only bridge between them,
so there is exactly one place where a number could drift from its source -- and it does not,
because every field below is copied, not recalculated.

    python app/scripts/export_web.py        # -> app/web/public/data/*.json

Run `python app/scripts/showcase.py` first: this reads runs/, outputs/ and docs/.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root: data/, outputs/, runs/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # app/: the chakravyuh package

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

# Human-facing names for the three regimes. The pack files carry ids; a judge reads names.
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
    runs, cards = [], []
    for s in summary or []:
        runs.append({
            "pack_id": s.get("pack_id"),
            "asserted_properties": s.get("asserted_properties", []),
            "excluded_at_baseline": s.get("excluded_at_baseline", []),
            "baseline": s.get("baseline", {}),
            "runs_completed": s.get("runs_completed"),
            "max_examples": s.get("max_examples"),
            "unique_minimal_failures": s.get("unique_minimal_failures"),
            "found": s.get("hypothesis_found_counterexample"),
            "wall_seconds": s.get("wall_seconds"),
        })
        for c in s.get("cards", []):
            cards.append({**c, "pack_id": s.get("pack_id")})
    # One card per (failure_id, pack): the same minimal counterexample repeats across runs.
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
        except ImportError as exc:      # optional dependency absent in this environment
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


# Ledger kinds the timeline shows. DELIVERY is the inbox plumbing: thousands of rows, no drama.
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
        # The footer carries the run's own accounting: why proposals were blocked, whether a
        # forged order executed, and who released the human gate. It is the most quotable entry
        # in the ledger, so it is surfaced rather than rendered as one more timeline row.
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    comparison = _load_json(OUTPUTS / "comparison.json", {}) or {}
    retrieval = _load_json(OUTPUTS / "retrieval_eval.json", []) or []
    adviser = _load_json(OUTPUTS / "adviser_eval.json", {}) or {}

    bundle = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "sources": sources_meta(),
        "retrieval": [{k: v for k, v in r.items() if k != "per_question"} for r in retrieval],
        "adviser": adviser.get("summary", {}),
    }
    (OUT / "bundle.json").write_text(json.dumps(bundle, indent=1, sort_keys=True))
    print(f"wrote {OUT/'bundle.json'}")

    index = []
    for path in sorted(RUNS.glob(f"{SCENARIO}__*.jsonl")):
        tl = timeline_for(path)
        pack = tl["header"].get("pack_id") or path.stem
        dest = OUT / f"timeline.{pack}.json"
        dest.write_text(json.dumps(tl, indent=1, sort_keys=True))
        index.append({"pack_id": pack, "file": dest.name, "items": len(tl["items"])})
        print(f"wrote {dest}  ({len(tl['items'])} items)")
    (OUT / "timelines.json").write_text(json.dumps(index, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
