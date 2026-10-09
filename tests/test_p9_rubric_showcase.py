"""Rubric-showcase guarantees: CAP envelopes, computed confidence, provenance, audit surface.

These tests exist because each one covers a claim the showcase makes to a judge. A claim nobody
can break on stage is worth more than a claim in a README.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from chakravyuh.alerts.cap import (CAP_REQUIRED_FIELDS, build_cap, cap_shape_errors,
                                   check_circle, check_polygon, language_tag, region_for_area)
from chakravyuh.analysis.gap_register import (RUBRIC_COLUMNS, VALID_GAP_TYPES, confidence_for,
                                              load_document_gaps)
from chakravyuh.kb.clause_store import ClauseStore
from chakravyuh.sim.events import load_scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "data/scenarios/amphan_2020.yaml"
EPOCH = "2020-05-16T08:45:00+05:30"


# ----------------------------------------------------------------- CAP 1.2 / X.1303
def test_cap_envelope_carries_every_required_element():
    cap = build_cap(alert_id="a1", area="WB-KOLKATA", t_minutes=100, languages=["bn", "hi"],
                    issued_by="sdma_alerts", epoch_iso=EPOCH)
    assert cap_shape_errors(cap) == [], f"missing CAP elements: {cap_shape_errors(cap)}"
    assert set(CAP_REQUIRED_FIELDS)        # the contract itself is not empty


def test_cap_sent_is_derived_from_the_scenario_clock_not_the_wall_clock():
    """Two builds of the same alert must agree, or a replayed run is not replayable."""
    kw = dict(alert_id="a1", area="WB-KOLKATA", t_minutes=6300, languages=["bn"],
              issued_by="sdma_alerts", epoch_iso=EPOCH)
    first, second = build_cap(**kw), build_cap(**kw)
    assert first == second
    # T+6300 min from 16 May 08:45 IST is 20 May 17:45 IST.
    assert first["sent"] == "2020-05-20T17:45:00+05:30"


def test_cap_status_is_exercise_never_actual():
    """A simulated alert claiming CAP status 'Actual' would be the one genuinely misleading field."""
    cap = build_cap(alert_id="a1", area="WB-KOLKATA", t_minutes=0, languages=["bn"],
                    issued_by="sdma_alerts", epoch_iso=EPOCH)
    assert cap["status"] == "Exercise"
    assert "simulated" in cap["note"]
    assert {"valueName": "layer:simulated", "value": "true"} in cap["info"]["parameter"]


def test_cap_rejects_values_outside_the_standard_enumerations():
    for bad in ({"status": "Real"}, {"urgency": "Soon"}, {"severity": "Catastrophic"},
                {"certainty": "Certain"}):
        with pytest.raises(ValueError):
            build_cap(alert_id="a", area="WB-KOLKATA", t_minutes=0, languages=["bn"],
                      issued_by="x", epoch_iso=EPOCH, **bad)


def test_cap_rejects_an_unclosed_polygon():
    """CAP 1.2 requires a closed ring; parsers accept an open one and draw a different area."""
    closed = "22.5,88.3 22.4,88.3 22.4,88.5 22.5,88.3"
    assert check_polygon(closed) == closed
    with pytest.raises(ValueError, match="not closed"):
        check_polygon("22.5,88.3 22.4,88.3 22.4,88.5 22.5,88.5")
    with pytest.raises(ValueError, match="at least 4"):
        check_polygon("22.5,88.3 22.4,88.3 22.5,88.3")
    with pytest.raises(ValueError, match="out of range"):
        check_polygon("99.5,88.3 22.4,88.3 22.4,88.5 99.5,88.3")


def test_cap_circle_matches_the_imd_landfall_point():
    assert check_circle("21.65,88.30 60") == "21.65,88.30 60"
    with pytest.raises(ValueError):
        check_circle("21.65,88.30")


def test_language_tag_is_region_aware_across_the_border():
    """Bengali is bn-IN in West Bengal and bn-BD in Khulna; P3 is a cross-border property."""
    assert language_tag("bn", "WB-KOLKATA") == "bn-IN"
    assert language_tag("bn", "BD-KHULNA") == "bn-BD"
    assert language_tag("or", "OD-BALASORE") == "or-IN"
    assert region_for_area("BD-KHULNA") == "BD"
    # An unmapped code must say 'undetermined', never guess.
    assert language_tag("zz", "WB-KOLKATA") == "und"


def test_cap_info_language_is_the_local_language_not_the_alphabetically_first():
    """An Odia district's primary info block must read or-IN."""
    run = ROOT / "runs/amphan_2020__india_current__rule__seed0.jsonl"
    if not run.exists():
        pytest.skip("no demo run; python scripts/run_demo.py")
    seen = {}
    for line in run.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        p = entry["payload"]
        if entry["kind"] == "EFFECT" and p.get("action_type") == "ISSUE_CAP_ALERT":
            seen[p["area"]] = p["cap_language"]
    assert seen, "the run issued no CAP alert"
    for area, tag in seen.items():
        if area.startswith("OD-"):
            assert tag == "or-IN", f"{area} alerted in {tag}, not Odia"
        elif area.startswith("WB-"):
            assert tag == "bn-IN", f"{area} alerted in {tag}, not Bengali"


