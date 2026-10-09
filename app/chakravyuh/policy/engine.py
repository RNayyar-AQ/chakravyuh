"""Deterministic policy engine. Y.3172 node: P.

THE LLM NEVER DECIDES LEGALITY OR WORLD STATE (spec §0). This module is pure Python over
compiled rules and the world state.

HARD CONSTRAINT: this module must not import anything from `chakravyuh.llm`, directly or
transitively. `tests/test_engine_purity.py` fails the build if it ever does.

Resolution order (spec §5.4):
  1. powers check          -> ultra vires
  2. authentication check  -> forged-order handling. A pack with no authentication requirement
                              ALLOWS the forged order: that is the vulnerability we measure, not
                              a bug to patch in code.
  3. rule evaluation       -> prohibitions, then permits/obligations, with conditions
  4. reversibility         -> irreversible actions need a human (Y.3173-style)
  5. Verdict(decision, rule_ids, clause_ids, explanation, mode)
"""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from ..schemas import Decision, Event, PolicyPack, Proposal, Rule, Verdict
from ..world.state import WorldState
from ..y3172 import node

# Proposals that are never actions on the world; always permitted.
NON_ACTIONS = frozenset({"NOOP", "ASK", "REPORT_INCIDENT_ACK"})

# Action types whose effects cannot be undone once applied. A pack may override per rule via
# Rule.reversible; this is the default classification.
IRREVERSIBLE_BY_DEFAULT = frozenset({"ORDER_SUSPENSION"})


class ActorView:
    """What one role has actually received by time t. The engine uses it for `event_seen`.

    Carries both the redacted view (what the agent knew) and the authentic flag (what was true),
    because the engine is the Game Master's arm, not an agent: it is entitled to ground truth.
    """

    def __init__(self, role: str, events: Sequence[Event] = (), arrival: Mapping[str, int] | None = None):
        self.role = role
        self.events: list[Event] = list(events)
        self.arrival: dict[str, int] = dict(arrival or {})

    def add(self, event: Event, arrived_t: int) -> None:
        self.events.append(event)
        self.arrival[event.event_id] = arrived_t

    def seen_types(self, t: int) -> set[str]:
        return {e.type for e in self.events if self.arrival.get(e.event_id, e.t_minutes) <= t}

    def seen(self, event_type: str, t: int) -> bool:
        return event_type in self.seen_types(t)

    def seen_authentic(self, event_type: str, t: int) -> bool:
        return any(e.type == event_type and e.authentic
                   and self.arrival.get(e.event_id, e.t_minutes) <= t for e in self.events)

    def first_arrival_of(self, event_type: str) -> Optional[int]:
        ts = [self.arrival.get(e.event_id, e.t_minutes) for e in self.events if e.type == event_type]
        return min(ts) if ts else None

    def by_id(self, event_id: str) -> Optional[Event]:
        for e in self.events:
            if e.event_id == event_id:
                return e
        return None


