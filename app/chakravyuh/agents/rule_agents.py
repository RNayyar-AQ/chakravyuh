"""Deterministic rule-based twin of each role. Y.3172 node: M."""
from __future__ import annotations

from typing import Optional

from ..schemas import PolicyPack, Proposal
from ..y3172 import node
from .base import ProposalIdFactory, noop
from .roles import ROLES, Inbox


class RuleAgent:
    """Base twin: tracks what it has already done so it does not re-propose every tick."""
    tier = "rule"

    def __init__(self, role_id: str, ids: Optional[ProposalIdFactory] = None):
        self.role_id = role_id
        self.role = ROLES[role_id]
        self.ids = ids or ProposalIdFactory()
        self.done: set[str] = set()
        self._pending_key: Optional[str] = None
        self._key_of: dict[str, str] = {}
        self._blocked_at: dict[str, int] = {}
        self._inbox_len = 0

    def _once(self, key: str) -> bool:
        """True the first time only. Keeps the twin from spamming the same proposal each tick."""
        if key in self.done:
            return False
        self.done.add(key)
        self._pending_key = key
        return True

    def _p(self, t: int, action_type: str, params: dict, rules: list[str], why: str,
           triggers: list[str]) -> Proposal:
        pid = self.ids.next(self.role_id, t, action_type)
        if self._pending_key is not None:
            self._key_of[pid] = self._pending_key
            self._pending_key = None
        return Proposal(proposal_id=pid, t_minutes=t,
                        actor_role=self.role_id, action_type=action_type, params=params,
                        cited_rule_ids=rules, reasoning=why, triggered_by_event_ids=triggers)

    def on_verdict(self, proposal: Proposal, verdict) -> None:
        """Let the twin retry what was refused as "not yet", but not what it may never do."""
        key = self._key_of.get(proposal.proposal_id)
        if key is None or verdict.decision.value != "BLOCK":
            return
        if not verdict.explanation.startswith(("preconditions_unmet", "unauthenticated_order")):
            return
        self.done.discard(key)
        self._blocked_at[key] = self._inbox_len

    def _rule_ids(self, pack: PolicyPack, action_type: str) -> list[str]:
        return [r.rule_id for r in pack.rules_for(self.role_id, action_type)]

    @node("M")
    def observe(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        """Record how much the twin knows, then decide. Subclasses override _decide."""
        self._inbox_len = len(inbox.items)
        return self._decide(inbox, t, pack)

    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        raise NotImplementedError


@node("M")
class CompetentAuthorityTwin(RuleAgent):
    """Orders what the law lets it order, as soon as it hears something that justifies it."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        out: list[Proposal] = []
        powers = pack.powers_of(self.role_id)
        seen = inbox.types_seen()

        if "DECLARE_DISASTER" in powers:
            for etype in ("IMD_WARNING", "LANDFALL"):
                for item in inbox.all_of(etype):
                    for area in _areas_of(item):
                        if self._once(f"declare:{area}"):
                            out.append(self._p(t, "DECLARE_DISASTER", {"area": area},
                                               self._rule_ids(pack, "DECLARE_DISASTER"),
                                               f"{etype} names {area} as at risk; declaring enables "
                                               f"the response powers that depend on a declaration.",
                                               [item["event"]["event_id"]]))

        if "ORDER_DISASTER_ROAMING" in powers:
            for etype in ("LANDFALL", "DAMAGE_REPORT"):
                for item in inbox.all_of(etype):
                    for area in _areas_of(item):
                        if self._once(f"roamorder:{area}"):
                            out.append(self._p(t, "ORDER_DISASTER_ROAMING", {"area": area},
                                               self._rule_ids(pack, "ORDER_DISASTER_ROAMING"),
                                               f"{etype} shows service loss in {area}; directing "
                                               f"inter-operator roaming so subscribers keep access.",
                                               [item["event"]["event_id"]]))

        if "ORDER_SUSPENSION" in powers and "RUMOUR" in seen:
            for item in inbox.all_of("RUMOUR"):
                for area in _areas_of(item):
                    if self._once(f"suspend:{area}"):
                        out.append(self._p(
                            t, "ORDER_SUSPENSION",
                            {"area": area, "duration_min": 360,
                             "reasons": "reports of unrest and rumour-driven mobilisation",
                             "exempt_priority_slice": False},
                            self._rule_ids(pack, "ORDER_SUSPENSION"),
                            f"Rumour traffic reported in {area}; ordering temporary suspension to "
                            f"prevent incitement, as the suspension power permits.",
                            [item["event"]["event_id"]]))
        return out or [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"))]


@node("M")
class SdmaAlertsTwin(RuleAgent):
    """Alerts every area it is told about, in that area's languages, and asks the neighbour."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        out: list[Proposal] = []
        powers = pack.powers_of(self.role_id)
        for etype in ("IMD_WARNING", "LANDFALL", "CROSS_BORDER_REQUEST", "DISASTER_DECLARED"):
            for item in inbox.all_of(etype):
                for area in _areas_of(item):
                    langs = _languages_of(item, area)
                    if "ISSUE_CAP_ALERT" in powers and self._once(f"alert:{area}"):
                        out.append(self._p(
                            t, "ISSUE_CAP_ALERT",
                            {"area": area, "languages": langs, "severity": "Severe",
                             "languages_include_local": True},
                            self._rule_ids(pack, "ISSUE_CAP_ALERT"),
                            f"{etype} puts {area} at risk; issuing a CAP alert in {langs} so the "
                            f"population can act on it.",
                            [item["event"]["event_id"]]))
                    if ("REQUEST_CROSS_BORDER_ALERT" in powers
                            and area in _cross_border_hint(item)
                            and self._once(f"xborder:{area}")):
                        out.append(self._p(
                            t, "REQUEST_CROSS_BORDER_ALERT",
                            {"area": area, "languages": langs},
                            self._rule_ids(pack, "REQUEST_CROSS_BORDER_ALERT"),
                            f"{area} lies across the border and is outside my alerting power; "
                            f"passing the warning to the neighbouring authority.",
                            [item["event"]["event_id"]]))
        return out or [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"))]


@node("M")
class TspNetworkTwin(RuleAgent):
    """Complies with orders it receives, restores sites, and prioritises relief when it may."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        out: list[Proposal] = []
        powers = pack.powers_of(self.role_id)

        for item in inbox.all_of("ORDER"):
            ev = item["event"]
            area = ev.get("area") or (ev.get("payload") or {}).get("area")
            if not area or "SUSPEND_SERVICE" not in powers:
                continue
            if self._once(f"suspend:{ev['event_id']}"):
                payload = ev.get("payload") or {}
                out.append(self._p(
                    t, "SUSPEND_SERVICE",
                    {"area": area, "duration_min": payload.get("duration_min", 360),
                     "exempt_priority_slice": bool(payload.get("exempt_priority_slice", False))},
                    self._rule_ids(pack, "SUSPEND_SERVICE"),
                    f"Received a suspension direction for {area} from "
                    f"{ev.get('claimed_issuer') or 'the authority'}; giving effect to it as "
                    f"the licence condition requires.",
                    [ev["event_id"]]))

        if "PRIORITISE_RELIEF_SLICE" in powers:
            for etype in ("LANDFALL", "DAMAGE_REPORT", "SITE_DOWN", "DISASTER_DECLARED", "ORDER"):
                for item in inbox.all_of(etype):
                    for area in _areas_of(item):
                        if self._once(f"prio:{area}"):
                            out.append(self._p(
                                t, "PRIORITISE_RELIEF_SLICE", {"area": area},
                                self._rule_ids(pack, "PRIORITISE_RELIEF_SLICE"),
                                f"{etype} in {area}; raising the relief priority slice so emergency "
                                f"traffic keeps getting through.",
                                [item["event"]["event_id"]]))

        if "ENABLE_ROAMING" in powers:
            standing = [r for r in pack.rules_for(self.role_id, "ENABLE_ROAMING")
                        if r.effect in ("permit", "oblige")
                        and "ORDER_DISASTER_ROAMING" not in str(r.conditions.get("event_seen", ""))]
            order_items = inbox.all_of("ORDER_DISASTER_ROAMING")
            trigger_items = order_items or ([i for e in ("LANDFALL", "DAMAGE_REPORT", "SITE_DOWN")
                                             for i in inbox.all_of(e)] if standing else [])
            for item in trigger_items:
                for area in _areas_of(item):
                    if self._once(f"roam:{area}"):
                        out.append(self._p(
                            t, "ENABLE_ROAMING", {"area": area, "ordered": bool(order_items)},
                            self._rule_ids(pack, "ENABLE_ROAMING"),
                            f"Enabling disaster roaming in {area} "
                            + ("on the direction received." if order_items else
                               "under the standing trigger, no separate direction required."),
                            [item["event"]["event_id"]]))

        if "RESTORE_SITE" in powers:
            for etype in ("SITE_DOWN", "DAMAGE_REPORT", "POWER_LOSS"):
                for item in inbox.all_of(etype):
                    for area in _areas_of(item):
                        if self._once(f"restore:{area}:{item['arrives_t']}"):
                            out.append(self._p(
                                t, "RESTORE_SITE", {"area": area, "max_sites": 3},
                                self._rule_ids(pack, "RESTORE_SITE"),
                                f"Sites down in {area}; dispatching restoration.",
                                [item["event"]["event_id"]]))

        if "REPORT_INCIDENT" in powers:
            for etype in ("SUSPICIOUS_ORDER", "CYBER_INCIDENT", "SITE_DOWN"):
                for item in inbox.all_of(etype):
                    if self._once(f"report:{item['event']['event_id']}"):
                        out.append(self._p(
                            t, "REPORT_INCIDENT",
                            {"to": "cert_in", "incident_type": etype,
                             "about_event_id": item["event"]["event_id"]},
                            self._rule_ids(pack, "REPORT_INCIDENT"),
                            f"{etype} is a reportable incident; reporting within the statutory window.",
                            [item["event"]["event_id"]]))
        return out or [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"))]


@node("M")
class CertInTwin(RuleAgent):
    """Flags orders reported to it as suspicious. Sees incident reports only."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        out: list[Proposal] = []
        powers = pack.powers_of(self.role_id)
        if "FLAG_FORGED_ORDER" in powers:
            for etype in ("INCIDENT_REPORT", "SUSPICIOUS_ORDER", "ORDER"):
                for item in inbox.all_of(etype):
                    ev = item["event"]
                    about = (ev.get("payload") or {}).get("about_event_id") or ev["event_id"]
                    if self._once(f"flag:{about}"):
                        out.append(self._p(
                            t, "FLAG_FORGED_ORDER",
                            {"about_event_id": about, "confidence": "medium"},
                            self._rule_ids(pack, "FLAG_FORGED_ORDER"),
                            f"Order {about} was reported to me and I cannot confirm its provenance "
                            f"from the material I hold; flagging it as a suspected forgery.",
                            [ev["event_id"]]))
        return out or [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"))]


@node("M")
class NeighbourAuthorityTwin(RuleAgent):
    """Acts on its own powers when a cross-border request finally reaches it."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        out: list[Proposal] = []
        powers = pack.powers_of(self.role_id)

        for etype in ("LANDFALL", "DAMAGE_REPORT", "CROSS_BORDER_REQUEST"):
            for item in inbox.all_of(etype):
                ev = item["event"]
                for area in _areas_of(item):
                    if "ENABLE_ROAMING" in powers and self._once(f"nroam:{area}"):
                        out.append(self._p(
                            t, "ENABLE_ROAMING", {"area": area, "ordered": True},
                            self._rule_ids(pack, "ENABLE_ROAMING"),
                            f"{etype} shows service loss in {area} on my side of the border; "
                            f"enabling disaster roaming under my own powers.",
                            [ev["event_id"]]))
                    if "ISSUE_CAP_ALERT" in powers and self._once(f"nalert:{area}"):
                        langs = _languages_of(item, area)
                        out.append(self._p(
                            t, "ISSUE_CAP_ALERT",
                            {"area": area, "languages": langs, "languages_include_local": True},
                            self._rule_ids(pack, "ISSUE_CAP_ALERT"),
                            f"Alerting {area} on my own authority now that the warning has "
                            f"reached me at T+{item['arrives_t']}.",
                            [ev["event_id"]]))

        for item in inbox.all_of("CROSS_BORDER_REQUEST"):
            ev = item["event"]
            for area in _areas_of(item):
                if "ACKNOWLEDGE_CROSS_BORDER" in powers and self._once(f"ack:{ev['event_id']}"):
                    out.append(self._p(
                        t, "ACKNOWLEDGE_CROSS_BORDER", {"area": area},
                        self._rule_ids(pack, "ACKNOWLEDGE_CROSS_BORDER"),
                        f"Cross-border request about {area} received at T+{item['arrives_t']}; "
                        f"acknowledging.",
                        [ev["event_id"]]))
        return out or [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"))]


@node("M")
class AdviserTwin(RuleAgent):
    """The adviser proposes nothing; it answers questions. See agents/adviser.py."""
    def _decide(self, inbox: Inbox, t: int, pack: PolicyPack) -> list[Proposal]:
        return [noop(self.role_id, t, self.ids.next(self.role_id, t, "NOOP"),
                     "advisory role: holds no powers and proposes no actions")]


TWINS = {
    "competent_authority": CompetentAuthorityTwin,
    "sdma_alerts": SdmaAlertsTwin,
    "tsp_network": TspNetworkTwin,
    "cert_in": CertInTwin,
    "neighbour_authority": NeighbourAuthorityTwin,
    "adviser": AdviserTwin,
}


def build_rule_agents(ids: Optional[ProposalIdFactory] = None) -> dict[str, RuleAgent]:
    ids = ids or ProposalIdFactory()
    return {rid: cls(rid, ids) for rid, cls in TWINS.items()}


def _areas_of(item: dict) -> list[str]:
    """Every area an inbox item refers to, deduplicated and sorted for determinism."""
    ev = item["event"]
    payload = ev.get("payload") or {}
    areas: list[str] = []
    if ev.get("area"):
        areas.append(ev["area"])
    for key in ("areas", "areas_at_risk", "cross_border_areas"):
        v = payload.get(key)
        if isinstance(v, list):
            areas.extend(a for a in v if isinstance(a, str))
    if isinstance(payload.get("area"), str):
        areas.append(payload["area"])
    return sorted(dict.fromkeys(areas))


def _languages_of(item: dict, area: str) -> list[str]:
    payload = item["event"].get("payload") or {}
    langs = payload.get("languages") or payload.get("languages_by_area", {}).get(area)
    if isinstance(langs, str):
        return [langs]
    if isinstance(langs, list) and langs:
        return sorted(langs)
    return ["en"]


def _cross_border_hint(item: dict) -> list[str]:
    payload = item["event"].get("payload") or {}
    v = payload.get("cross_border_areas")
    return [a for a in v if isinstance(a, str)] if isinstance(v, list) else []
