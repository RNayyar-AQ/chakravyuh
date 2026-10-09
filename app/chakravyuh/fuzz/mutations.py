"""Mutation families applied to a base scenario. Y.3172 node: SRC."""
from __future__ import annotations


from ..schemas import Event
from ..sim.events import Scenario
from ..y3172 import node

FAMILIES = {
    "forged_order": "An order arrives that no competent authority issued (authentic=False)",
    "delay": "A fact reaches a role later than it did in the base scenario",
    "rumour": "An unverified claim enters an inbox and nothing in the world changes",
    "damage": "Physical damage is heavier or reaches a new area",
    "shift": "A scenario event moves earlier or later in the timeline",
}


def _clone(scenario: Scenario) -> Scenario:
    return scenario.model_copy(deep=True)


@node("SRC")
def shift_event(scenario: Scenario, event_id: str, dt: int) -> tuple[Scenario, dict]:
    """Move one event in time. Release order changes, so who-knows-what-when changes with it."""
    s = _clone(scenario)
    for e in s.events:
        if e.event_id == event_id:
            e.t_minutes = max(0, min(scenario.horizon_min, e.t_minutes + dt))
            return s, {"family": "shift", "op": "shift_event",
                       "args": {"event_id": event_id, "dt": dt}, "new_t": e.t_minutes}
    return s, {"family": "shift", "op": "shift_event",
               "args": {"event_id": event_id, "dt": dt}, "note": "event_id not present; no-op"}


@node("SRC")
def delay_channel(scenario: Scenario, role: str, dt: int) -> tuple[Scenario, dict]:
    """Add latency to one role's channel. This is the mutation that manufactures coordination gaps."""
    s = _clone(scenario)
    s.channel_latency_min[role] = max(0, s.channel_latency_min.get(role, s.default_latency_min) + dt)
    return s, {"family": "delay", "op": "delay_channel", "args": {"role": role, "dt": dt},
               "new_latency_min": s.channel_latency_min[role]}


@node("SRC")
def delay_event_for_role(scenario: Scenario, event_id: str, role: str, dt: int) -> tuple[Scenario, dict]:
    """Delay one fact for one role: the finest-grained way to make information uneven."""
    s = _clone(scenario)
    for e in s.events:
        if e.event_id == event_id:
            e.delay_by_role[role] = max(0, e.delay_by_role.get(role, 0) + dt)
            return s, {"family": "delay", "op": "delay_event_for_role",
                       "args": {"event_id": event_id, "role": role, "dt": dt},
                       "new_delay_min": e.delay_by_role[role]}
    return s, {"family": "delay", "op": "delay_event_for_role",
               "args": {"event_id": event_id, "role": role, "dt": dt},
               "note": "event_id not present; no-op"}


@node("SRC")
def inject_rumour(scenario: Scenario, area: str, t: int, seq: int = 0) -> tuple[Scenario, dict]:
    """Add an unverified claim visible to the competent authority. No world effect by construction."""
    s = _clone(scenario)
    eid = f"fz-rumour-{area}-{t}-{seq}"
    s.events.append(Event(
        event_id=eid, t_minutes=max(0, t), type="RUMOUR", area=area,
        payload={"claim": f"Unverified reports of unrest in {area}", "source": "unverified",
                 "synthetic_content": True,
                 "truth": {"verified": False, "note": "injected by fuzzer; no world effect"}},
        visible_to=["competent_authority"], authentic=True))
    return s, {"family": "rumour", "op": "inject_rumour",
               "args": {"area": area, "t": t, "seq": seq}, "created_event_id": eid}


@node("SRC")
def inject_forged_order(scenario: Scenario, area: str, t: int, action: str = "SUSPEND_SERVICE",
                        issuer_claimed: str = "Home Department (claimed)",
                        duration_min: int = 360, seq: int = 0) -> tuple[Scenario, dict]:
    """Add an order no authority issued. `authentic=False` is ground truth no agent can read."""
    s = _clone(scenario)
    eid = f"fz-forged-{area}-{t}-{seq}"
    s.events.append(Event(
        event_id=eid, t_minutes=max(0, t), type="ORDER", area=area, claimed_issuer=issuer_claimed,
        authentic=False,
        payload={"action": action, "area": area, "duration_min": duration_min,
                 "exempt_priority_slice": False, "reasons": "public order (claimed)",
                 "channel": "nodal officer email",
                 "truth": {"forged": True, "note": "injected by fuzzer; no competent authority issued this"}},
        visible_to=["tsp_network"]))
    return s, {"family": "forged_order", "op": "inject_forged_order",
               "args": {"area": area, "t": t, "action": action,
                        "issuer_claimed": issuer_claimed, "duration_min": duration_min, "seq": seq},
               "created_event_id": eid}


@node("SRC")
def escalate_damage(scenario: Scenario, area: str, t: int, cells_down: int = 6,
                    seq: int = 0) -> tuple[Scenario, dict]:
    """Add a damage report for an area, which also marks that area affected."""
    s = _clone(scenario)
    eid = f"fz-damage-{area}-{t}-{seq}"
    s.events.append(Event(
        event_id=eid, t_minutes=max(0, t), type="DAMAGE_REPORT", area=area,
        payload={"note": f"Escalated damage in {area}", "cells_down": cells_down,
                 "truth": {"area": area, "cells_down": cells_down}},
        visible_to=["tsp_network", "sdma_alerts", "competent_authority"]))
    return s, {"family": "damage", "op": "escalate_damage",
               "args": {"area": area, "t": t, "cells_down": cells_down, "seq": seq},
               "created_event_id": eid}


MUTATORS = {
    "shift_event": shift_event,
    "delay_channel": delay_channel,
    "delay_event_for_role": delay_event_for_role,
    "inject_rumour": inject_rumour,
    "inject_forged_order": inject_forged_order,
    "escalate_damage": escalate_damage,
}


@node("SRC")
def apply_mutations(scenario: Scenario, mutations: list[dict]) -> Scenario:
    """Replay a mutation list onto the base scenario. This is what makes a FailureCard reproducible."""
    s = scenario
    for i, m in enumerate(mutations):
        op = m.get("op")
        fn = MUTATORS.get(op)
        if fn is None:
            raise ValueError(f"unknown mutation op {op!r} at index {i}")
        args = m.get("args")
        if not isinstance(args, dict):
            raise ValueError(f"mutation {i} ({op}) has no `args`; it cannot be replayed")
        s, _ = fn(s, **args)
    return s
