"""Hypothesis stateful policy fuzzing. Y.3172 node: M/SINK."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from ..policy.compiler import compile_pack
from ..schemas import PolicyPack
from ..sim.events import Scenario, load_scenario
from ..sim.runner import run
from ..y3172 import node
from . import mutations as mut

DEFAULT_SCENARIO = Path("data/scenarios/amphan_2020.yaml")
DEFAULT_PACK = Path("data/packs/india_current.yaml")

CONFIG: dict = {"scenario": None, "pack": None, "runs_dir": "runs/fuzz",
                "properties": ("P1", "P2", "P3", "P4"), "failures": []}


def configure(scenario: Scenario | str | Path = DEFAULT_SCENARIO,
              pack: PolicyPack | str | Path = DEFAULT_PACK,
              runs_dir: str = "runs/fuzz",
              properties: tuple[str, ...] = ("P1", "P2", "P3", "P4"),
              baseline_only: bool = True) -> dict:
    """Point the state machine at a scenario and pack, and reset the collected failures."""
    CONFIG["scenario"] = scenario if isinstance(scenario, Scenario) else load_scenario(scenario)
    CONFIG["pack"] = pack if isinstance(pack, PolicyPack) else compile_pack(pack)
    CONFIG["runs_dir"] = runs_dir
    CONFIG["failures"] = []

    baseline = run(CONFIG["scenario"], CONFIG["pack"], seed=0, runs_dir=runs_dir,
                   ledger_path=Path(runs_dir) / "_baseline.jsonl")
    outcomes = {p.property_id: p.passed for p in baseline.properties}
    CONFIG["baseline"] = outcomes
    if baseline_only:
        kept = tuple(pid for pid in properties if outcomes.get(pid, True))
        CONFIG["properties"] = kept
        CONFIG["excluded_at_baseline"] = tuple(pid for pid in properties if pid not in kept)
    else:
        CONFIG["properties"] = properties
        CONFIG["excluded_at_baseline"] = ()
    return {"baseline": outcomes, "asserted": CONFIG["properties"],
            "excluded_at_baseline": CONFIG["excluded_at_baseline"]}


def _areas() -> list[str]:
    scen = CONFIG["scenario"]
    return list(scen.areas) if scen else ["OD-COAST"]


def _event_ids() -> list[str]:
    scen = CONFIG["scenario"]
    return [e.event_id for e in scen.events] if scen else []


ROLES_ST = st.sampled_from(["competent_authority", "sdma_alerts", "tsp_network", "cert_in",
                            "neighbour_authority"])
DT_ST = st.integers(min_value=-120, max_value=240).map(lambda x: 15 * round(x / 15))
T_ST = st.integers(min_value=0, max_value=660).map(lambda x: 15 * round(x / 15))


@node("M")
class PolicyFuzzMachine(RuleBasedStateMachine):
    """Mutate the scenario, re-run, assert P1-P4. Hypothesis shrinks the failing mutation list."""
    def __init__(self):
        super().__init__()
        self.scenario: Scenario = CONFIG["scenario"]
        self.pack: PolicyPack = CONFIG["pack"]
        if self.scenario is None or self.pack is None:
            raise RuntimeError("call chakravyuh.fuzz.machine.configure(...) before fuzzing")
        self.applied: list[dict] = []
        self.last_result = None

    @initialize()
    def start(self) -> None:
        self.applied = []
        self._rerun()

    @rule(area=st.sampled_from(_areas() or ["OD-COAST"]), t=T_ST)
    def forged_order(self, area: str, t: int) -> None:
        self._mutate(mut.inject_forged_order, area=area, t=t)

    @rule(role=ROLES_ST, dt=st.integers(min_value=15, max_value=240).map(lambda x: 15 * round(x / 15)))
    def channel_delay(self, role: str, dt: int) -> None:
        self._mutate(mut.delay_channel, role=role, dt=dt)

    @rule(area=st.sampled_from(_areas() or ["OD-COAST"]), t=T_ST)
    def rumour(self, area: str, t: int) -> None:
        self._mutate(mut.inject_rumour, area=area, t=t)

    @rule(area=st.sampled_from(_areas() or ["OD-COAST"]), t=T_ST,
          cells=st.integers(min_value=2, max_value=12))
    def damage(self, area: str, t: int, cells: int) -> None:
        self._mutate(mut.escalate_damage, area=area, t=t, cells_down=cells)

    @rule(event_id=st.sampled_from(_event_ids() or ["ev001"]), dt=DT_ST)
    def shift(self, event_id: str, dt: int) -> None:
        self._mutate(mut.shift_event, event_id=event_id, dt=dt)

    @rule(event_id=st.sampled_from(_event_ids() or ["ev001"]), role=ROLES_ST, dt=DT_ST)
    def event_delay(self, event_id: str, role: str, dt: int) -> None:
        self._mutate(mut.delay_event_for_role, event_id=event_id, role=role, dt=dt)

    def _mutate(self, fn, **kwargs) -> None:
        self.scenario, record = fn(self.scenario, **kwargs)
        self.applied.append(record)
        self._rerun()

    def _rerun(self) -> None:
        self.last_result = run(self.scenario, self.pack, seed=len(self.applied),
                               mutations=list(self.applied), runs_dir=CONFIG["runs_dir"],
                               ledger_path=Path(CONFIG["runs_dir"]) / "_fuzz_scratch.jsonl")

    @invariant()
    def properties_hold(self) -> None:
        if self.last_result is None:
            return
        for prop in self.last_result.properties:
            if prop.property_id not in CONFIG["properties"]:
                continue
            if not prop.passed:
                CONFIG["failures"].append({
                    "mutations": list(self.applied),
                    "property_id": prop.property_id,
                    "margin": prop.margin,
                    "detail": prop.detail,
                    "run_id": self.last_result.run_id,
                    "pack_id": self.pack.pack_id,
                })
                raise AssertionError(
                    f"{prop.property_id} violated under pack {self.pack.pack_id} "
                    f"(margin {prop.margin} {prop.unit}) after {len(self.applied)} mutation(s): "
                    f"{[m.get('op') for m in self.applied]}")


def make_test(max_examples: int = 300, stateful_step_count: int = 6, deadline_ms: Optional[int] = None):
    """Build the pytest-visible test class with a configured budget (300/pack for the demo)."""
    PolicyFuzzMachine.TestCase.settings = settings(
        max_examples=max_examples,
        stateful_step_count=stateful_step_count,
        deadline=deadline_ms,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
        print_blob=True,
        # A campaign that explores different worlds on each machine produces a different
        # counterexample on each machine -- the minimal case is not unique, and a warm example
        # database finds a different one from a cold CI runner. derandomize pins generation to a
        # fixed seed and database=None stops a local cache replaying what CI has never seen, so
        # the card the page shows is the card any run of the same command produces.
        derandomize=True,
        database=None,
    )
    return PolicyFuzzMachine.TestCase
