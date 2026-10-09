"""P3 gate (spec §10): same seed -> identical ledger hash twice. Everything else rests on this."""
from __future__ import annotations

from chakravyuh.agents.base import ProposalIdFactory
from chakravyuh.agents.rule_agents import build_rule_agents
from chakravyuh.audit.ledger import verify
from chakravyuh.sim.runner import context_for, run


def test_same_seed_identical_ledger_hash(scenario, india_pack, tmp_path):
    a = run(scenario, india_pack, agents=build_rule_agents(ProposalIdFactory()), seed=0,
            ledger_path=tmp_path / "a.jsonl")
    b = run(scenario, india_pack, agents=build_rule_agents(ProposalIdFactory()), seed=0,
            ledger_path=tmp_path / "b.jsonl")
    assert a.ledger_head_hash == b.ledger_head_hash
    assert (tmp_path / "a.jsonl").read_text() == (tmp_path / "b.jsonl").read_text()


def test_ledger_verifies_after_a_run(scenario, india_pack, tmp_path):
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    ok, msg = verify(r.ledger_path)
    assert ok, msg


def test_run_is_reproducible_across_packs(scenario, packs, tmp_path):
    for pack_id, pack in packs.items():
        first = run(scenario, pack, seed=3, ledger_path=tmp_path / f"{pack_id}-1.jsonl")
        second = run(scenario, pack, seed=3, ledger_path=tmp_path / f"{pack_id}-2.jsonl")
        assert first.ledger_head_hash == second.ledger_head_hash, pack_id


def test_agents_never_touch_the_world(scenario, india_pack, tmp_path):
    """Only the Game Master writes. An agent holding a world reference would be a design break."""
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    ctx = context_for(r)
    for agent in build_rule_agents().values():
        assert not any(hasattr(agent, attr) for attr in ("world", "state", "ledger"))
    assert ctx["world"].t_minutes == scenario.horizon_min


def test_events_are_redacted_before_reaching_an_agent(scenario, india_pack, tmp_path):
    """`authentic` and `truth` are ground truth; no inbox may carry them."""
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    ctx = context_for(r)
    for inbox in ctx["inboxes"].values():
        for item in inbox.items:
            assert "authentic" not in item["event"]
            assert "truth" not in (item["event"].get("payload") or {})


def test_information_is_uneven_across_roles(scenario, india_pack, tmp_path):
    """The brief's mandatory property: different agents hold different information."""
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    ctx = context_for(r)
    seen = {role: inbox.types_seen() for role, inbox in ctx["inboxes"].items()}
    assert seen["tsp_network"] != seen["competent_authority"]
    assert "IMD_WARNING" not in seen["tsp_network"], "the operator must not get warnings directly"
    assert "IMD_WARNING" in seen["competent_authority"]
    latencies = ctx["bus"].latency_report()
    assert latencies["neighbour_authority"]["max_latency_min"] > 0, "cross-border channel is slow"


def test_tick_count_matches_horizon(scenario, india_pack, tmp_path):
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    assert r.tick_count == scenario.horizon_min // scenario.tick_min + 1


def test_run_context_window_is_bounded(scenario, india_pack, tmp_path):
    """A fuzz campaign runs the simulator thousands of times; the context table must not grow."""
    from chakravyuh.sim import runner

    first = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "first.jsonl",
                run_suffix="ctx-first")
    assert context_for(first)["world"] is not None

    for i in range(runner.CONTEXT_LIMIT + 5):
        run(scenario, india_pack, seed=i, ledger_path=tmp_path / "x.jsonl",
            run_suffix=f"ctx-{i}")

    assert len(runner.result_context) <= runner.CONTEXT_LIMIT
    import pytest
    with pytest.raises(KeyError, match="evicted"):
        context_for(first)
