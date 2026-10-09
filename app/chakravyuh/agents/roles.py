"""Role definitions: mandate, powers, inbox filter, channel latency, prompt. Y.3172 node: M.

Six roles (spec §5.2). Powers come from the *pack*, not from here -- this file carries what the
role optimises and what it can perceive. Keeping the two separate is what lets the same agent
behave differently under three different legal regimes without changing any agent code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ROLE_ORDER = [
    "competent_authority",
    "sdma_alerts",
    "tsp_network",
    "cert_in",
    "neighbour_authority",
    "adviser",
]


@dataclass(frozen=True)
class Role:
    role_id: str
    name: str
    analogue: str
    mandate: str
    inbox_types: tuple[str, ...]         # event types this role can ever receive
    priority: int                        # GM tie-break order within a tick
    channel_latency_min: int = 0
    boundaries: str = ""

    def sees(self, event_type: str) -> bool:
        return "*" in self.inbox_types or event_type in self.inbox_types


ROLES: dict[str, Role] = {
    "competent_authority": Role(
        role_id="competent_authority",
        name="Competent Authority (Home Department)",
        analogue="Union/State Home Secretary under Telecom Act 2023 s.20 + Suspension Rules 2024",
        mandate=("Maintain public order and public safety while keeping the State's emergency "
                 "response functioning. You answer for both an unnecessary suspension and a "
                 "failure to act."),
        inbox_types=("IMD_WARNING", "LANDFALL", "DAMAGE_REPORT", "RUMOUR", "ORDER",
                     "SUSPICIOUS_ORDER", "DISASTER_DECLARED", "CROSS_BORDER_REQUEST"),
        priority=0,
        boundaries=("You do not see cell-level telemetry and you cannot verify a report yourself. "
                    "You cannot operate the network; you can only order."),
    ),
    "sdma_alerts": Role(
        role_id="sdma_alerts",
        name="State Disaster Management Authority (alerting)",
        analogue="NDMA/SDMA under DM Act 2005, CAP alerts via SACHET",
        mandate=("Get an accurate, intelligible warning to every person in every area at risk, "
                 "in a language they read, before the hazard arrives."),
        inbox_types=("IMD_WARNING", "LANDFALL", "DAMAGE_REPORT", "DISASTER_DECLARED",
                     "CROSS_BORDER_REQUEST"),
        priority=1,
        boundaries=("You do not see network telemetry or cyber incidents. You cannot compel an "
                    "operator to do anything."),
    ),
    "tsp_network": Role(
        role_id="tsp_network",
        name="Telecom Service Provider NOC (5G network and services)",
        analogue="Telecom operator network operations centre",
        mandate=("Keep the network carrying traffic, above all emergency and relief traffic, and "
                 "comply with lawful directions you receive through your nodal officer."),
        inbox_types=("SITE_DOWN", "POWER_LOSS", "DAMAGE_REPORT", "ORDER", "ORDER_DISASTER_ROAMING",
                     "SUSPICIOUS_ORDER", "DISASTER_DECLARED", "LANDFALL", "CYBER_INCIDENT"),
        priority=2,
        boundaries=("You do not receive meteorological warnings directly and you cannot verify "
                    "whether an order you received is genuine. You cannot issue public alerts."),
    ),
    "cert_in": Role(
        role_id="cert_in",
        name="CERT-In (national computer emergency response team)",
        analogue="CERT-In, Directions of 28 April 2022, six-hour reporting",
        mandate=("Detect and call out forged or tampered directions and reportable cyber "
                 "incidents affecting telecom networks."),
        inbox_types=("INCIDENT_REPORT", "CYBER_INCIDENT", "SUSPICIOUS_ORDER", "ORDER"),
        priority=3,
        boundaries=("You see incident reports only. You do not see meteorological warnings, "
                    "damage reports or public alerts, and you cannot order anything on the network."),
    ),
    "neighbour_authority": Role(
        role_id="neighbour_authority",
        name="Neighbouring State authority",
        analogue="Bangladesh regulator / Department of Disaster Management",
        mandate=("Protect the population on your side of the border. You act on your own legal "
                 "powers, not on a foreign authority's order."),
        inbox_types=("CROSS_BORDER_REQUEST", "LANDFALL", "DAMAGE_REPORT"),
        priority=4,
        channel_latency_min=75,
        boundaries=("You reach everything through the cross-border channel, which is slow. You "
                    "cannot see the other State's internal orders or telemetry."),
    ),
    "adviser": Role(
        role_id="adviser",
        name="Policy & Legal Adviser",
        analogue="Standing legal/policy adviser to the response",
        mandate=("Answer questions about who may lawfully do what, citing clauses. You hold no "
                 "powers and you propose no actions."),
        inbox_types=("*",),
        priority=5,
        boundaries=("Advisory only. Every claim must cite a clause_id present in the retrieved "
                    "context. If the clauses do not answer the question, say so and name the gap."),
    ),
}


@dataclass
class Inbox:
    """What one role has received, in arrival order. The agent's entire world."""
    role_id: str
    items: list[dict] = field(default_factory=list)   # {"arrives_t", "event" (redacted)}
    raw_events: list = field(default_factory=list)    # full Event objects, for the GM/engine only

    def add(self, delivery) -> None:
        self.items.append({"arrives_t": delivery.arrives_t, "event": delivery.event.redact()})
        self.raw_events.append(delivery.event)

    def new_since(self, t: int) -> list[dict]:
        return [i for i in self.items if i["arrives_t"] > t]

    def types_seen(self) -> set[str]:
        return {i["event"]["type"] for i in self.items}

    def latest_of(self, event_type: str) -> dict | None:
        matches = [i for i in self.items if i["event"]["type"] == event_type]
        return matches[-1] if matches else None

    def all_of(self, event_type: str) -> list[dict]:
        return [i for i in self.items if i["event"]["type"] == event_type]

    def as_text(self, limit: int = 40) -> str:
        """Render the inbox for an LLM prompt: timestamped, redacted, newest last."""
        lines = []
        for item in self.items[-limit:]:
            ev = item["event"]
            issuer = f" claimed_issuer={ev['claimed_issuer']}" if ev.get("claimed_issuer") else ""
            area = f" area={ev['area']}" if ev.get("area") else ""
            payload = {k: v for k, v in (ev.get("payload") or {}).items()}
            lines.append(f"T+{item['arrives_t']:>4} min | {ev['type']}{area}{issuer} | {payload}")
        return "\n".join(lines) if lines else "(your inbox is empty)"


def role_latencies() -> dict[str, int]:
    return {r.role_id: r.channel_latency_min for r in ROLES.values() if r.channel_latency_min}
