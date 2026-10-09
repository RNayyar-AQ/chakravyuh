"""P4 gate (spec §10): the forged-order scenario violates P2 with gap_class=policy."""
from __future__ import annotations

import csv

from chakravyuh.analysis.compare import gap_findings_across, passes_under, run_across_packs
from chakravyuh.analysis.gaps import classify_run
from chakravyuh.analysis.gap_register import RUBRIC_COLUMNS, write_register
from chakravyuh.fuzz.properties import check_all
from chakravyuh.sim.events import Thresholds
from chakravyuh.sim.runner import context_for, run
from chakravyuh.world.state import build_world


def _props(result):
    return {p.property_id: p for p in result.properties}


def test_forged_order_violates_p2_as_a_policy_gap(scenario, india_pack, tmp_path):
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    p2 = _props(r)["P2"]
    assert not p2.passed, "the hand-built forged order must break P2 under the India pack"
    assert p2.detail["count"] >= 1

    ctx = context_for(r)
    gaps = {g.violated_property: g for g in classify_run(r, india_pack, ctx["world"], ctx["gm"], scenario)}
    assert gaps["P2"].gap_class == "policy"
    assert gaps["P2"].responsible_clause_ids
    assert gaps["P2"].domain == "Emergency telecom"


def test_india_fails_all_four_and_comparators_pass(scenario, packs, tmp_path):
    results = run_across_packs(scenario, packs, seed=0, runs_dir=str(tmp_path))
    india = _props(results["india_current"])
    assert not any(p.passed for p in india.values()), "the baseline India pack fails all four"
    for comparator in ("bangladesh", "fcc_mdri"):
        assert all(p.passed for p in _props(results[comparator]).values()), comparator


def test_every_india_gap_has_a_comparator_that_passes(scenario, packs, tmp_path):
    results = run_across_packs(scenario, packs, seed=0, runs_dir=str(tmp_path))
    findings = gap_findings_across(results, packs, scenario)
    assert len(findings["india_current"]) == 4
    for f in findings["india_current"]:
        assert f.evidence["passes_under_packs"], f"{f.gap_id} has no comparator"
        assert f.instance, f.gap_id


def test_cross_border_gaps_are_phrased_domain_first(scenario, packs, tmp_path):
    results = run_across_packs(scenario, packs, seed=0, runs_dir=str(tmp_path))
    findings = gap_findings_across(results, packs, scenario)
    cross = [f for f in findings["india_current"] if "Bangladesh" in f.instance]
    assert cross, "the cross-border gaps are the rubric's critical examples"
    for f in cross:
        assert f.domain == "Emergency telecom"
        assert not f.statement.startswith("India"), "domain first, country as instance"


def test_gap_register_csv_has_neighbour_and_global_columns(scenario, packs, tmp_path):
    """The register must name an Indian instance, a neighbour and a global example per row."""
    results = run_across_packs(scenario, packs, seed=0, runs_dir=str(tmp_path))
    findings = gap_findings_across(results, packs, scenario)
    out = write_register(findings, packs, out_path=tmp_path / "gap_register.csv")
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert list(rows[0].keys())[: len(RUBRIC_COLUMNS)] == RUBRIC_COLUMNS
    text = out.read_text(encoding="utf-8")
    assert "Bangladesh" in text and "United States" in text
    assert len(rows) >= 9
    assert {"simulation", "document"} == {r["source"] for r in rows}


def test_passes_under_is_computed_not_asserted(scenario, packs, tmp_path):
    results = run_across_packs(scenario, packs, seed=0, runs_dir=str(tmp_path))
    assert passes_under(results, "P2") == ["bangladesh", "fcc_mdri"]
    assert passes_under(results, "P4") == ["bangladesh", "fcc_mdri"]


def test_p1_scope_covers_a_suspended_unaffected_metro():
    """A suspension of a metro hosting the response is in P1's scope, not out of it."""
    w = build_world(["METRO"], {"METRO": 10})
    w.disaster_declared["OTHER"] = True
    from chakravyuh.world.state import Suspension
    w.suspensions.append(Suspension(suspension_id="s1", area="METRO", start_t=0, end_t=600,
                                    ordered_by="competent_authority"))
    p1 = check_all(w, Thresholds())[0]
    assert not p1.passed
    assert p1.detail["per_area"]["METRO@s1"]["hazard_affected_area"] is False


def test_p4_not_applicable_without_landfall():
    w = build_world(["A"], {"A": 5})
    p4 = [p for p in check_all(w, Thresholds()) if p.property_id == "P4"][0]
    assert p4.passed and "not applicable" in p4.detail["note"]


def test_p4_not_applicable_when_no_affected_area_lost_service():
    """A district warned and left undamaged needs no roaming; demanding it is a false failure."""
    w = build_world(["A"], {"A": 5})
    w.affected_areas = ["A"]
    w.landfall_t = 60
    w.t_minutes = 720
    p4 = [p for p in check_all(w, Thresholds()) if p.property_id == "P4"][0]
    assert p4.passed
    assert "lost service" in p4.detail["note"]


def test_p3_clock_starts_when_an_area_is_first_warned():
    """An area warned late and alerted promptly must not be scored from the run's first bulletin."""
    from chakravyuh.world.state import Alert
    w = build_world(["EARLY", "LATE"], {"EARLY": 4, "LATE": 4},
                    {"EARLY": ["bn"], "LATE": ["bn"]})
    w.affected_areas = ["EARLY", "LATE"]
    w.first_warning_t = 0
    w.first_warning_by_area = {"EARLY": 0, "LATE": 1400}
    w.t_minutes = 2000
    w.alerts = [Alert(alert_id="a1", area="EARLY", t_minutes=30, languages=["bn"]),
                Alert(alert_id="a2", area="LATE", t_minutes=1430, languages=["bn"])]
    p3 = [p for p in check_all(w, Thresholds(t_alert_min=90)) if p.property_id == "P3"][0]
    assert p3.passed, p3.detail
    assert p3.detail["per_area"]["LATE"]["delay_min"] == 30
    assert p3.detail["warning_baseline_by_area"]["LATE"] == 1400


def test_margins_are_finite_and_in_minutes_when_an_area_is_never_served():
    w = build_world(["A"], {"A": 5}, {"A": ["bn"]})
    w.affected_areas = ["A"]
    w.first_warning_t = 0
    w.first_warning_by_area = {"A": 0}
    w.landfall_t = 60
    w.t_minutes = 720
    next(iter(w.cells.values())).up = False
    props = {p.property_id: p for p in check_all(w, Thresholds())}
    for pid in ("P3", "P4"):
        assert not props[pid].passed
        assert abs(props[pid].margin) < 10_000, "margin must be a real quantity, not a sentinel"
        assert "minutes" in props[pid].unit