# ------------------------------------------------------- computed gap confidence
def test_confidence_is_certain_only_for_primary_text():
    """The column must discriminate: a gazette record earns `certain`, a summary does not."""
    store = ClauseStore()
    gazette = [c.clause_id for c in store.all_clauses() if c.quotable][:2]
    summary = [c.clause_id for c in store.all_clauses() if not c.is_real_text][:1]
    assert gazette and summary, "the corpus must contain both kinds for this test to mean anything"

    conf, unverified = confidence_for(gazette, store)
    assert conf == "certain" and unverified == []

    conf, unverified = confidence_for(gazette + summary, store)
    assert conf == "likely" and unverified == summary


def test_a_negative_finding_cannot_be_certain_on_non_quotable_text():
    """A record carrying page-break artefacts cannot establish that something is ABSENT."""
    store = ClauseStore()
    artefacted = [c.clause_id for c in store.all_clauses()
                  if c.is_real_text and not c.quotable][:1]
    if not artefacted:
        pytest.skip("no record with page-break artefacts in this corpus")
    assert confidence_for(artefacted, store, negative_finding=False)[0] == "certain"
    assert confidence_for(artefacted, store, negative_finding=True)[0] == "likely"


def test_confidence_is_never_read_from_the_yaml():
    """A hand-written confidence in document_gaps.yaml must have no effect on the register."""
    for gap in load_document_gaps():
        assert "confidence" not in gap, (
            f"{gap['gap_id']} declares a confidence; the generator computes it and a declared "
            f"one would silently disagree with the clause store")


def test_every_document_gap_has_a_valid_type_and_three_instances():
    gaps = load_document_gaps()
    assert len(gaps) >= 5
    for gap in gaps:
        assert gap["gap_type"] in VALID_GAP_TYPES
        assert gap.get("india_clause_ids"), f"{gap['gap_id']} cites no Indian instrument"
        # A neighbour or global cell may legitimately be "none found", but it must be said.
        assert gap.get("neighbour_clause_ids") is not None or gap.get("neighbour_note")
        assert gap.get("global_clause_ids") or gap.get("global_note")


def test_gap_register_has_the_rubric_columns_first_and_enough_rows():
    path = ROOT / "outputs/gap_register.csv"
    if not path.exists():
        pytest.skip("no register; python scripts/run_demo.py")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) >= 5
    assert list(rows[0].keys())[: len(RUBRIC_COLUMNS)] == RUBRIC_COLUMNS
    for row in rows:
        assert row["confidence"] in ("certain", "likely")
        assert row["gap_type"] in VALID_GAP_TYPES
        for col in ("india_instance", "neighbour_instance", "global_example", "evidence"):
            assert row[col].strip(), f"{row['gap_id']}.{col} is empty"


def test_gap_types_cover_all_four_of_the_rubrics_classes():
    path = ROOT / "outputs/gap_register.csv"
    if not path.exists():
        pytest.skip("no register")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert set(VALID_GAP_TYPES) <= {r["gap_type"] for r in rows}


# ------------------------------------------------------------- scenario provenance
def test_every_constructed_event_is_flagged_synthetic():
    """A constructed event must be machine-identifiable, not identifiable by its id prefix."""
    scen = load_scenario(SCENARIO)
    for event in scen.events:
        constructed = event.event_id.startswith("sim")
        assert event.synthetic is constructed, (
            f"{event.event_id}: synthetic={event.synthetic} but the id says "
            f"constructed={constructed}")
    assert sum(1 for e in scen.events if e.synthetic) >= 3
    assert sum(1 for e in scen.events if not e.synthetic) >= 5


def test_the_forged_order_is_both_synthetic_and_inauthentic():
    scen = load_scenario(SCENARIO)
    forged = [e for e in scen.events if e.authentic is False]
    assert forged, "property P2 has nothing to catch"
    for event in forged:
        assert event.synthetic, f"{event.event_id} is a forged order presented as history"


def test_scenario_declares_a_cap_epoch_with_an_offset():
    scen = load_scenario(SCENARIO)
    assert scen.epoch_iso, "no epoch_iso: CAP `sent` cannot be a real dateTime"
    assert "+" in scen.epoch_iso or scen.epoch_iso.endswith("Z")


def test_declared_area_shapes_are_valid_cap_geometry():
    """Every shape the scenario declares must parse; none may be invented district boundaries."""
    scen = load_scenario(SCENARIO)
    for area, circle in scen.area_circles.items():
        assert check_circle(circle), area
    for area, polygon in scen.area_polygons.items():
        assert check_polygon(polygon), area


