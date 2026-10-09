"""Classify a property violation as policy | coordination | execution. Y.3172 node: SINK."""
from __future__ import annotations

from typing import Optional

from ..schemas import GapFinding, PolicyPack, PropertyResult
from ..world.state import WorldState
from ..y3172 import node

DOMAIN = "Emergency telecom"

PREVENTING_ACTION = {
    "P1": ("PRIORITISE_RELIEF_SLICE", ("tsp_network",)),
    "P2": ("SUSPEND_SERVICE", ("tsp_network",)),
    "P3": ("ISSUE_CAP_ALERT", ("sdma_alerts", "neighbour_authority")),
    "P4": ("ENABLE_ROAMING", ("tsp_network", "neighbour_authority")),
}

ENABLING_FACTS = {
    "P1": ("ORDER", "LANDFALL", "DAMAGE_REPORT", "DISASTER_DECLARED"),
    "P2": ("SUSPICIOUS_ORDER", "INCIDENT_REPORT"),
    "P3": ("IMD_WARNING", "LANDFALL", "CROSS_BORDER_REQUEST", "DAMAGE_REPORT"),
    "P4": ("LANDFALL", "DAMAGE_REPORT", "ORDER_DISASTER_ROAMING", "CROSS_BORDER_REQUEST"),
}


@node("SINK")
def classify(result: PropertyResult, pack: PolicyPack, world: WorldState, gm,
             scenario=None, run_id: str = "") -> Optional[GapFinding]:
    """Classify one violated property. Returns None for a property that passed."""
    if result.passed:
        return None
    pid = result.property_id

    if pid == "P2":
        return _classify_p2(result, pack, world, gm, run_id)
    if pid == "P1":
        return _classify_p1(result, pack, world, gm, run_id)
    return _classify_timing(result, pack, world, gm, scenario, run_id)


def _enabling_rules(pack: PolicyPack, action_type: str, roles: tuple[str, ...]) -> list:
    return [r for r in pack.rules
            if r.action_type == action_type and r.effect in ("permit", "oblige")
            and r.actor_role in roles]


def _prohibiting_rules(pack: PolicyPack, action_type: str, roles: tuple[str, ...]) -> list:
    return [r for r in pack.rules
            if r.action_type == action_type and r.effect == "prohibit" and r.actor_role in roles]


def _finding(pid: str, gap_class: str, statement: str, instance: str, clause_ids: list[str],
             rule_ids: list[str], run_id: str, evidence: dict) -> GapFinding:
    return GapFinding(
        gap_id=f"{pid}-{gap_class}-{instance.replace(' ', '')}"[:80],
        violated_property=pid, gap_class=gap_class, domain=DOMAIN, statement=statement,
        instance=instance, responsible_clause_ids=sorted(set(clause_ids)),
        responsible_rule_ids=sorted(set(rule_ids)), evidence_run_id=run_id, evidence=evidence)


def _classify_p2(result, pack, world, gm, run_id) -> GapFinding:
    """P2: an irreversible act executed on a forged order."""
    action, roles = PREVENTING_ACTION["P2"]
    auth_rules = [r for r in pack.rules
                  if r.action_type == action and r.requires_authenticated_order]
    executions = result.detail.get("executions", [])
    areas = sorted({e.get("area") for e in executions if e.get("area")})
    instance = f"India ({', '.join(areas)})" if areas else "India"

    if not auth_rules:
        acting = _enabling_rules(pack, action, roles)
        return _finding(
            "P2", "policy",
            ("No instrument requires an operator to authenticate a service-suspension direction "
             "before giving effect to it, so a forged direction executes exactly like a genuine "
             "one and the irreversible act is complete before any verification occurs."),
            instance,
            [c for r in acting for c in r.clause_ids],
            [r.rule_id for r in acting], run_id,
            {"forged_executions": executions,
             "rules_governing_compliance": [r.rule_id for r in acting],
             "rules_requiring_authentication": []})

    view = gm.views.get("tsp_network")
    saw_flag = any(view.seen(f, world.t_minutes) for f in ENABLING_FACTS["P2"]) if view else False
    if not saw_flag:
        return _finding(
            "P2", "coordination",
            ("An authentication duty exists, but the operator was never told the direction was "
             "suspect: the forgery flag never reached it, so the duty had nothing to bite on."),
            instance, [c for r in auth_rules for c in r.clause_ids],
            [r.rule_id for r in auth_rules], run_id,
            {"forged_executions": executions, "tsp_saw_forgery_flag": False})
    return _finding(
        "P2", "execution",
        ("An authentication duty exists and the operator had been warned, and it still gave "
         "effect to the unauthenticated direction."),
        instance, [c for r in auth_rules for c in r.clause_ids],
        [r.rule_id for r in auth_rules], run_id,
        {"forged_executions": executions, "tsp_saw_forgery_flag": True})