@node("P")
def evaluate(proposal: Proposal, state: WorldState, pack: PolicyPack,
             view: Optional[ActorView] = None,
             events_by_id: Optional[Mapping[str, Event]] = None) -> Verdict:
    """Decide ALLOW | BLOCK | NEEDS_HUMAN for one proposal. Pure function: no I/O, no randomness."""
    view = view or ActorView(proposal.actor_role)
    events_by_id = events_by_id or {}
    mode = pack.mode

    # ---- 0. non-actions -------------------------------------------------
    if proposal.action_type in NON_ACTIONS:
        return Verdict(proposal_id=proposal.proposal_id, decision=Decision.ALLOW,
                       rule_ids=[], clause_ids=[],
                       explanation=f"{proposal.action_type} is not an action on the world",
                       mode=mode)

    # ---- 1. powers check (ultra vires) ----------------------------------
    powers = pack.powers_of(proposal.actor_role)
    if proposal.action_type not in powers:
        return Verdict(
            proposal_id=proposal.proposal_id, decision=Decision.BLOCK, rule_ids=[], clause_ids=[],
            explanation=(f"ultra_vires: {proposal.actor_role} holds no power to "
                         f"{proposal.action_type} under pack {pack.pack_id}; "
                         f"its powers are {powers or ['(none)']}"),
            mode=mode)

    candidates = pack.rules_for(proposal.actor_role, proposal.action_type)

    # ---- 2. authentication check ----------------------------------------
    auth_rules = [r for r in candidates if r.requires_authenticated_order]
    forged = _triggering_order_is_forged(proposal, view, events_by_id)
    if auth_rules and forged:
        r = auth_rules[0]
        return Verdict(
            proposal_id=proposal.proposal_id, decision=Decision.BLOCK,
            rule_ids=[r.rule_id], clause_ids=list(r.clause_ids),
            explanation=(f"unauthenticated_order: {r.rule_id} requires an authenticated order, "
                         f"and the triggering order failed authentication"),
            mode=mode)

    # ---- 3. rule evaluation ---------------------------------------------
    for rule in candidates:
        if rule.effect == "prohibit" and _conditions_hold(rule, proposal, state, view):
            return Verdict(
                proposal_id=proposal.proposal_id, decision=Decision.BLOCK,
                rule_ids=[rule.rule_id], clause_ids=list(rule.clause_ids),
                explanation=f"prohibited_by_rule: {rule.rule_id} ({rule.summary or 'prohibition'})",
                mode=mode)

    enabling = [r for r in candidates
                if r.effect in ("permit", "oblige") and _conditions_hold(r, proposal, state, view)]
    if not enabling:
        unmet = [(r.rule_id, _unmet_conditions(r, proposal, state, view))
                 for r in candidates if r.effect in ("permit", "oblige")]
        detail = "; ".join(f"{rid}: unmet {keys}" for rid, keys in unmet) or "no permitting rule exists"
        return Verdict(
            proposal_id=proposal.proposal_id, decision=Decision.BLOCK,
            rule_ids=[r.rule_id for r in candidates], clause_ids=[c for r in candidates for c in r.clause_ids],
            explanation=f"preconditions_unmet: {detail}", mode=mode)

    rule = enabling[0]

    # ---- 4. reversibility -> human in the loop --------------------------
    irreversible = (not rule.reversible) or (
        proposal.action_type in IRREVERSIBLE_BY_DEFAULT and not rule.reversible)
    if irreversible:
        return Verdict(
            proposal_id=proposal.proposal_id, decision=Decision.NEEDS_HUMAN,
            rule_ids=[rule.rule_id], clause_ids=list(rule.clause_ids),
            explanation=(f"irreversible_action: {rule.rule_id} permits this but marks it "
                         f"irreversible; human authorisation required before execution"),
            mode=mode)

    # ---- 5. allow --------------------------------------------------------
    return Verdict(
        proposal_id=proposal.proposal_id, decision=Decision.ALLOW,
        rule_ids=[rule.rule_id], clause_ids=list(rule.clause_ids),
        explanation=(f"permitted_by_rule: {rule.rule_id}"
                     + (f" (effective after {rule.approval_delay_min} min approval delay)"
                        if rule.approval_delay_min else "")),
        mode=mode)


def approval_delay_for(proposal: Proposal, pack: PolicyPack, verdict: Verdict) -> int:
    """Minutes the GM must wait before applying effects (the pack's own procedural latency)."""
    delays = [r.approval_delay_min for r in pack.rules if r.rule_id in verdict.rule_ids]
    return max(delays) if delays else 0


def _triggering_order_is_forged(proposal: Proposal, view: ActorView,
                                events_by_id: Mapping[str, Event]) -> bool:
    """True when any event this proposal cites as its trigger is an inauthentic ORDER."""
    for eid in proposal.triggered_by_event_ids:
        ev = events_by_id.get(eid) or view.by_id(eid)
        if ev is not None and ev.type == "ORDER" and not ev.authentic:
            return True
    return False