def test_landfall_matches_the_imd_release_timing():
    """T+6285 min = 104.75 h, which is the pre-cyclone-watch lead time the IMD release states."""
    scen = load_scenario(SCENARIO)
    landfall = [e for e in scen.events if e.type == "LANDFALL"]
    assert landfall
    assert round(min(e.t_minutes for e in landfall) / 60, 2) == 104.75


# -------------------------------------------------------------- the audit surface
def test_every_actionable_proposal_cites_a_clause_the_pack_defines():
    run = ROOT / "runs/amphan_2020__india_current__rule__seed0.jsonl"
    if not run.exists():
        pytest.skip("no demo run")
    store = ClauseStore()
    checked = 0
    for line in run.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry["kind"] != "PROPOSAL":
            continue
        p = entry["payload"]
        if p["action_type"] in ("ASK", "NOOP"):
            continue
        assert p["reasoning"], f"{p['proposal_id']} has no reasoning"
        assert p["cited_rule_ids"], f"{p['proposal_id']} cites no rule"
        assert p["cited_clause_ids"], f"{p['proposal_id']} cites no clause"
        for cid in p["cited_clause_ids"]:
            assert store.exists(cid), f"{p['proposal_id']} cites unknown clause {cid}"
        checked += 1
    assert checked > 0


def test_the_audit_sample_verifies_on_its_own():
    """A prefix of a hash chain is a chain; a curated subset would not be."""
    sample = ROOT / "outputs/audit_sample.jsonl"
    if not sample.exists():
        pytest.skip("no sample; python scripts/export_audit_sample.py")
    from chakravyuh.audit.ledger import verify
    ok, msg = verify(sample)
    assert ok, msg


@pytest.mark.slow
def test_tamper_demo_detects_a_single_character_edit():
    run = ROOT / "runs/amphan_2020__india_current__rule__seed0.jsonl"
    if not run.exists():
        pytest.skip("no demo run")
    proc = subprocess.run([sys.executable, "scripts/verify_ledger.py", "--tamper-demo", str(run)],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr
    assert "FAIL" in proc.stdout, proc.stdout
    assert "tampered at seq" in proc.stdout or "hash mismatch" in proc.stdout


# ------------------------------------------------------------ abstention eval set
def test_the_eval_set_has_answerable_and_unanswerable_questions():
    rows = [json.loads(l) for l in
            (ROOT / "data/eval/retrieval_qa.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    answerable = [r for r in rows if r.get("gold_clause_ids")]
    abstain = [r for r in rows if not r.get("gold_clause_ids")]
    assert len(answerable) >= 30
    assert len(abstain) >= 3
    store = ClauseStore()
    for row in answerable:
        for cid in row["gold_clause_ids"]:
            assert store.exists(cid), f"{row['qid']} golds a missing clause {cid}"
    for row in abstain:
        assert row.get("why"), f"{row['qid']} abstains with no stated reason"


def test_retrieval_eval_reports_abstention_separability():
    path = ROOT / "outputs/retrieval_eval.json"
    if not path.exists():
        pytest.skip("no eval; python scripts/eval_retrieval.py")
    results = json.loads(path.read_text(encoding="utf-8"))
    scored = [r for r in results if r.get("questions")]
    assert len(scored) >= 3
    for r in scored:
        assert r.get("abstention_questions", 0) >= 3, r["mode"]
        sep = r.get("abstention_separability")
        assert sep is not None and 0.0 <= sep <= 1.0, r["mode"]


# --------------------------------------------------------------- ITU alignment
def test_ai_readiness_map_accounts_for_every_itu_dimension():
    src = ROOT / "data/sources/INTL/02_ITU_AI_Readiness_dimensions.json"
    out = ROOT / "docs/ai_readiness_map.md"
    if not out.exists():
        pytest.skip("no map; python scripts/gen_ai_readiness_map.py")
    data = json.loads(src.read_text(encoding="utf-8"))
    text = out.read_text(encoding="utf-8")
    for dim in data["dimensions"]:
        assert dim["name"] in text, f"D{dim['id']} {dim['name']!r} is unaccounted for"


def test_d1_is_the_data_model_marketplace_not_open_source():
    """The §0 correction, asserted against ITU's file rather than against our memory of it."""
    data = json.loads(
        (ROOT / "data/sources/INTL/02_ITU_AI_Readiness_dimensions.json").read_text(encoding="utf-8"))
    d1 = next(d for d in data["dimensions"] if d["id"] == 1)
    assert d1["name"] == "Data/Model Marketplace"
    assert "opensource" in {f["id"] for f in data["factors"]}
    assert "Open Source" not in {d["name"] for d in data["dimensions"]}


@pytest.mark.slow
def test_rubric_audit_has_no_failing_checks():
    proc = subprocess.run([sys.executable, "scripts/rubric_audit.py"],
                          capture_output=True, text=True, cwd=ROOT)
    assert proc.returncode == 0, proc.stdout[-3000:]
    assert "0 FAIL" in proc.stdout, proc.stdout[-3000:]