def _classify_p1(result, pack, world, gm, run_id) -> GapFinding:
    """P1: relief traffic went unreachable in a suspended area."""
    per_area = result.detail.get("per_area", {})
    worst = sorted(per_area.items(), key=lambda kv: kv[1].get("pct_relief_reachable", 100.0))
    area_label = worst[0][0].split("@")[0] if worst else "n/a"
    instance = f"India ({area_label})"

    carve_out = _prohibiting_rules(pack, "SUSPEND_SERVICE", ("tsp_network",))
    obliged_priority = [r for r in pack.rules
                        if r.action_type == "PRIORITISE_RELIEF_SLICE" and r.effect == "oblige"]

    if not carve_out and not obliged_priority:
        permits = _enabling_rules(pack, "PRIORITISE_RELIEF_SLICE", ("tsp_network",))
        return _finding(
            "P1", "policy",
            ("A suspension direction carries no mandatory carve-out for relief and emergency "
             "traffic, and priority routing is permitted rather than obliged, so a lawful "
             "suspension can switch off the very traffic the response depends on."),
            instance, [c for r in permits for c in r.clause_ids],
            [r.rule_id for r in permits], run_id,
            {"per_area": per_area, "prohibitions_on_non_exempt_suspension": [],
             "obligations_to_prioritise": []})

    view = gm.views.get("tsp_network")
    saw = any(view.seen(f, world.t_minutes) for f in ENABLING_FACTS["P1"]) if view else False
    gap_class = "execution" if saw else "coordination"
    rules = carve_out + obliged_priority
    return _finding(
        "P1", gap_class,
        ("A carve-out or priority obligation exists, "
         + ("and the operator had the facts it needed, and relief traffic still went unreachable."
            if saw else "but the operator never received the fact that would trigger it.")),
        instance, [c for r in rules for c in r.clause_ids], [r.rule_id for r in rules], run_id,
        {"per_area": per_area, "tsp_had_trigger_fact": saw})


