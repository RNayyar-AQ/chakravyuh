"""Shared fixtures. The clause store must exist before any pack compiles, so build it once."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from chakravyuh.kb import ingest
from chakravyuh.policy.compiler import compile_all, compile_pack
from chakravyuh.sim.events import load_scenario


@pytest.fixture(scope="session", autouse=True)
def built_kb():
    """Build the clause store from the seed corpus once per test session."""
    return ingest.build(push_chroma=False)


@pytest.fixture(scope="session")
def packs(built_kb):
    return compile_all()


@pytest.fixture(scope="session")
def india_pack(built_kb):
    return compile_pack(ROOT / "data/packs/india_current.yaml")


@pytest.fixture(scope="session")
def scenario():
    return load_scenario(ROOT / "data/scenarios/amphan_like.yaml")
