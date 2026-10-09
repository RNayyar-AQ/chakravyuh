"""Deterministic effects of approved actions and exogenous events. Y.3172 node: D."""
from __future__ import annotations


from ..schemas import Decision, Event, Proposal, Verdict
from ..alerts.cap import build_cap, cap_shape_errors
from ..y3172 import node
from .state import Alert, IncidentReport, RoamingGrant, Suspension, WorldState

DERIVED_EVENT_TYPE = {
    "ORDER_SUSPENSION": "ORDER",
    "ORDER_DISASTER_ROAMING": "ORDER_DISASTER_ROAMING",
    "REQUEST_CROSS_BORDER_ALERT": "CROSS_BORDER_REQUEST",
    "FLAG_FORGED_ORDER": "SUSPICIOUS_ORDER",
    "REPORT_INCIDENT": "INCIDENT_REPORT",
    "DECLARE_DISASTER": "DISASTER_DECLARED",
}

DERIVED_VISIBILITY = {
    "ORDER": ["tsp_network", "cert_in"],
    "ORDER_DISASTER_ROAMING": ["tsp_network"],
    "CROSS_BORDER_REQUEST": ["neighbour_authority"],
    "SUSPICIOUS_ORDER": ["tsp_network", "competent_authority"],
    "INCIDENT_REPORT": ["cert_in"],
    "DISASTER_DECLARED": ["tsp_network", "sdma_alerts", "cert_in"],
}


def _bool(v, default: bool = False) -> bool:
    return bool(v) if isinstance(v, bool) else default


def _int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@node("D")
def apply_exogenous(state: WorldState, event: Event) -> dict:
    """Apply what the world does on its own: warnings, landfall, site damage, power loss."""
    truth = event.payload.get("truth", {})
    changed: dict = {"event_id": event.event_id, "type": event.type, "cells_changed": []}

    if event.type == "IMD_WARNING":
        if state.first_warning_t is None:
            state.first_warning_t = event.t_minutes
        named = list(truth.get("areas_at_risk", []))
        named += [a for a in (event.payload.get("cross_border_areas") or []) if isinstance(a, str)]
        for area in named:
            if area not in state.affected_areas:
                state.affected_areas.append(area)
            state.first_warning_by_area.setdefault(area, event.t_minutes)
        changed["affected_areas"] = sorted(state.affected_areas)
        changed["newly_warned"] = sorted(a for a in named
                                         if state.first_warning_by_area.get(a) == event.t_minutes)

    elif event.type == "LANDFALL":
        if state.landfall_t is None:
            state.landfall_t = event.t_minutes
        for area in truth.get("areas", []):
            if area not in state.affected_areas:
                state.affected_areas.append(area)
            state.first_warning_by_area.setdefault(area, event.t_minutes)
        changed["affected_areas"] = sorted(state.affected_areas)

    elif event.type in ("SITE_DOWN", "DAMAGE_REPORT"):
        area = event.area or truth.get("area")
        n_down = _int(truth.get("cells_down"), 0)
        cells = sorted(state.cells_in(area or ""), key=lambda c: c.cell_id)
        for cell in [c for c in cells if c.up][:n_down]:
            cell.up = False
            cell.damaged = True
            cell.priority_slice_up = False
            changed["cells_changed"].append(cell.cell_id)
        if area and area not in state.affected_areas:
            state.affected_areas.append(area)

    elif event.type == "POWER_LOSS":
        area = event.area or truth.get("area")
        if area:
            state.grid_down[area] = True
        for cell in sorted(state.cells_in(area or ""), key=lambda c: c.cell_id):
            cell.power_backup_min = max(0, cell.power_backup_min - _int(truth.get("drain_min"), 60))
            if cell.power_backup_min == 0 and cell.up:
                cell.up = False
                cell.priority_slice_up = False
                changed["cells_changed"].append(cell.cell_id)
        changed["grid_down"] = sorted(a for a, v in state.grid_down.items() if v)

    elif event.type == "RUMOUR":
        changed["note"] = "rumour: no world effect, inbox only"

    return changed


