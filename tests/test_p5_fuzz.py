"""P5 gate (spec §10): fuzzing finds >=1 minimal failure, and replay_cmd reproduces it."""
from __future__ import annotations

import io
import unittest

import pytest

from chakravyuh.fuzz import machine
from chakravyuh.fuzz.mutations import (apply_mutations, delay_channel,
                                       delay_event_for_role, inject_forged_order)
from chakravyuh.fuzz.shrink_report import build_card, dedupe, failure_id, write_cards


def test_mutations_are_pure(scenario):
    before = len(scenario.events)
    mutated, record = inject_forged_order(scenario, "OD-COAST", 200)
    assert len(scenario.events) == before, "the base scenario must not be mutated in place"
    assert len(mutated.events) == before + 1
    assert record["args"]["area"] == "OD-COAST"


def test_mutation_record_replays_exactly(scenario):
    s1, m1 = inject_forged_order(scenario, "OD-COAST", 200)
    s2, m2 = delay_channel(s1, "sdma_alerts", 120)
    replayed = apply_mutations(scenario, [m1, m2])
    assert len(replayed.events) == len(s2.events)
    assert replayed.channel_latency_min["sdma_alerts"] == s2.channel_latency_min["sdma_alerts"]


def test_mutation_without_args_cannot_be_replayed(scenario):
    with pytest.raises(ValueError, match="cannot be replayed"):
        apply_mutations(scenario, [{"op": "delay_channel", "role": "cert_in", "dt": 30}])


def test_failure_id_ignores_generated_event_ids(scenario):
    _, m1 = inject_forged_order(scenario, "OD-COAST", 200, seq=0)
    m2 = dict(m1, created_event_id="something-else")
    assert failure_id("p", "P2", [m1]) == failure_id("p", "P2", [m2])


def test_fuzzer_finds_a_new_failure_in_a_passing_pack(scenario, packs, tmp_path):
    """fcc_mdri passes all four unmutated, so anything found here is a NEW failure."""
    info = machine.configure(scenario=scenario, pack=packs["fcc_mdri"],
                             runs_dir=str(tmp_path), baseline_only=True)
    assert info["asserted"], "fcc_mdri should pass at baseline and so have something to fuzz"

    TC = machine.make_test(max_examples=60, stateful_step_count=4)
    unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(
        unittest.TestLoader().loadTestsFromTestCase(TC))
    assert machine.CONFIG["failures"], "no counterexample found within the budget"


def test_event_delay_overrides_channel_latency(scenario, packs, tmp_path):
    """Precedence matters for every fuzz result: an event's own per-role delay wins.

    `ev001` already sets delay_by_role[sdma_alerts]=15, so raising the sdma_alerts CHANNEL
    latency changes nothing for that event. Only delay_event_for_role moves it. A fuzz campaign
    that found the channel mutation "ineffective" would be reporting this rule, not the law.
    """
    from chakravyuh.sim.runner import run
    channel = apply_mutations(scenario, [delay_channel(scenario, "sdma_alerts", 240)[1]])
    per_event = apply_mutations(scenario, [delay_event_for_role(scenario, "ev001",
                                                                "sdma_alerts", 240)[1]])
    a = run(channel, packs["fcc_mdri"], seed=0, ledger_path=tmp_path / "a.jsonl")
    b = run(per_event, packs["fcc_mdri"], seed=0, ledger_path=tmp_path / "b.jsonl")
    p3 = lambda r: next(p for p in r.properties if p.property_id == "P3")
    assert p3(a).passed, "channel latency is overridden by ev001's own per-role delay"
    assert not p3(b).passed, "delaying the event for that role does break P3"


def test_card_reproduces_and_round_trips(scenario, packs, tmp_path):
    """A card that does not replay is worse than no card; build_card must prove it replays."""
    _, m = delay_event_for_role(scenario, "ev001", "sdma_alerts", 240)
    card = build_card(scenario, packs, "fcc_mdri", "P3", [m], seed=0, runs_dir=str(tmp_path))
    assert card is not None, "this mutation should break P3 under fcc_mdri"
    assert card.margin < 0
    assert card.replay_cmd.startswith("python scripts/run_fuzz.py --replay")

    again = build_card(scenario, packs, "fcc_mdri", "P3", card.mutations, seed=card.seed,
                       runs_dir=str(tmp_path))
    assert again is not None
    assert again.failure_id == card.failure_id
    assert again.margin == card.margin, "replay must give the identical margin"

    paths = write_cards([card], out_dir=tmp_path / "cards")
    assert (tmp_path / "cards" / f"{card.failure_id}.json").exists()
    assert (tmp_path / "cards" / "index.json").exists()
    assert len(paths) == 2


def test_card_is_none_when_the_case_does_not_reproduce(scenario, packs, tmp_path):
    card = build_card(scenario, packs, "fcc_mdri", "P2", [], seed=0, runs_dir=str(tmp_path))
    assert card is None, "fcc_mdri passes P2 unmutated, so there is no card to build"


def test_dedupe_keeps_the_worst_margin(scenario, packs, tmp_path):
    _, m = delay_event_for_role(scenario, "ev001", "sdma_alerts", 240)
    a = build_card(scenario, packs, "fcc_mdri", "P3", [m], seed=0, runs_dir=str(tmp_path))
    assert a is not None
    worse = a.model_copy(update={"margin": a.margin - 100})
    assert dedupe([a, worse])[0].margin == a.margin - 100


def test_india_pack_has_nothing_left_to_fuzz(scenario, packs, tmp_path):
    """It fails everything unmutated. The fuzzer must say so rather than re-finding them."""
    info = machine.configure(scenario=scenario, pack=packs["india_current"],
                             runs_dir=str(tmp_path), baseline_only=True)
    assert info["asserted"] == ()
    assert set(info["excluded_at_baseline"]) == {"P1", "P2", "P3", "P4"}
