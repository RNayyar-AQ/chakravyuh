"""Message bus with per-channel latency and per-role visibility. Y.3172 node: D."""
from __future__ import annotations

import heapq
from typing import Optional

from ..schemas import Event
from ..y3172 import node


class Delivery:
    """One event arriving at one role at one time."""
    __slots__ = ("role", "event", "released_t", "arrives_t")

    def __init__(self, role: str, event: Event, released_t: int, arrives_t: int):
        self.role = role
        self.event = event
        self.released_t = released_t
        self.arrives_t = arrives_t

    @property
    def latency(self) -> int:
        return self.arrives_t - self.released_t

    def ledger_payload(self) -> dict:
        return {"role": self.role, "event_id": self.event.event_id, "event_type": self.event.type,
                "released_t": self.released_t, "arrives_t": self.arrives_t, "latency_min": self.latency,
                "visible": self.event.redact()}


@node("D")
class Bus:
    """Per-role inbox delivery with configurable latency."""
    def __init__(self, channel_latency_min: Optional[dict[str, int]] = None,
                 default_latency_min: int = 0):
        self.channel_latency_min = dict(channel_latency_min or {})
        self.default_latency_min = default_latency_min
        self._pending: list[tuple[int, str, str, Delivery]] = []
        self._seq = 0
        self.delivered: list[Delivery] = []

    def latency_for(self, event: Event, role: str) -> int:
        """Event-specific delay wins over the structural channel latency for that role."""
        if role in event.delay_by_role:
            return int(event.delay_by_role[role])
        return int(self.channel_latency_min.get(role, self.default_latency_min))

    @node("D")
    def publish(self, event: Event, released_t: int) -> list[Delivery]:
        """Queue the event for every role that can see it. Returns the scheduled deliveries."""
        out: list[Delivery] = []
        for role in sorted(set(event.visible_to)):
            arrives = released_t + self.latency_for(event, role)
            d = Delivery(role, event, released_t, arrives)
            heapq.heappush(self._pending, (arrives, event.event_id, role, d))
            self._seq += 1
            out.append(d)
        return out

    def deliver_due(self, t: int) -> list[Delivery]:
        """Pop every delivery whose arrival time has come, in (arrives_t, event_id, role) order."""
        out: list[Delivery] = []
        while self._pending and self._pending[0][0] <= t:
            out.append(heapq.heappop(self._pending)[3])
        self.delivered.extend(out)
        return out

    def drain_all(self) -> list[Delivery]:
        out = [heapq.heappop(self._pending)[3] for _ in range(len(self._pending))]
        self.delivered.extend(out)
        return out

    def in_flight(self) -> int:
        return len(self._pending)

    def latency_report(self) -> dict[str, dict]:
        """Observed latency per role: evidence for a coordination gap."""
        per: dict[str, list[int]] = {}
        for d in self.delivered:
            per.setdefault(d.role, []).append(d.latency)
        return {role: {"deliveries": len(v), "max_latency_min": max(v),
                       "mean_latency_min": round(sum(v) / len(v), 1)}
                for role, v in sorted(per.items())}
