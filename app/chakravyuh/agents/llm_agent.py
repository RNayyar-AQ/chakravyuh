"""Generic role-bound LLM agent returning typed JSON. Y.3172 node: M.

Delegation is explicit (§5.2): every prompt carries an objective, an output schema, the
allowed actions, and explicit boundaries ("you cannot see X; if unsure, ASK").

The agent PROPOSES ONLY. It cannot change the world, and it is not asked whether its action is
legal -- the policy engine decides that. An LLM proposal outside the role's powers is not
filtered here: it goes to the Game Master, which BLOCKs it as `ultra_vires` and logs it. A
filtered-out overreach would be a finding destroyed; a blocked one is a finding recorded.

Every call writes an LLM_TRACE ledger entry (model, prompt sha, raw output, parsed proposal,
latency, tokens). The demo runs in replay mode, so the showcase is identical every time.
"""
from __future__ import annotations

import json
from typing import Optional

from pydantic import ValidationError

from ..audit.ledger import Ledger
from ..audit.trace import llm_trace_payload
from ..llm.client import CacheMiss, LLMClient, extract_json
from ..schemas import PolicyPack, Proposal
from ..y3172 import node
from .base import ProposalIdFactory, noop
from .roles import ROLES, Inbox

PROPOSAL_SCHEMA_HINT = json.dumps({
    "action_type": "one of the allowed actions, or ASK, or NOOP",
    "params": {"area": "string", "...": "action-specific parameters"},
    "cited_rule_ids": ["rule_id that authorises this action"],
    "reasoning": "under 120 words: why this action, on what information",
}, indent=2)

SYSTEM_TEMPLATE = """You are {role_name}. Mandate: {mandate}.
You may ONLY propose these actions: {allowed_actions}.
You see only the messages below; you do NOT know anything else about the world.
Boundaries: {boundaries}
Legal powers you hold (rule_id: summary):
{rules_for_role}
Return JSON matching this schema:
{schema}
Cite rule_ids that authorise your action.
If information is missing, return action_type="ASK" with params.to and params.question.
Do not claim outcomes; you only propose. Keep reasoning under 120 words."""

USER_TEMPLATE = """Current simulated time: T+{t} minutes.

Your inbox (arrival time | event type | details), oldest first:
{inbox}

Actions you have already proposed this run (do not repeat them):
{history}

Propose at most ONE action for this tick. Return only the JSON object."""