@node("D")
def apply_action(state: WorldState, proposal: Proposal, verdict: Verdict,
                 trigger_authentic: bool = True) -> tuple[dict, list[Event]]:
    """Apply an executing action. Returns (effect description, derived events to re-inject)."""
    if not verdict.executes:
        raise ValueError(f"apply_action called on non-executing verdict {verdict.decision} "
                         f"for {proposal.proposal_id}")

    p = proposal.params
    area = p.get("area")
    t = proposal.t_minutes
    effect: dict = {"action_type": proposal.action_type, "actor_role": proposal.actor_role,
                    "area": area, "t": t, "advisory_override": verdict.decision is Decision.BLOCK}

    if proposal.action_type == "DECLARE_DISASTER":
        if area:
            state.disaster_declared[area] = True
        effect["declared"] = area

    elif proposal.action_type == "SUSPEND_SERVICE":
        exempt = _bool(p.get("exempt_priority_slice"), False)
        duration = _int(p.get("duration_min"), 240)
        susp = Suspension(
            suspension_id=f"susp-{proposal.proposal_id}", area=area or "", start_t=t,
            end_t=t + duration, ordered_by=proposal.actor_role,
            order_event_id=(proposal.triggered_by_event_ids or [None])[0],
            order_authentic=trigger_authentic, exempt_priority_slice=exempt)
        state.suspensions.append(susp)
        for cell in state.cells_in(area or ""):
            cell.service_suspended = True
            if not exempt:
                cell.priority_slice_up = False
        effect.update({"suspension_id": susp.suspension_id, "until_t": susp.end_t,
                       "exempt_priority_slice": exempt, "order_authentic": trigger_authentic})

    elif proposal.action_type == "PRIORITISE_RELIEF_SLICE":
        raised = []
        for cell in state.cells_in(area or ""):
            susp = [s for s in state.active_suspensions(t) if s.area == cell.area]
            if susp and not any(s.exempt_priority_slice for s in susp):
                continue
            if cell.up:
                cell.priority_slice_up = True
                raised.append(cell.cell_id)
        effect["cells_prioritised"] = len(raised)

    elif proposal.action_type == "ENABLE_ROAMING":
        grant = RoamingGrant(grant_id=f"roam-{proposal.proposal_id}", area=area or "", t_minutes=t,
                             cross_border=(area or "") in state.cross_border_areas,
                             granted_by=proposal.actor_role, ordered=_bool(p.get("ordered"), True))
        state.roaming.append(grant)
        for cell in state.cells_in(area or ""):
            cell.roaming_enabled = True
        effect.update({"grant_id": grant.grant_id, "cross_border": grant.cross_border})

    elif proposal.action_type == "ISSUE_CAP_ALERT":
        langs = p.get("languages") or []
        langs = [langs] if isinstance(langs, str) else list(langs)
        alert_id = f"alert-{proposal.proposal_id}"
        local = state.local_languages.get(area or "", [])
        cap_langs = ([x for x in local if x in langs]
                     + [x for x in langs if x not in local])
        cap = build_cap(
            alert_id=alert_id, area=area or "", t_minutes=t, languages=cap_langs,
            issued_by=proposal.actor_role, severity=str(p.get("severity", "Severe")),
            channel=str(p.get("channel", "cell_broadcast")),
            urgency=str(p.get("urgency", "Immediate")),
            certainty=str(p.get("certainty", "Likely")),
            event=str(p.get("event", "Cyclone")),
            epoch_iso=state.epoch_iso, scenario_id=state.scenario_id,
            polygon=state.area_polygons.get(area or ""),
            circle=state.area_circles.get(area or ""),
        )
        alert = Alert(alert_id=alert_id, area=area or "", t_minutes=t,
                      languages=langs, issued_by=proposal.actor_role,
                      severity=str(p.get("severity", "Severe")),
                      channel=str(p.get("channel", "cell_broadcast")), cap=cap)
        state.alerts.append(alert)
        required = set(state.local_languages.get(area or "", []))
        effect.update({"alert_id": alert.alert_id, "languages": langs,
                       "in_local_language": bool(not required or (set(langs) & required)),
                       "cap_identifier": cap["identifier"], "cap_sent": cap["sent"],
                       "cap_language": cap["info"]["language"],
                       "cap_shape_ok": not cap_shape_errors(cap)})

    elif proposal.action_type == "RESTORE_SITE":
        restored = []
        budget = _int(p.get("max_sites"), 3)
        if area and state.grid_down.get(area):
            state.grid_down[area] = False
            effect["grid_restored"] = area
        for cell in sorted(state.cells_in(area or ""), key=lambda c: c.cell_id):
            if not cell.up and len(restored) < budget:
                cell.up = True
                cell.damaged = False
                cell.power_backup_min = max(cell.power_backup_min, 120)
                restored.append(cell.cell_id)
        effect["cells_restored"] = len(restored)

    elif proposal.action_type == "REPORT_INCIDENT":
        rep = IncidentReport(report_id=f"rep-{proposal.proposal_id}", t_minutes=t,
                             reported_by=proposal.actor_role, to=str(p.get("to", "cert_in")),
                             incident_type=str(p.get("incident_type", "unspecified")),
                             about_event_id=p.get("about_event_id"))
        state.incidents.append(rep)
        effect["report_id"] = rep.report_id

    elif proposal.action_type in ("ORDER_SUSPENSION", "ORDER_DISASTER_ROAMING",
                                  "REQUEST_CROSS_BORDER_ALERT", "FLAG_FORGED_ORDER",
                                  "ISSUE_ADVISORY", "ACKNOWLEDGE_CROSS_BORDER"):
        effect["note"] = "communicative act: effect is the derived event it emits"

    else:
        effect["note"] = f"no world effect defined for {proposal.action_type}"

    return effect, derive_events(proposal, verdict)


