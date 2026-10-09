"""Agent protocol. Y.3172 node: M."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schemas import PolicyPack, Proposal
from .roles import Inbox


@runtime_checkable
class Agent(Protocol):
    role_id: str
    tier: str

    def observe(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        """Return proposals for this tick. Must be deterministic given (inbox, t, pack)."""
        ...


class ProposalIdFactory:
    """Deterministic proposal ids: no uuid4, no time, so two runs of one seed match byte for byte."""
    def __init__(self, run_id: str = "run"):
        self.run_id = run_id
        self._n = 0

    def next(self, role_id: str, t: int, action_type: str) -> str:
        self._n += 1
        return f"{role_id}:{t:05d}:{action_type}:{self._n:04d}"


def noop(role_id: str, t: int, pid: str, why: str = "no action required this tick") -> Proposal:
    return Proposal(proposal_id=pid, t_minutes=t, actor_role=role_id, action_type="NOOP",
                    params={}, cited_rule_ids=[], reasoning=why, triggered_by_event_ids=[])
