"""Game Master: resolves proposals in deterministic order. Y.3172 node: D."""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from ..audit.ledger import Ledger
from ..policy.engine import ActorView, approval_delay_for, evaluate
from ..schemas import Decision, Event, PolicyPack, Proposal, Verdict
from ..world import dynamics
from ..world.state import WorldState
from ..agents.roles import ROLES
from ..y3172 import node


class HumanGate:
    """Human-in-the-loop stub for NEEDS_HUMAN verdicts (§5.4 step 4)."""
    def __init__(self, mode: str = "batch", auto_approve_after_min: int = 30):
        self.mode = mode
        self.auto_approve_after_min = auto_approve_after_min
        self.pending: dict[str, dict] = {}
        self.decisions: list[dict] = []

    def hold(self, proposal: Proposal, verdict: Verdict, t: int) -> None:
        self.pending[proposal.proposal_id] = {
            "proposal": proposal, "verdict": verdict, "held_at": t,
            "due_at": t + self.auto_approve_after_min,
        }

    def approve(self, proposal_id: str, approver: str = "human") -> None:
        held = self.pending.pop(proposal_id, None)
        if held is not None:
            self.decisions.append({"proposal_id": proposal_id, "approved": True,
                                   "approver": approver, "at": held["due_at"]})

    def release_due(self, t: int) -> list[tuple[Proposal, Verdict, str]]:
        """Return (proposal, verdict, approver) for everything cleared to execute at time t."""
        if self.mode == "deny":
            return []
        out = []
        for _pid, held in sorted(self.pending.items()):
            if self.mode == "batch" and t >= held["due_at"]:
                out.append((held["proposal"], held["verdict"], "auto_batch"))
        for p, _v, approver in out:
            self.pending.pop(p.proposal_id, None)
            self.decisions.append({"proposal_id": p.proposal_id, "approved": True,
                                   "approver": approver, "at": t})
        return out


