"""The narrated run must be the run. Narration is output only; it may not invent a number.

Every assertion here compares what the transcript says against the artefact it claims to be
reading -- the ledger on disk, the clause store's digests, the run's own property results.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "app" / "scripts" / "narrate_run.py"

sys.path.insert(0, str(ROOT / "app"))

from chakravyuh.audit.ledger import verify  # noqa: E402
from chakravyuh.kb.clause_store import ClauseStore  # noqa: E402


def narrate(*args: str) -> str:
    """Run the narrator and return its transcript, colour stripped."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--color", "never", *args],
        cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
    assert proc.returncode == 0, f"narrator exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    return proc.stdout


@pytest.fixture(scope="module")
def india() -> str:
    return narrate("--skip-retrieval", "--pack", "india_current")


def test_the_head_hash_narrated_is_the_head_of_the_ledger_it_names(india: str):
    """The closing hash is not formatted from memory: re-walk the chain and compare."""
    path = re.search(r"file\s+(runs/\S+\.jsonl)", india)
    head = re.search(r"head\s+([0-9a-f]{32})…", india)
    assert path and head, "the transcript must name its ledger and its head hash"

    ledger = ROOT / path.group(1)
    assert ledger.exists(), f"the narrator named {ledger}, which does not exist"
    ok, message = verify(ledger)
    assert ok, f"the ledger the narrator read does not verify: {message}"
    assert message.split("head ")[1].startswith(head.group(1)[:16])


def test_entry_counts_narrated_are_the_entries_on_disk(india: str):
    """`928 entries: 394 VERDICT, …` is counted from the file, so the file must agree."""
    line = re.search(r"(\d+) entries: (.+)", india)
    path = re.search(r"file\s+(runs/\S+\.jsonl)", india)
    assert line and path
    ledger = ROOT / path.group(1)
    actual = sum(1 for raw in ledger.read_text(encoding="utf-8").splitlines() if raw.strip())
    assert int(line.group(1)) == actual, "the narrated entry count is not the file's length"


def test_every_clause_digest_printed_is_the_digest_the_store_holds(india: str):
    """A citation is worth nothing if its hash is decorative. Check each one against the store."""
    store = ClauseStore()
    try:
        digests = {c.clause_id: c.sha256 for c in store.all_clauses()}
    finally:
        store.close()

    printed = re.findall(r"clause\s+(\S+)\s+([0-9a-f]{12})…", india)
    assert printed, "no clause citation was narrated at all"
    wrong = [(cid, short) for cid, short in printed
             if not digests.get(cid, "").startswith(short)]
    assert not wrong, f"these citations printed a digest the clause store does not hold: {wrong}"


def test_the_forged_order_is_narrated_as_executing(india: str):
    """The finding the demo exists to show must survive the collapse rule."""
    assert "authentic=False (forged)" in india, "the forged ORDER event was not narrated"
    assert "driven by an order that failed authentication" in india, (
        "the transcript did not say that a forged order drove an execution")
    forged_block = india.split("authentic=False (forged)", 1)[1]
    assert "EXECUTED  SUSPEND_SERVICE" in forged_block.split("T+6285")[0], (
        "the suspension that the forged order caused was collapsed away")


def test_the_properties_narrated_are_the_properties_the_run_measured(india: str):
    """P1-P4 with their margins, and the margin signs must match the pass/fail shown."""
    rows = re.findall(r"(P\d)\s+(PASS|FAIL)\s+margin\s+([-+][\d.]+)", india)
    assert len(rows) == 4, f"expected four properties, narrated {rows}"
    for pid, mark, margin in rows:
        negative = float(margin) < 0
        assert (mark == "FAIL") == negative, (
            f"{pid} says {mark} but its margin is {margin}: a negative margin is a violation")


def test_two_narrations_of_the_same_pack_agree(india: str):
    """Determinism, end to end -- the only lines allowed to differ are the wall-clock ones."""
    again = narrate("--skip-retrieval", "--pack", "india_current")
    drop = re.compile(r"ticks in [\d.]+s")
    assert drop.sub("", again) == drop.sub("", india), (
        "the same pack and seed narrated differently twice")


def test_a_different_pack_changes_the_outcome_and_nothing_else(india: str):
    """The comparison the project rests on, asserted on the transcripts themselves."""
    us = narrate("--skip-retrieval", "--pack", "fcc_mdri")
    for shared in ("amphan_2020", "224 cells", "7 events from the source release"):
        assert shared in india and shared in us, f"{shared!r} should be identical across packs"
    assert "driven by an order that failed authentication" not in us, (
        "fcc_mdri is the comparator that refuses the forged order; it should not execute one")


def test_narration_decides_nothing():
    """The narrator reads and prints. If it ever evaluated a rule, it could disagree with the run."""
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert "chakravyuh.policy.engine" not in imported, (
        "the narrator must not import the policy engine: it reports verdicts, it does not form them")

    narrator = (ROOT / "app" / "chakravyuh" / "narrate.py").read_text(encoding="utf-8")
    for banned in ("import json", "evaluate(", "Ledger(", "WorldState"):
        assert banned not in narrator, f"narrate.py should be formatting only, but mentions {banned}"
