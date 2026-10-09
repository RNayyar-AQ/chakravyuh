"""5G world state. Y.3172 node: SRC/SINK (the shared ground truth the Game Master mutates).

Illustrative units only (spec §0): cell counts, minutes, percentages. No money, no casualties,
no confidence intervals. "Harm" is a property violation (§5.5), measured in these units.

Only world/dynamics.py mutates a WorldState, and only on a Game Master verdict. No agent ever
holds a reference that lets it write here.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

PRIORITY_SLICE = "relief_priority"   # E.106 / IEPS-style priority slice for relief traffic


class Cell(BaseModel):
    """One 5G site. `priority_slice_up` is what property P1 measures."""
    cell_id: str
    area: str
    up: bool = True                   # radio/backhaul physically alive
    service_suspended: bool = False   # commercial service suspended by order
    priority_slice_up: bool = False   # relief priority slice carrying traffic
    power_backup_min: int = 240
    load: float = 0.3                 # 0..1 illustrative utilisation
    damaged: bool = False
    roaming_enabled: bool = False

    @property
    def reachable_for_relief(self) -> bool:
        return self.up and self.priority_slice_up


class Suspension(BaseModel):
    """An in-force suspension of telecom service in an area."""
    suspension_id: str
    area: str
    start_t: int
    end_t: int                        # start_t + duration
    ordered_by: str
    order_event_id: Optional[str] = None
    order_authentic: bool = True      # ground truth; agents never read this
    exempt_priority_slice: bool = False   # did the order carve out relief traffic?

    def active_at(self, t: int) -> bool:
        return self.start_t <= t < self.end_t


class Alert(BaseModel):
    """A public alert actually delivered to an area (CAP / X.1303-shaped)."""
    alert_id: str
    area: str
    t_minutes: int
    languages: list[str] = []
    issued_by: str = ""
    severity: str = "Severe"
    channel: str = "cell_broadcast"
    # The CAP 1.2 / ITU-T X.1303 envelope this alert was emitted as, built by
    # chakravyuh.alerts.cap. Stored on the alert so the UI and the ledger show the same
    # envelope the agent produced, rather than one rebuilt later from different inputs.
    cap: dict = {}


class RoamingGrant(BaseModel):
    """Disaster roaming in force for an area, optionally across a border."""
    grant_id: str
    area: str
    t_minutes: int
    cross_border: bool = False
    granted_by: str = ""
    ordered: bool = True              # False = operator acted without an order


class IncidentReport(BaseModel):
    """An incident reported to CERT-In (6-hour clock) or to a regulator."""
    report_id: str
    t_minutes: int
    reported_by: str
    to: str
    incident_type: str
    about_event_id: Optional[str] = None


class WorldState(BaseModel):
    """The single authoritative world. One per run."""
    t_minutes: int = 0
    areas: list[str] = []
    cross_border_areas: list[str] = []          # areas on the neighbour's side
    cells: dict[str, Cell] = {}
    affected_areas: list[str] = []              # set by the scenario / damage events
    disaster_declared: dict[str, bool] = {}
    suspensions: list[Suspension] = []
    alerts: list[Alert] = []
    roaming: list[RoamingGrant] = []
    incidents: list[IncidentReport] = []
    local_languages: dict[str, list[str]] = {}  # area -> languages a valid alert must use
    grid_down: dict[str, bool] = {}             # area -> mains power lost (set by POWER_LOSS)

    # CAP envelope metadata, copied from the scenario. `epoch_iso` turns the run's T+minutes
    # into the real dateTime CAP 1.2 requires; the area shapes are only those the scenario
    # declares from a cited source, so an area with no published shape gets no shape.
    epoch_iso: Optional[str] = None
    area_polygons: dict[str, str] = {}
    area_circles: dict[str, str] = {}
    scenario_id: str = ""

    # scenario clocks, filled by the GM as the truth unfolds
    first_warning_t: Optional[int] = None
    landfall_t: Optional[int] = None
    # When each area FIRST became the subject of a warning. A real cyclone escalates: districts
    # enter the warning as the track narrows, so an area named only at the cyclone-alert stage
    # must have its alerting clock started then -- not at the run's first bulletin. Measuring
    # every area from a single global t0 scored Kolkata, alerted 5 minutes after it was first
    # named, as 1440 minutes late.
    first_warning_by_area: dict[str, int] = {}

    # -- queries -----------------------------------------------------------
    def cells_in(self, area: str) -> list[Cell]:
        return [c for c in self.cells.values() if c.area == area]

    def active_suspensions(self, t: Optional[int] = None) -> list[Suspension]:
        t = self.t_minutes if t is None else t
        return [s for s in self.suspensions if s.active_at(t)]

    def suspended_areas(self, t: Optional[int] = None) -> set[str]:
        return {s.area for s in self.active_suspensions(t)}

    def roaming_active_in(self, area: str) -> bool:
        return any(g.area == area for g in self.roaming)

    def roaming_t_for(self, area: str) -> Optional[int]:
        ts = [g.t_minutes for g in self.roaming if g.area == area]
        return min(ts) if ts else None

    def alerts_for(self, area: str) -> list[Alert]:
        return [a for a in self.alerts if a.area == area]

    def warning_baseline_for(self, area: str) -> int:
        """When the alerting clock starts for this area: when it was first warned about."""
        t = self.first_warning_by_area.get(area)
        if t is not None:
            return t
        return self.first_warning_t if self.first_warning_t is not None else 0

    def valid_alert_t_for(self, area: str) -> Optional[int]:
        """Earliest alert for the area that was issued in at least one required local language."""
        required = set(self.local_languages.get(area, []))
        ts = [a.t_minutes for a in self.alerts_for(area)
              if not required or (set(a.languages) & required)]
        return min(ts) if ts else None

    def impaired_areas(self) -> list[str]:
        """Areas where service was actually lost: any cell down, damaged or suspended.

        Distinct from `affected_areas`, which also holds districts that were merely warned.
        Roaming under disaster only means anything where a network is impaired -- that is how
        47 CFR 4.17 frames it ("a provider whose network is impaired in the affected area") --
        so timing properties about roaming scope to this set, not to everything warned.
        """
        out = {c.area for c in self.cells.values()
               if (not c.up) or c.damaged or c.service_suspended}
        return sorted(out)

    def pct_relief_reachable(self, area: str) -> float:
        """Percent of cells in the area where relief traffic can still get through (P1's unit)."""
        cells = self.cells_in(area)
        if not cells:
            return 100.0
        return 100.0 * sum(1 for c in cells if c.reachable_for_relief) / len(cells)

    def snapshot(self) -> dict:
        """Compact, hashable view for the ledger. Must be deterministic: sorted keys only."""
        return {
            "t": self.t_minutes,
            "cells_up": sum(1 for c in self.cells.values() if c.up),
            "cells_total": len(self.cells),
            "priority_up": sum(1 for c in self.cells.values() if c.priority_slice_up),
            "suspended_areas": sorted(self.suspended_areas()),
            "roaming_areas": sorted({g.area for g in self.roaming}),
            "alerted_areas": sorted({a.area for a in self.alerts}),
            "affected_areas": sorted(self.affected_areas),
            "incidents": len(self.incidents),
        }


def build_world(areas: list[str], cells_per_area: dict[str, int],
                local_languages: dict[str, list[str]] | None = None,
                cross_border_areas: list[str] | None = None) -> WorldState:
    """Deterministic world construction: cell ids are area-ordered, never random."""
    cells: dict[str, Cell] = {}
    for area in areas:
        for i in range(cells_per_area.get(area, 0)):
            cid = f"{area}-cell-{i:03d}"
            cells[cid] = Cell(cell_id=cid, area=area)
    return WorldState(
        areas=list(areas),
        cross_border_areas=list(cross_border_areas or []),
        cells=cells,
        disaster_declared={a: False for a in areas},
        local_languages=dict(local_languages or {}),
    )