@node("D")
class GameMaster:
    """The single authority over world state. No agent holds a reference to the world."""
    def __init__(self, world: WorldState, pack: PolicyPack, ledger: Ledger,
                 human_gate: Optional[HumanGate] = None,
                 agents: Optional[Mapping[str, object]] = None):
        self.agents = dict(agents or {})
        self.world = world
        self.pack = pack
        self.ledger = ledger
        self.gate = human_gate or HumanGate()
        self.views: dict[str, ActorView] = {rid: ActorView(rid) for rid in ROLES}
        self.events_by_id: dict[str, Event] = {}
        self.verdicts: list[Verdict] = []
        self.effects: list[dict] = []
        self.deferred: list[tuple[int, Proposal, Verdict]] = []
        self.forged_executions: list[dict] = []
        self._pending_derived: list[Event] = []
        self._rule_clauses: Optional[dict[str, list[str]]] = None

    def register_event(self, event: Event) -> None:
        """Record the full event (with ground truth) for the engine's authentication check."""
        self.events_by_id[event.event_id] = event

    def record_delivery(self, delivery) -> None:
        """An event has arrived at a role: update that role's view and log the delivery."""
        self.views[delivery.role].add(delivery.event, delivery.arrives_t)
        self.ledger.append("DELIVERY", delivery.ledger_payload(), delivery.arrives_t)

    def apply_exogenous(self, event: Event, t: int) -> dict:
        changed = dynamics.apply_exogenous(self.world, event)
        self.ledger.append("EVENT", {"event": event.model_dump(), "world_change": changed,
                                     "authentic": event.authentic}, t)
        return changed

    def _clauses_for_rules(self, rule_ids: Sequence[str]) -> list[str]:
        """Clause ids the given rules cite, in the pack's order, de-duplicated."""
        if self._rule_clauses is None:
            self._rule_clauses = {r.rule_id: list(r.clause_ids) for r in self.pack.rules}
        out: list[str] = []
        for rule_id in rule_ids:
            for cid in self._rule_clauses.get(rule_id, ()):
                if cid not in out:
                    out.append(cid)
        return out

    @node("D")
    def resolve_tick(self, proposals: list[Proposal], t: int) -> list[Verdict]:
        """Resolve every proposal for this tick in (t, role priority, proposal_id) order."""
        ordered = sorted(proposals, key=lambda p: (p.t_minutes,
                                                   ROLES[p.actor_role].priority if p.actor_role in ROLES else 99,
                                                   p.proposal_id))
        out: list[Verdict] = []
        for proposal in ordered:
            proposal.cited_clause_ids = self._clauses_for_rules(proposal.cited_rule_ids)
            self.ledger.append("PROPOSAL", proposal.model_dump(), t)
            verdict = evaluate(proposal, self.world, self.pack,
                               view=self.views.get(proposal.actor_role),
                               events_by_id=self.events_by_id)
            self.ledger.append("VERDICT", verdict.model_dump(), t)
            self.verdicts.append(verdict)
            out.append(verdict)
            self._notify(proposal, verdict)

            if verdict.decision is Decision.NEEDS_HUMAN:
                self.gate.hold(proposal, verdict, t)
                self.ledger.append("EFFECT", {"proposal_id": proposal.proposal_id,
                                              "status": "held_for_human",
                                              "gate_mode": self.gate.mode}, t)
                continue

            if not verdict.executes:
                continue

            delay = approval_delay_for(proposal, self.pack, verdict)
            if delay > 0:
                self.deferred.append((t + delay, proposal, verdict))
                self.ledger.append("EFFECT", {"proposal_id": proposal.proposal_id,
                                              "status": "deferred_for_approval_delay",
                                              "effective_t": t + delay,
                                              "delay_min": delay}, t)
                continue

            self._execute(proposal, verdict, t)
        return out

    def _notify(self, proposal: Proposal, verdict: Verdict) -> None:
        """Tell the proposing agent what happened, if it cares to know."""
        agent = self.agents.get(proposal.actor_role)
        hook = getattr(agent, "on_verdict", None)
        if callable(hook):
            hook(proposal, verdict)

    def release_deferred(self, t: int) -> None:
        """Apply actions whose pack-mandated approval delay has now elapsed."""
        still: list[tuple[int, Proposal, Verdict]] = []
        for eff_t, proposal, verdict in sorted(self.deferred, key=lambda x: (x[0], x[1].proposal_id)):
            if eff_t <= t:
                self._execute(proposal.model_copy(update={"t_minutes": t}), verdict, t)
            else:
                still.append((eff_t, proposal, verdict))
        self.deferred = still

    def release_human_gate(self, t: int) -> None:
        for proposal, verdict, approver in self.gate.release_due(t):
            allowed = verdict.model_copy(update={
                "decision": Decision.ALLOW,
                "explanation": f"{verdict.explanation} | released by human gate ({approver})"})
            self.ledger.append("VERDICT", allowed.model_dump(), t)
            self._execute(proposal.model_copy(update={"t_minutes": t}), allowed, t)

    def _execute(self, proposal: Proposal, verdict: Verdict, t: int) -> None:
        """Apply an executing action to the world and record whether a forged order drove it."""
        trigger_authentic = self._trigger_authentic(proposal)
        effect, derived = dynamics.apply_action(self.world, proposal, verdict,
                                                trigger_authentic=trigger_authentic)
        effect["proposal_id"] = proposal.proposal_id
        effect["rule_ids"] = list(verdict.rule_ids)
        effect["clause_ids"] = list(verdict.clause_ids)
        effect["trigger_authentic"] = trigger_authentic
        self.effects.append(effect)
        self.ledger.append("EFFECT", effect, t)

        if not trigger_authentic:
            self.forged_executions.append({
                "proposal_id": proposal.proposal_id, "action_type": proposal.action_type,
                "actor_role": proposal.actor_role, "t": t,
                "triggered_by": list(proposal.triggered_by_event_ids),
                "rule_ids": list(verdict.rule_ids), "clause_ids": list(verdict.clause_ids),
                "reversible": proposal.action_type not in ("NOOP", "ASK"),
            })

        for ev in derived:
            self.register_event(ev)
            self._pending_derived.append(ev)

    def take_derived(self) -> list[Event]:
        """Derived events produced since the last call; the runner publishes them onto the bus."""
        out, self._pending_derived = list(self._pending_derived), []
        return out

    def _trigger_authentic(self, proposal: Proposal) -> bool:
        for eid in proposal.triggered_by_event_ids:
            ev = self.events_by_id.get(eid)
            if ev is not None and ev.type == "ORDER" and not ev.authentic:
                return False
        return True

    def verdict_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self.verdicts:
            counts[v.decision.value] = counts.get(v.decision.value, 0) + 1
        return counts

    def blocks_by_reason(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in self.verdicts:
            if v.decision is Decision.BLOCK:
                reason = v.explanation.split(":", 1)[0]
                out[reason] = out.get(reason, 0) + 1
        return out
