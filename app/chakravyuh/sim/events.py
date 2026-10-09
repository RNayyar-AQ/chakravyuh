"""Scenario loader + chunked, uneven event release. Y.3172 node: SRC/D."""
from __future__ import annotations

import heapq
from pathlib import Path
from typing import Iterable, Optional

import yaml
from pydantic import BaseModel

from ..schemas import Event
from ..world.state import WorldState, build_world
from ..y3172 import node

SCENARIOS_DIR = Path("data/scenarios")


class Thresholds(BaseModel):
    """Property thresholds. ILLUSTRATIVE units, stated as such in the report (§5.5)."""
    t_alert_min: int = 90
    t_roam_min: int = 120
    min_pct_relief_cells: float = 60.0
    max_forged_executions: int = 0


class Scenario(BaseModel):
    scenario_id: str
    title: str = ""
    description: str = ""
    horizon_min: int = 720
    tick_min: int = 15
    areas: list[str] = []
    cross_border_areas: list[str] = []
    cells_per_area: dict[str, int] = {}
    local_languages: dict[str, list[str]] = {}
    epoch_iso: Optional[str] = None
    area_polygons: dict[str, str] = {}
    area_circles: dict[str, str] = {}
    channel_latency_min: dict[str, int] = {}
    default_latency_min: int = 0
    thresholds: Thresholds = Thresholds()
    events: list[Event] = []

    def world(self) -> WorldState:
        world = build_world(self.areas, self.cells_per_area, self.local_languages,
                            self.cross_border_areas)
        world.epoch_iso = self.epoch_iso
        world.area_polygons = dict(self.area_polygons)
        world.area_circles = dict(self.area_circles)
        world.scenario_id = self.scenario_id
        return world


@node("SRC")
def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a scenario YAML. Event ids must be unique and times non-negative."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    scen = Scenario(**raw)
    seen: set[str] = set()
    for e in scen.events:
        if e.event_id in seen:
            raise ValueError(f"{path}: duplicate event_id {e.event_id!r}")
        seen.add(e.event_id)
        if e.t_minutes < 0:
            raise ValueError(f"{path}: event {e.event_id} has negative t_minutes")
    return scen


@node("D")
class EventQueue:
    """Priority queue of events by release time. Ties break on event_id, so release is total-ordered."""
    def __init__(self, events: Iterable[Event] = ()):
        self._heap: list[tuple[int, str, Event]] = []
        self._counter = 0
        for e in events:
            self.push(e)

    def push(self, event: Event) -> None:
        heapq.heappush(self._heap, (event.t_minutes, event.event_id, event))

    def due(self, t: int) -> list[Event]:
        """Pop every event released at or before t, in (t, event_id) order."""
        out: list[Event] = []
        while self._heap and self._heap[0][0] <= t:
            out.append(heapq.heappop(self._heap)[2])
        return out

    def peek_next_t(self) -> Optional[int]:
        return self._heap[0][0] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)