def _classify_timing(result, pack, world, gm, scenario, run_id) -> GapFinding:
    """P3/P4: an area was alerted or roamed too late, or never."""
    pid = result.property_id
    action, roles = PREVENTING_ACTION[pid]
    missed = result.detail.get("areas_missed", [])
    per_area = result.detail.get("per_area", {})
    threshold = result.detail.get("threshold_min")

    if missed:
        focus = sorted(missed)[0]
    else:
        focus = max(per_area, key=lambda a: per_area[a].get("delay_min", 0)) if per_area else "n/a"
    cross_border = focus in world.cross_border_areas
    instance = f"India-Bangladesh ({focus})" if cross_border else f"India ({focus})"

    enabling = _enabling_rules(pack, action, roles)
    prohibiting = _prohibiting_rules(pack, action, roles)

    serviceable = []
    for r in enabling:
        scope = r.conditions.get("area_in")
        if scope == "cross_border" and not cross_border:
            continue
        if scope == "affected" and cross_border:
            continue
        if cross_border and r.actor_role != "neighbour_authority":
            continue
        if not cross_border and r.actor_role == "neighbour_authority":
            continue
        serviceable.append(r)

    blocked_here = [r for r in prohibiting
                    if r.conditions.get("area_in") == "cross_border" and cross_border]

    if not serviceable or blocked_here:
        statement = (
            f"No standing cross-border trigger: no instrument empowers any actor to "
            f"{_verb(action)} across the border in time, and the domestic alerting/roaming power "
            f"is scoped to domestic areas only."
            if cross_border else
            f"No actor is empowered to {_verb(action)} for this area within the threshold; the "
            f"power exists only on conditions this situation does not satisfy.")
        rules = blocked_here or enabling
        return _finding(pid, "policy", statement, instance,
                        [c for r in rules for c in r.clause_ids], [r.rule_id for r in rules],
                        run_id, {"per_area": per_area, "areas_missed": missed,
                                 "threshold_min": threshold,
                                 "prohibited_by": [r.rule_id for r in blocked_here],
                                 "enabling_rules": [r.rule_id for r in enabling]})

    arrivals: dict[str, Optional[int]] = {}
    for role in sorted({r.actor_role for r in serviceable}):
        view = gm.views.get(role)
        if view is None:
            continue
        arrivals[role] = _first_arrival_about(view, ENABLING_FACTS[pid], focus)

    base = world.first_warning_t if pid == "P3" else world.landfall_t
    base = 0 if base is None else base
    in_time = [role for role, at in arrivals.items()
               if at is not None and threshold is not None and (at - base) <= threshold]

    if not in_time:
        return _finding(
            pid, "coordination",
            (f"The power to {_verb(action)} exists and reaches this area, but the fact that "
             f"triggers it reached the empowered authority after the threshold had already "
             f"passed: the delay is in the channel, not in the law."),
            instance, [c for r in serviceable for c in r.clause_ids],
            [r.rule_id for r in serviceable], run_id,
            {"per_area": per_area, "areas_missed": missed, "threshold_min": threshold,
             "first_enabling_fact_arrival_by_role": arrivals, "baseline_t": base,
             "latency_by_role": getattr(gm, "latency_by_role", {})})

    return _finding(
        pid, "execution",
        (f"The power to {_verb(action)} exists, reaches this area, and the triggering fact "
         f"arrived in time, and the empowered actor still did not act within the threshold."),
        instance, [c for r in serviceable for c in r.clause_ids],
        [r.rule_id for r in serviceable], run_id,
        {"per_area": per_area, "areas_missed": missed, "threshold_min": threshold,
         "first_enabling_fact_arrival_by_role": arrivals, "roles_informed_in_time": in_time,
         "baseline_t": base})


def _event_mentions_area(event, area: str) -> bool:
    """True when an event is about this area, by its own field or by any area list in its payload."""
    if event.area == area:
        return True
    payload = event.payload or {}
    if payload.get("area") == area:
        return True
    for key in ("areas", "areas_at_risk", "cross_border_areas"):
        v = payload.get(key)
        if isinstance(v, list) and area in v:
            return True
    return False


def _first_arrival_about(view, fact_types: tuple[str, ...], area: str) -> Optional[int]:
    """Earliest arrival, at this role, of one of these fact types concerning this area."""
    times = [view.arrival.get(e.event_id, e.t_minutes) for e in view.events
             if e.type in fact_types and _event_mentions_area(e, area)]
    return min(times) if times else None


def _verb(action_type: str) -> str:
    return {"ISSUE_CAP_ALERT": "issue a public alert",
            "ENABLE_ROAMING": "enable disaster roaming",
            "PRIORITISE_RELIEF_SLICE": "prioritise relief traffic",
            "SUSPEND_SERVICE": "give effect to a suspension"}.get(action_type, action_type)


@node("SINK")
def classify_run(result, pack: PolicyPack, world: WorldState, gm, scenario=None) -> list[GapFinding]:
    """Classify every violated property in a finished run."""
    out = []
    for prop in result.properties:
        finding = classify(prop, pack, world, gm, scenario, result.run_id)
        if finding is not None:
            out.append(finding)
    return out
