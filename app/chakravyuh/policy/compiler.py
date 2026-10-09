"""YAML policy pack -> validated Rule objects. Y.3172 node: PP."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import yaml

from ..schemas import PolicyPack, Rule
from ..y3172 import node
from ..kb.clause_store import ClauseStore, DEFAULT_DB

PACKS_DIR = Path("data/packs")

KNOWN_CONDITIONS = {
    "event_seen",
    "event_seen_authentic",
    "area_in",
    "after_min",
    "before_min",
    "within_min_of",
    "disaster_declared",
    "order_in_force",
    "param_max",
    "param_required",
    "param_in",
}

KNOWN_EFFECTS = {"permit", "oblige", "prohibit"}


class PackCompileError(ValueError):
    """A pack is not fit to run: unknown clause, hash drift, bad condition, duplicate rule id."""
@node("PP")
def compile_pack(path: str | Path, store: Optional[ClauseStore] = None,
                 strict_clauses: bool = True) -> PolicyPack:
    """Load, validate and return a PolicyPack. Raises PackCompileError on any defect."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise PackCompileError(f"{path}: top level must be a mapping")

    owns_store = store is None
    if store is None and strict_clauses:
        store = ClauseStore(DEFAULT_DB)

    errors: list[str] = []
    rules: list[Rule] = []
    seen_ids: set[str] = set()

    for i, rr in enumerate(raw.get("rules") or []):
        where = f"{path}:rules[{i}]"
        try:
            rule = Rule(**rr)
        except Exception as exc:
            errors.append(f"{where}: {exc}")
            continue

        if rule.rule_id in seen_ids:
            errors.append(f"{where}: duplicate rule_id {rule.rule_id!r}")
        seen_ids.add(rule.rule_id)

        if rule.effect not in KNOWN_EFFECTS:
            errors.append(f"{where} ({rule.rule_id}): unknown effect {rule.effect!r}")

        unknown = set(rule.conditions) - KNOWN_CONDITIONS
        if unknown:
            errors.append(f"{where} ({rule.rule_id}): unknown condition keys {sorted(unknown)}")
        errors.extend(_check_condition_shapes(rule, where))

        if strict_clauses:
            if not rule.clause_ids:
                errors.append(f"{where} ({rule.rule_id}): no clause_ids -- every rule must cite law")
            for cid in rule.clause_ids:
                clause = store.try_get(cid)
                if clause is None:
                    errors.append(f"{where} ({rule.rule_id}): clause {cid!r} not in clause store")
                elif not clause.hash_matches():
                    errors.append(f"{where} ({rule.rule_id}): clause {cid!r} failed verbatim hash check")

        rules.append(rule)

    if owns_store and store is not None:
        store.close()

    if errors:
        raise PackCompileError(f"{len(errors)} error(s) compiling {path}:\n  - " + "\n  - ".join(errors))

    try:
        return PolicyPack(pack_id=raw["pack_id"], jurisdiction=raw["jurisdiction"],
                          version=str(raw["version"]), mode=raw.get("mode", "blocking"), rules=rules)
    except KeyError as exc:
        raise PackCompileError(f"{path}: missing required field {exc}") from exc


def _check_condition_shapes(rule: Rule, where: str) -> list[str]:
    errs: list[str] = []
    c = rule.conditions
    if "within_min_of" in c:
        v = c["within_min_of"]
        if not isinstance(v, dict) or "event_type" not in v or "minutes" not in v:
            errs.append(f"{where} ({rule.rule_id}): within_min_of needs {{event_type, minutes}}")
    if "area_in" in c and c["area_in"] not in ("affected", "declared", "cross_border", "any"):
        errs.append(f"{where} ({rule.rule_id}): area_in must be affected|declared|cross_border|any")
    for key in ("param_max", "param_in"):
        if key in c and not isinstance(c[key], dict):
            errs.append(f"{where} ({rule.rule_id}): {key} must be a mapping")
    if "param_required" in c and not isinstance(c["param_required"], list):
        errs.append(f"{where} ({rule.rule_id}): param_required must be a list")
    return errs


@node("PP")
def compile_all(packs_dir: str | Path = PACKS_DIR, store: Optional[ClauseStore] = None,
                strict_clauses: bool = True) -> dict[str, PolicyPack]:
    """Compile every *.yaml in packs_dir. Returns {pack_id: PolicyPack}."""
    owns_store = store is None
    if store is None and strict_clauses:
        store = ClauseStore(DEFAULT_DB)
    out: dict[str, PolicyPack] = {}
    for p in sorted(Path(packs_dir).glob("*.yaml")):
        pack = compile_pack(p, store=store, strict_clauses=strict_clauses)
        out[pack.pack_id] = pack
    if owns_store and store is not None:
        store.close()
    return out


def compile_report(packs: Iterable[PolicyPack]) -> dict:
    """Numbers for kb_report.md §9.1: rules per pack, clause citations, distinct clauses used."""
    rows = []
    for pack in packs:
        cited = {cid for r in pack.rules for cid in r.clause_ids}
        rows.append({
            "pack_id": pack.pack_id,
            "jurisdiction": pack.jurisdiction,
            "mode": pack.mode,
            "rules": len(pack.rules),
            "permits": sum(1 for r in pack.rules if r.effect == "permit"),
            "obligations": sum(1 for r in pack.rules if r.effect == "oblige"),
            "prohibitions": sum(1 for r in pack.rules if r.effect == "prohibit"),
            "distinct_clauses_cited": len(cited),
            "rules_requiring_authenticated_order": sum(1 for r in pack.rules if r.requires_authenticated_order),
        })
    return {"packs": rows}