# ------------------------------------------------------------ condition DSL

def _area_of(proposal: Proposal) -> Optional[str]:
    a = proposal.params.get("area")
    return a if isinstance(a, str) else None


def _condition_results(rule: Rule, proposal: Proposal, state: WorldState,
                       view: ActorView) -> dict[str, bool]:
    """Evaluate each condition key independently so BLOCK explanations can name what failed."""
    t = proposal.t_minutes
    area = _area_of(proposal)
    out: dict[str, bool] = {}

    for key, want in rule.conditions.items():
        if key == "event_seen":
            wanted = [want] if isinstance(want, str) else list(want)
            out[key] = any(view.seen(w, t) for w in wanted)
        elif key == "event_seen_authentic":
            out[key] = view.seen_authentic(want, t)
        elif key == "area_in":
            if want == "any" or area is None:
                out[key] = want == "any"
            elif want == "affected":
                out[key] = area in state.affected_areas
            elif want == "declared":
                out[key] = bool(state.disaster_declared.get(area, False))
            elif want == "cross_border":
                out[key] = area in state.cross_border_areas
            else:
                out[key] = False
        elif key == "after_min":
            out[key] = t >= int(want)
        elif key == "before_min":
            out[key] = t <= int(want)
        elif key == "within_min_of":
            ref = view.first_arrival_of(want["event_type"])
            out[key] = ref is not None and (t - ref) <= int(want["minutes"])
        elif key == "disaster_declared":
            declared = any(state.disaster_declared.values()) if area is None else \
                bool(state.disaster_declared.get(area, False))
            out[key] = declared is bool(want)
        elif key == "order_in_force":
            out[key] = area is not None and area in state.suspended_areas(t)
        elif key == "param_max":
            out[key] = all(_num(proposal.params.get(p)) is not None
                           and _num(proposal.params.get(p)) <= int(lim)
                           for p, lim in want.items())
        elif key == "param_required":
            out[key] = all(proposal.params.get(p) not in (None, "", [], {}) for p in want)
        elif key == "param_in":
            out[key] = all(proposal.params.get(p) in allowed for p, allowed in want.items())
        else:  # unreachable: the compiler rejects unknown keys
            out[key] = False
    return out


def _num(v) -> Optional[float]:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _conditions_hold(rule: Rule, proposal: Proposal, state: WorldState, view: ActorView) -> bool:
    return all(_condition_results(rule, proposal, state, view).values())


def _unmet_conditions(rule: Rule, proposal: Proposal, state: WorldState, view: ActorView) -> list[str]:
    return sorted(k for k, ok in _condition_results(rule, proposal, state, view).items() if not ok)


@node("P")
def obligations_due(pack: PolicyPack, state: WorldState, views: Mapping[str, ActorView],
                    t: int) -> list[dict]:
    """Obligations whose deadline has passed without the obliged action having happened.

    Used by the gap classifier to tell a *policy* gap (no obligation exists at all) from an
    *execution* gap (the obligation existed, the fact arrived, nobody acted).
    """
    out: list[dict] = []
    for rule in pack.rules:
        if rule.effect != "oblige" or rule.deadline_min is None:
            continue
        view = views.get(rule.actor_role)
        if view is None:
            continue
        trigger = rule.conditions.get("event_seen") or rule.conditions.get("event_seen_authentic")
        triggers = [trigger] if isinstance(trigger, str) else list(trigger or [])
        for tr in triggers:
            start = view.first_arrival_of(tr)
            if start is not None and t >= start + rule.deadline_min:
                out.append({"rule_id": rule.rule_id, "actor_role": rule.actor_role,
                            "action_type": rule.action_type, "trigger": tr,
                            "due_at": start + rule.deadline_min, "clause_ids": list(rule.clause_ids)})
    return out
