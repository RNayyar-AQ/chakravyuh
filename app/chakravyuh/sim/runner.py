"""run(scenario, pack, agents, seed) -> RunResult. Y.3172 node: D.

The tick loop (spec §5.3). At each 15-minute tick:
  1. release due events          (scenario timeline, chunked and progressive)
  2. deliver via bus with delays (per-role, uneven, incomplete)
  3. agents observe and propose  (only their own inbox; no world access)
  4. GM resolves in deterministic order, consulting the policy engine
  5. world dynamics step
  6. ledger append

Determinism: no wall clock, no uuid, no RNG except a seeded generator threaded explicitly. Two
runs of the same (scenario, pack, agents, seed) produce an identical ledger head hash, which is
the P3 acceptance gate and the basis of every replay claim in the report.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..agents.base import ProposalIdFactory
from ..agents.rule_agents import build_rule_agents
from ..agents.roles import ROLES, Inbox
from ..audit.ledger import Ledger
from ..schemas import Event, PolicyPack, Proposal, PropertyResult, RunResult
from ..y3172 import node
from ..fuzz.properties import check_all
from ..world import dynamics
from .bus import Bus
from .events import Scenario
from .game_master import GameMaster, HumanGate

RUNS_DIR = Path("runs")


def run_id_for(scenario_id: str, pack_id: str, seed: int, tier: str, suffix: str = "") -> str:
    """Deterministic run id: the same inputs always name the same run, so replay_cmd is honest."""
    base = f"{scenario_id}__{pack_id}__{tier}__seed{seed}"
    return f"{base}__{suffix}" if suffix else base


@node("D")
def run(scenario: Scenario, pack: PolicyPack, agents: Optional[Mapping[str, object]] = None,
        seed: int = 0, *, mutations: Sequence[dict] = (), runs_dir: str | Path = RUNS_DIR,
        human_gate_mode: str = "batch", tier: Optional[str] = None,
        ledger_path: Optional[str | Path] = None, run_suffix: str = "") -> RunResult:
    """Execute one full simulation and return its RunResult (properties included)."""
    started = time.perf_counter()

    ids = ProposalIdFactory()
    agents = dict(agents) if agents is not None else build_rule_agents(ids)
    tier = tier or getattr(next(iter(agents.values())), "tier", "rule")
    rid = run_id_for(scenario.scenario_id, pack.pack_id, seed, tier, run_suffix)

    path = Path(ledger_path) if ledger_path else Path(runs_dir) / f"{rid}.jsonl"
    if path.exists():
        path.unlink()      # a run id names one run; never append onto a previous chain
    ledger = Ledger(path, run_id=rid)

    world = scenario.world()
    bus = Bus(scenario.channel_latency_min, scenario.default_latency_min)
    gm = GameMaster(world, pack, ledger, HumanGate(mode=human_gate_mode), agents=agents)
    inboxes = {rid_: Inbox(rid_) for rid_ in ROLES}

    ledger.append("EVENT", {
        "kind": "RUN_HEADER", "run_id": rid, "scenario_id": scenario.scenario_id,
        "pack_id": pack.pack_id, "pack_version": pack.version, "pack_mode": pack.mode,
        "seed": seed, "agent_tier": tier, "tick_min": scenario.tick_min,
        "horizon_min": scenario.horizon_min, "mutations": list(mutations),
        "thresholds": scenario.thresholds.model_dump(),
        "roles": sorted(agents), "world": world.snapshot(),
    }, 0)

    pending: list[Event] = sorted(scenario.events, key=lambda e: (e.t_minutes, e.event_id))
    for ev in pending:
        gm.register_event(ev)

    ticks = 0
    t = 0
    while t <= scenario.horizon_min:
        # 1. release due scenario events
        due = [e for e in pending if e.t_minutes <= t]
        pending = [e for e in pending if e.t_minutes > t]
        for ev in sorted(due, key=lambda e: (e.t_minutes, e.event_id)):
            gm.apply_exogenous(ev, t)
            bus.publish(ev, t)

        # 2. deliver what has arrived
        for delivery in bus.deliver_due(t):
            gm.record_delivery(delivery)
            inboxes[delivery.role].add(delivery)

        # 3. agents propose from their own inbox only
        proposals: list[Proposal] = []
        for role_id in sorted(agents, key=lambda r: (ROLES[r].priority if r in ROLES else 99, r)):
            agent = agents[role_id]
            got = agent.observe(inboxes[role_id], t, pack) or []
            proposals.extend(p for p in got if p.action_type != "NOOP")

        # 4. GM resolves, then applies anything whose delay/human gate has cleared
        gm.resolve_tick(proposals, t)
        gm.release_deferred(t)
        gm.release_human_gate(t)

        # derived events (an order becoming a fact) go back onto the bus
        for ev in gm.take_derived():
            bus.publish(ev, t)

        # 5. world step
        step_info = dynamics.step(world, t)
        if step_info["suspensions_expired"] or step_info["cells_lost_to_power"]:
            ledger.append("EFFECT", {"kind": "WORLD_STEP", **step_info}, t)

        ticks += 1
        t += scenario.tick_min

    # Anything still in flight at the horizon never arrived: that itself is evidence.
    undelivered = bus.in_flight()
    results: list[PropertyResult] = check_all(world, scenario.thresholds, gm)
    for r in results:
        ledger.append("PROPERTY", r.model_dump(), scenario.horizon_min)

    ledger.append("EVENT", {
        "kind": "RUN_FOOTER", "run_id": rid, "world": world.snapshot(),
        "verdicts": gm.verdict_counts(), "blocks_by_reason": gm.blocks_by_reason(),
        "latency_by_role": bus.latency_report(), "undelivered_at_horizon": undelivered,
        "forged_executions": len(gm.forged_executions),
        "human_gate": {"mode": gm.gate.mode, "decisions": gm.gate.decisions,
                       "still_pending": sorted(gm.gate.pending)},
        "properties": {r.property_id: {"passed": r.passed, "margin": r.margin} for r in results},
    }, scenario.horizon_min)

    llm_calls = sum(getattr(a, "llm_calls", 0) for a in agents.values())
    result = RunResult(
        run_id=rid, pack_id=pack.pack_id, scenario_id=scenario.scenario_id, seed=seed,
        agent_tier=tier, ledger_path=str(path), ledger_head_hash=ledger.head_hash,
        properties=results, mutations=list(mutations), tick_count=ticks,
        wall_seconds=round(time.perf_counter() - started, 4), llm_calls=llm_calls,
    )

    # Gap classification needs the GM's views and the bus; attach them for the caller without
    # putting non-serialisable objects on the Pydantic model.
    _remember_context(result.run_id, {"world": world, "gm": gm, "bus": bus, "scenario": scenario,
                                      "pack": pack, "inboxes": inboxes})
    return result


# Side table of live objects from the most recent runs, keyed by run_id. The RunResult itself stays
# serialisable; analysis code that needs the world asks for it here.
#
# BOUNDED on purpose. Each entry pins a whole WorldState, GameMaster and Bus, and a fuzz campaign
# runs the simulator thousands of times -- an unbounded dict would retain every one of them and the
# campaign would grow without limit. Oldest entries are evicted first; analysis always runs
# immediately after the run that produced it, so a small window is enough.
CONTEXT_LIMIT = 64
result_context: "OrderedDict[str, dict]" = OrderedDict()


def _remember_context(run_id: str, ctx: dict) -> None:
    result_context[run_id] = ctx
    result_context.move_to_end(run_id)
    while len(result_context) > CONTEXT_LIMIT:
        result_context.popitem(last=False)


def context_for(result: RunResult) -> dict:
    """Live objects (world, GM, bus, inboxes) for a recent run.

    Raises KeyError once the run has been evicted from the bounded window, rather than returning
    a stale or empty context that would silently produce wrong analysis.
    """
    ctx = result_context.get(result.run_id)
    if ctx is None:
        raise KeyError(
            f"no live context for run {result.run_id}: it has been evicted from the most recent "
            f"{CONTEXT_LIMIT} runs. Re-run it to analyse it.")
    result_context.move_to_end(result.run_id)
    return ctx
