"""Cross-pack comparison: replay the same seed under every pack. Y.3172 node: SINK.

This is what turns "India has a gap" into the evidence the rubric calls critical: the same facts,
the same agents, the same seed, three legal regimes, and a measured difference. The neighbouring
and global examples are produced by running them, not asserted.
"""
from __future__ import annotations

from typing import Callable, Mapping, Optional, Sequence

from ..schemas import PolicyPack, RunResult
from ..sim.events import Scenario
from ..sim.runner import context_for, run
from ..y3172 import node


@node("SINK")
def run_across_packs(scenario: Scenario, packs: Mapping[str, PolicyPack], seed: int = 0,
                     agent_factory: Optional[Callable[[], dict]] = None,
                     mutations: Sequence[dict] = (), runs_dir: str = "runs",
                     run_suffix: str = "") -> dict[str, RunResult]:
    """Run the same scenario+seed under each pack. Returns {pack_id: RunResult}."""
    out: dict[str, RunResult] = {}
    for pack_id in sorted(packs):
        agents = agent_factory() if agent_factory else None
        out[pack_id] = run(scenario, packs[pack_id], agents=agents, seed=seed,
                           mutations=mutations, runs_dir=runs_dir, run_suffix=run_suffix)
    return out


@node("SINK")
def passes_under(results: Mapping[str, RunResult], property_id: str) -> list[str]:
    """Pack ids under which this property passes. The `passes_under_packs` field of a FailureCard."""
    return sorted(pid for pid, r in results.items()
                  if all(p.passed for p in r.properties if p.property_id == property_id))


@node("SINK")
def comparison_table(results: Mapping[str, RunResult]) -> list[dict]:
    """One row per (pack, property) with pass/fail and margin: the comparison board in the UI."""
    rows: list[dict] = []
    for pack_id in sorted(results):
        r = results[pack_id]
        for prop in r.properties:
            rows.append({
                "pack_id": pack_id, "property_id": prop.property_id,
                "passed": prop.passed, "margin": prop.margin, "unit": prop.unit,
                "run_id": r.run_id, "seed": r.seed, "agent_tier": r.agent_tier,
            })
    return rows


@node("SINK")
def divergences(results: Mapping[str, RunResult]) -> list[dict]:
    """Properties where the packs disagree. These are the findings worth reporting."""
    by_prop: dict[str, dict[str, bool]] = {}
    margins: dict[str, dict[str, float]] = {}
    for pack_id, r in results.items():
        for prop in r.properties:
            by_prop.setdefault(prop.property_id, {})[pack_id] = prop.passed
            margins.setdefault(prop.property_id, {})[pack_id] = prop.margin
    out = []
    for pid, verdicts in sorted(by_prop.items()):
        if len(set(verdicts.values())) > 1:
            out.append({
                "property_id": pid,
                "fails_under": sorted(p for p, ok in verdicts.items() if not ok),
                "passes_under": sorted(p for p, ok in verdicts.items() if ok),
                "margins": dict(sorted(margins[pid].items())),
            })
    return out


@node("SINK")
def gap_findings_across(results: Mapping[str, RunResult], packs: Mapping[str, PolicyPack],
                        scenario: Scenario) -> dict[str, list]:
    """Classified gaps per pack, with each finding's cross-pack result attached."""
    from .gaps import classify_run   # local import: keeps gaps.py free of a compare.py cycle
    out: dict[str, list] = {}
    for pack_id, result in results.items():
        ctx = context_for(result)
        findings = classify_run(result, packs[pack_id], ctx["world"], ctx["gm"], scenario)
        for f in findings:
            f.evidence["passes_under_packs"] = passes_under(results, f.violated_property)
            f.evidence["comparator_margins"] = {
                pid: next((p.margin for p in r.properties if p.property_id == f.violated_property), None)
                for pid, r in sorted(results.items())}
        out[pack_id] = findings
    return out