@node("D")
def derive_events(proposal: Proposal, verdict: Verdict) -> list[Event]:
    """Turn an executed communicative act into a fact other agents can receive and cite."""
    etype = DERIVED_EVENT_TYPE.get(proposal.action_type)
    if etype is None:
        return []
    payload = {k: v for k, v in proposal.params.items() if k != "truth"}
    payload["issued_by_role"] = proposal.actor_role
    return [Event(
        event_id=f"der-{proposal.proposal_id}",
        t_minutes=proposal.t_minutes,
        type=etype,
        area=proposal.params.get("area"),
        payload=payload,
        visible_to=list(DERIVED_VISIBILITY.get(etype, [])),
        authentic=True,
        claimed_issuer=proposal.actor_role,
    )]


@node("D")
def step(state: WorldState, t: int) -> dict:
    """Advance the clock and apply time-driven world behaviour (suspension expiry, battery drain)."""
    prev = state.t_minutes
    state.t_minutes = t
    dt = max(0, t - prev)
    expired = []
    for s in state.suspensions:
        if s.end_t <= t and s.active_at(prev):
            expired.append(s.suspension_id)
            for cell in state.cells_in(s.area):
                cell.service_suspended = any(
                    o.active_at(t) for o in state.suspensions if o.area == cell.area)
    drained = []
    for cell in sorted(state.cells.values(), key=lambda c: c.cell_id):
        if not cell.up or not state.grid_down.get(cell.area, False):
            continue
        cell.power_backup_min = max(0, cell.power_backup_min - dt)
        if cell.power_backup_min == 0:
            cell.up = False
            cell.priority_slice_up = False
            drained.append(cell.cell_id)
    return {"t": t, "suspensions_expired": expired, "cells_lost_to_power": drained,
            "grid_down_areas": sorted(a for a, v in state.grid_down.items() if v)}