@node("M")
class LLMAgent:
    """Role-bound LLM agent. Deterministic via the record/replay cache + temperature 0."""

    tier = "llm"

    def __init__(self, role_id: str, client: Optional[LLMClient] = None,
                 ids: Optional[ProposalIdFactory] = None, ledger: Optional[Ledger] = None,
                 max_actions: int = 12, strict: bool = True):
        self.role_id = role_id
        self.role = ROLES[role_id]
        self.client = client or LLMClient()
        self.ids = ids or ProposalIdFactory()
        self.ledger = ledger
        self.strict = strict          # strict: a replay cache miss aborts the run
        self.max_actions = max_actions
        self.history: list[str] = []
        self.llm_calls = 0
        self.parse_failures = 0
        self.cache_misses = 0

    # -- prompt ------------------------------------------------------------
    def system_prompt(self, pack: PolicyPack) -> str:
        powers = pack.powers_of(self.role_id)
        rules = [r for r in pack.rules if r.actor_role == self.role_id]
        rule_lines = "\n".join(
            f"  - {r.rule_id} [{r.effect}] {r.action_type}: {r.summary or '(no summary)'}"
            + (f" (approval delay {r.approval_delay_min} min)" if r.approval_delay_min else "")
            + (f" (deadline {r.deadline_min} min)" if r.deadline_min else "")
            for r in rules) or "  (none)"
        return SYSTEM_TEMPLATE.format(
            role_name=self.role.name, mandate=self.role.mandate,
            allowed_actions=", ".join(powers + ["ASK", "NOOP"]),
            boundaries=self.role.boundaries, rules_for_role=rule_lines,
            schema=PROPOSAL_SCHEMA_HINT)

    def user_prompt(self, inbox: Inbox, t: int) -> str:
        return USER_TEMPLATE.format(
            t=t, inbox=inbox.as_text(),
            history="\n".join(f"  - {h}" for h in self.history) or "  (none yet)")

    # -- decision ----------------------------------------------------------
    @node("M")
    def observe(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        """One LLM call per tick. Returns at most one proposal; NOOP when nothing is new."""
        if not inbox.items:
            return [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"),
                         "inbox empty: nothing to act on")]
        if len(self.history) >= self.max_actions:
            return [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"),
                         "action budget for this run exhausted")]

        system = self.system_prompt(pack)
        user = self.user_prompt(inbox, t)
        try:
            resp = self.client.complete(user, system=system, schema_name="Proposal")
        except CacheMiss as exc:
            self.cache_misses += 1
            if self.strict:
                raise
            self._trace(system, user, "", None, 0.0, {}, "miss", t, note=str(exc))
            return [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"),
                         "replay cache miss: no recorded decision for this state")]

        self.llm_calls += 1
        proposal = self._parse(resp.text, inbox, t)
        self._trace(system, user, resp.text, proposal.model_dump() if proposal else None,
                    resp.latency_s, resp.tokens, resp.cache_status, t)

        if proposal is None:
            return [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"),
                         "model output could not be parsed into a Proposal")]
        if proposal.action_type == "NOOP":
            return [proposal]
        self.history.append(f"T+{t}: {proposal.action_type} {proposal.params.get('area', '')}")
        return [proposal]

    def _parse(self, text: str, inbox: Inbox, t: int) -> Optional[Proposal]:
        """Parse model JSON into a Proposal. Never repairs the decision, only the envelope."""
        try:
            raw = extract_json(text)
        except ValueError:
            self.parse_failures += 1
            return None
        action = str(raw.get("action_type", "NOOP")).strip().upper()
        params = raw.get("params") if isinstance(raw.get("params"), dict) else {}
        cited = raw.get("cited_rule_ids") or []
        cited = [cited] if isinstance(cited, str) else [str(c) for c in cited]
        # Attribute the proposal to the facts the agent actually holds, so the GM's authentication
        # check and the gap classifier have a trigger chain to walk.
        triggers = self._triggers_for(inbox, params.get("area"))
        try:
            return Proposal(
                proposal_id=self.ids.next(self.role_id, t, action), t_minutes=t,
                actor_role=self.role_id, action_type=action, params=params,
                cited_rule_ids=cited, reasoning=str(raw.get("reasoning", ""))[:2000],
                triggered_by_event_ids=triggers)
        except ValidationError:
            self.parse_failures += 1
            return None

    def _triggers_for(self, inbox: Inbox, area: Optional[str]) -> list[str]:
        """Most recent inbox items about this area (or the latest two overall) as the trigger chain."""
        relevant = [i for i in inbox.items
                    if area is None or i["event"].get("area") == area
                    or (i["event"].get("payload") or {}).get("area") == area]
        chosen = (relevant or inbox.items)[-2:]
        return [i["event"]["event_id"] for i in chosen]

    def _trace(self, system: str, user: str, raw: str, parsed: Optional[dict], latency: float,
               tokens: dict, cache_status: str, t: int, note: str = "") -> None:
        if self.ledger is None:
            return
        payload = llm_trace_payload(
            model=self.client.model, prompt=f"{system}\n\n---\n\n{user}", raw_output=raw,
            parsed=parsed, latency_s=latency, tokens=tokens, retrieved_chunk_ids=[],
            cache_status=cache_status, role=self.role_id)
        if note:
            payload["note"] = note
        self.ledger.append("LLM_TRACE", payload, t)


def build_llm_agents(client: Optional[LLMClient] = None, ledger: Optional[Ledger] = None,
                     ids: Optional[ProposalIdFactory] = None, strict: bool = True,
                     rule_fallback_for: tuple[str, ...] = ("adviser",)) -> dict:
    """Six agents. The adviser proposes nothing, so it stays a rule twin (§10 cut line)."""
    from .rule_agents import TWINS   # local import avoids a cycle at module load
    ids = ids or ProposalIdFactory()
    client = client or LLMClient()
    agents: dict[str, object] = {}
    for role_id in ROLES:
        if role_id in rule_fallback_for:
            agents[role_id] = TWINS[role_id](role_id, ids)
        else:
            agents[role_id] = LLMAgent(role_id, client=client, ids=ids, ledger=ledger, strict=strict)
    return agents
