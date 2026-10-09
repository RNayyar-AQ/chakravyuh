"""P2 gate (spec §10): engine purity, compile errors on bad clauses, ultra vires -> BLOCK."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from chakravyuh.policy.compiler import PackCompileError, compile_pack
from chakravyuh.policy.engine import ActorView, evaluate
from chakravyuh.schemas import Decision, Event, Proposal
from chakravyuh.world.state import build_world

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "chakravyuh/policy/engine.py"


def _imports_of(module: str) -> set[str]:
    """Absolute `chakravyuh.*` module names imported by one module, resolving relative imports."""
    path = ROOT / (module.replace(".", "/") + ".py")
    if not path.exists():
        path = ROOT / module.replace(".", "/") / "__init__.py"
    if not path.exists():
        return set()
    parts = module.split(".")
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names if a.name.startswith("chakravyuh"))
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # relative: resolve against this module's package
                base = parts[: len(parts) - node.level]
                target = ".".join(base + ([node.module] if node.module else []))
            else:
                target = node.module or ""
            if not target.startswith("chakravyuh"):
                continue
            out.add(target)
            # `from x.y import z` may name a submodule rather than an attribute.
            out.update(f"{target}.{a.name}" for a in node.names)
    return out


def _transitive_imports(root_module: str) -> set[str]:
    seen: set[str] = set()
    frontier = [root_module]
    while frontier:
        mod = frontier.pop()
        for dep in _imports_of(mod):
            if dep not in seen:
                seen.add(dep)
                frontier.append(dep)
    return seen


def test_engine_has_no_llm_import():
    """The P node must not be able to reach the LLM, directly OR transitively."""
    direct = _imports_of("chakravyuh.policy.engine")
    assert not any(m.startswith("chakravyuh.llm") for m in direct), sorted(direct)

    reachable = _transitive_imports("chakravyuh.policy.engine")
    offending = sorted(m for m in reachable if m.startswith("chakravyuh.llm"))
    assert not offending, f"engine can transitively reach {offending}"


def test_whole_policy_package_is_llm_free():
    for mod_path in sorted((ROOT / "chakravyuh/policy").glob("*.py")):
        module = f"chakravyuh.policy.{mod_path.stem}"
        reachable = _transitive_imports(module) | _imports_of(module)
        assert not any(m.startswith("chakravyuh.llm") for m in reachable), module


def test_engine_source_mentions_no_model_call():
    src = ENGINE.read_text(encoding="utf-8")
    for forbidden in ("litellm", "openai", "anthropic", "LLMClient", "complete("):
        assert forbidden not in src, f"engine references {forbidden}"


def test_unknown_clause_id_fails_compilation(tmp_path, built_kb):
    pack = {"pack_id": "bad", "jurisdiction": "XX", "version": "1",
            "rules": [{"rule_id": "R1", "clause_ids": ["NO.SUCH.CLAUSE"],
                       "actor_role": "tsp_network", "action_type": "RESTORE_SITE",
                       "effect": "permit"}]}
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(pack))
    with pytest.raises(PackCompileError, match="not in clause store"):
        compile_pack(path)


def test_rule_without_any_clause_fails_compilation(tmp_path, built_kb):
    pack = {"pack_id": "bad2", "jurisdiction": "XX", "version": "1",
            "rules": [{"rule_id": "R1", "clause_ids": [], "actor_role": "tsp_network",
                       "action_type": "RESTORE_SITE", "effect": "permit"}]}
    path = tmp_path / "bad2.yaml"
    path.write_text(yaml.safe_dump(pack))
    with pytest.raises(PackCompileError, match="must cite law"):
        compile_pack(path)


def test_unknown_condition_key_fails_compilation(tmp_path, built_kb):
    pack = {"pack_id": "bad3", "jurisdiction": "XX", "version": "1",
            "rules": [{"rule_id": "R1", "clause_ids": ["IN.UL.DISASTER"],
                       "actor_role": "tsp_network", "action_type": "RESTORE_SITE",
                       "effect": "permit", "conditions": {"eevent_seen": "LANDFALL"}}]}
    path = tmp_path / "bad3.yaml"
    path.write_text(yaml.safe_dump(pack))
    with pytest.raises(PackCompileError, match="unknown condition keys"):
        compile_pack(path)


def test_duplicate_rule_id_fails_compilation(tmp_path, built_kb):
    rule = {"rule_id": "R1", "clause_ids": ["IN.UL.DISASTER"], "actor_role": "tsp_network",
            "action_type": "RESTORE_SITE", "effect": "permit"}
    path = tmp_path / "bad4.yaml"
    path.write_text(yaml.safe_dump({"pack_id": "b4", "jurisdiction": "XX", "version": "1",
                                    "rules": [rule, dict(rule)]}))
    with pytest.raises(PackCompileError, match="duplicate rule_id"):
        compile_pack(path)


def test_all_shipped_packs_compile(packs):
    assert set(packs) == {"india_current", "bangladesh", "fcc_mdri"}
    for pack in packs.values():
        assert pack.rules


# ------------------------------------------------------------------ decisions

def _world():
    w = build_world(["A", "B"], {"A": 10, "B": 10}, {"A": ["bn"]}, cross_border_areas=["B"])
    w.affected_areas = ["A"]
    w.disaster_declared["A"] = True
    return w


def _proposal(role: str, action: str, **params) -> Proposal:
    return Proposal(proposal_id=f"{role}:{action}", t_minutes=60, actor_role=role,
                    action_type=action, params=params, reasoning="test")


def test_ultra_vires_is_blocked(india_pack):
    # The alerting authority has no power to suspend service under any pack.
    v = evaluate(_proposal("sdma_alerts", "SUSPEND_SERVICE", area="A"), _world(), india_pack)
    assert v.decision is Decision.BLOCK
    assert v.explanation.startswith("ultra_vires")


def test_fcc_pack_has_no_suspension_power_at_all(packs):
    v = evaluate(_proposal("competent_authority", "ORDER_SUSPENSION", area="A", duration_min=60,
                           reasons="x"), _world(), packs["fcc_mdri"])
    assert v.decision is Decision.BLOCK
    assert v.explanation.startswith("ultra_vires")


def test_noop_and_ask_are_always_allowed(india_pack):
    for action in ("NOOP", "ASK"):
        v = evaluate(_proposal("cert_in", action), _world(), india_pack)
        assert v.decision is Decision.ALLOW


def test_irreversible_action_needs_human(india_pack):
    v = evaluate(_proposal("competent_authority", "ORDER_SUSPENSION", area="A",
                           duration_min=360, reasons="unrest"), _world(), india_pack)
    assert v.decision is Decision.NEEDS_HUMAN
    assert "irreversible" in v.explanation


def test_param_max_is_enforced(india_pack):
    """r.2(4): no more than 15 days (21600 minutes) in one order."""
    v = evaluate(_proposal("competent_authority", "ORDER_SUSPENSION", area="A",
                           duration_min=99999, reasons="unrest"), _world(), india_pack)
    assert v.decision is Decision.BLOCK
    assert "param_max" in v.explanation


def test_forged_order_allowed_under_india_blocked_under_bangladesh(packs):
    """The authentication gap, stated as a test: same facts, two packs, two outcomes."""
    forged = Event(event_id="ev-forged", t_minutes=30, type="ORDER", area="A", authentic=False,
                   payload={"area": "A"}, visible_to=["tsp_network"])
    view = ActorView("tsp_network")
    view.add(forged, 30)
    events = {"ev-forged": forged}
    proposal = Proposal(proposal_id="p1", t_minutes=60, actor_role="tsp_network",
                        action_type="SUSPEND_SERVICE", params={"area": "A"},
                        reasoning="order received", triggered_by_event_ids=["ev-forged"])

    india = evaluate(proposal, _world(), packs["india_current"], view=view, events_by_id=events)
    assert india.decision is Decision.ALLOW, "India pack imposes no authentication duty"

    bd = evaluate(proposal, _world(), packs["bangladesh"], view=view, events_by_id=events)
    assert bd.decision is Decision.BLOCK
    assert bd.explanation.startswith("unauthenticated_order")


def test_cross_border_alert_prohibited_under_india(packs):
    w = _world()
    view = ActorView("sdma_alerts")
    warn = Event(event_id="w1", t_minutes=0, type="IMD_WARNING", visible_to=["sdma_alerts"])
    view.add(warn, 0)
    p = _proposal("sdma_alerts", "ISSUE_CAP_ALERT", area="B", languages=["bn"])
    v = evaluate(p, w, packs["india_current"], view=view)
    assert v.decision is Decision.BLOCK
    assert "IN.R.NO_CROSS_BORDER_ALERT" in v.rule_ids


def test_advisory_mode_logs_but_executes(india_pack):
    advisory = india_pack.model_copy(update={"mode": "advisory"})
    v = evaluate(_proposal("sdma_alerts", "SUSPEND_SERVICE", area="A"), _world(), advisory)
    assert v.decision is Decision.BLOCK
    assert v.executes, "in advisory mode a blocked action still executes, and the breach is logged"


def test_verdict_always_cites_rules_when_it_blocks_on_one(india_pack):
    w = _world()
    view = ActorView("sdma_alerts")
    view.add(Event(event_id="w1", t_minutes=0, type="IMD_WARNING", visible_to=["sdma_alerts"]), 0)
    v = evaluate(_proposal("sdma_alerts", "ISSUE_CAP_ALERT", area="B", languages=["bn"]),
                 w, india_pack, view=view)
    assert v.rule_ids and v.clause_ids
