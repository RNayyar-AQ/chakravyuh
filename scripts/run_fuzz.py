#!/usr/bin/env python3
"""Policy fuzzing campaign: Hypothesis -> minimal failures -> failure cards. Y.3172: M -> SINK.

  python scripts/run_fuzz.py                        # all packs, 300 examples each
  python scripts/run_fuzz.py --max-examples 50
  python scripts/run_fuzz.py --pack fcc_mdri
  python scripts/run_fuzz.py --replay F-P3-ab12cd34 # re-run one saved failure card

Fuzzing asserts only the properties a pack ALREADY passes on the unmutated scenario, so it searches
for NEW failures instead of rediscovering the baseline ones the gap register already reports. A
pack that fails everything at baseline has nothing to fuzz, and the report says so.

Agents are rule twins: thousands of runs, zero tokens, bit-identical replay.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

warnings.filterwarnings("ignore")

from chakravyuh.fuzz import machine
from chakravyuh.fuzz.mutations import FAMILIES
from chakravyuh.fuzz.shrink_report import build_card, card_markdown, dedupe, write_cards
from chakravyuh.policy.compiler import compile_all
from chakravyuh.sim.events import load_scenario

DOCS = Path("docs")
DATA = Path("outputs")


def fuzz_pack(scenario, pack, packs, max_examples: int, steps: int, runs_dir: str) -> dict:
    """Run one pack's campaign. Returns a summary row plus any cards built."""
    info = machine.configure(scenario=scenario, pack=pack, runs_dir=runs_dir, baseline_only=True)
    row = {
        "pack_id": pack.pack_id,
        "baseline": info["baseline"],
        "asserted_properties": list(info["asserted"]),
        "excluded_at_baseline": list(info["excluded_at_baseline"]),
        "max_examples": max_examples,
        "runs_completed": 0,
        "unique_minimal_failures": 0,
        "wall_seconds": 0.0,
        "cards": [],
    }
    if not info["asserted"]:
        row["note"] = ("pack fails every property on the unmutated scenario; nothing left to fuzz. "
                       "Those failures are in the gap register.")
        return row

    started = time.perf_counter()
    TC = machine.make_test(max_examples=max_examples, stateful_step_count=steps)
    result = unittest.TextTestRunner(verbosity=0, stream=io.StringIO()).run(
        unittest.TestLoader().loadTestsFromTestCase(TC))
    row["wall_seconds"] = round(time.perf_counter() - started, 2)
    row["runs_completed"] = len(machine.CONFIG["failures"]) + max_examples  # lower bound
    row["hypothesis_found_counterexample"] = bool(result.failures or result.errors)

    # The shortest mutation list per property is Hypothesis's shrunk case for that property.
    shortest: dict[str, dict] = {}
    for f in machine.CONFIG["failures"]:
        pid = f["property_id"]
        if pid not in shortest or len(f["mutations"]) < len(shortest[pid]["mutations"]):
            shortest[pid] = f

    cards = []
    for pid, f in sorted(shortest.items()):
        card = build_card(scenario, packs, pack.pack_id, pid, f["mutations"],
                          seed=f.get("seed", 0), runs_dir=f"{runs_dir}/cards")
        if card is not None:
            cards.append(card)
    cards = dedupe(cards)
    row["unique_minimal_failures"] = len(cards)
    row["cards"] = [c.model_dump() for c in cards]
    return row, cards


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", default="data/scenarios/amphan_2020.yaml")
    ap.add_argument("--pack", action="append", help="pack id (repeatable); default all")
    ap.add_argument("--max-examples", type=int, default=300, help="Hypothesis budget per pack")
    ap.add_argument("--steps", type=int, default=6, help="mutations per example")
    ap.add_argument("--runs-dir", default="runs/fuzz")
    ap.add_argument("--replay", help="failure_id of a saved card to re-run")
    args = ap.parse_args()

    scenario = load_scenario(args.scenario)
    all_packs = compile_all()

    if args.replay:
        return replay_card(args.replay, scenario, all_packs)

    packs = {k: v for k, v in all_packs.items() if not args.pack or k in args.pack}
    if not packs:
        raise SystemExit(f"no pack matched {args.pack}; available: {sorted(all_packs)}")

    rows, all_cards = [], []
    for pack_id in sorted(packs):
        print(f"\n=== fuzzing {pack_id} (budget {args.max_examples}, {args.steps} steps) ===")
        out = fuzz_pack(scenario, packs[pack_id], all_packs, args.max_examples, args.steps,
                        args.runs_dir)
        row, cards = (out, []) if isinstance(out, dict) else out
        rows.append(row)
        all_cards.extend(cards)
        if row.get("note"):
            print(f"  {row['note']}")
        else:
            print(f"  asserted {row['asserted_properties']}, "
                  f"{row['unique_minimal_failures']} unique minimal failure(s), "
                  f"{row['wall_seconds']}s")
            for c in cards:
                print(f"    {c.failure_id}: {c.violated_property} margin={c.margin:+g} "
                      f"({c.gap_class}) via {[m['op'] for m in c.mutations]}")

    DOCS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    paths = write_cards(all_cards)
    (DATA / "fuzz_summary.json").write_text(json.dumps(rows, indent=2, sort_keys=True, default=str),
                                           encoding="utf-8")
    (DOCS / "failure_atlas.md").write_text(atlas(rows, all_cards), encoding="utf-8")
    print(f"\nwrote {DOCS / 'failure_atlas.md'}, {DATA / 'fuzz_summary.json'}, "
          f"{len(paths)} card file(s) under outputs/failures/")
    return 0


def atlas(rows: list[dict], cards: list) -> str:
    lines = [
        "# Failure atlas (generated by scripts/run_fuzz.py -- do not edit)",
        "",
        "Hypothesis stateful fuzzing over mutations of the base scenario, with rule-based agent",
        "twins. Each campaign asserts only the properties its pack already passes unmutated, so",
        "these are **new** failures, not the baseline ones in `outputs/gap_register.csv`.",
        "",
        "## Mutation families",
        "",
        "| Family | What it does |",
        "|---|---|",
    ]
    for name, desc in sorted(FAMILIES.items()):
        lines.append(f"| `{name}` | {desc} |")
    lines += ["", "MVP scope is the first two families (forged order, delayed/rumour-driven events);",
              "the rest come free from the same state machine and are reported where they fire.",
              "", "## Campaigns", "",
              "| Pack | Baseline | Asserted | Excluded (already failing) | Unique minimal failures | Wall (s) |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        base = " ".join(f"{k}={'P' if v else 'F'}" for k, v in sorted(r["baseline"].items()))
        lines.append(f"| `{r['pack_id']}` | {base} | {', '.join(r['asserted_properties']) or '-'} "
                     f"| {', '.join(r['excluded_at_baseline']) or '-'} "
                     f"| {r['unique_minimal_failures']} | {r['wall_seconds']} |")
    for r in rows:
        if r.get("note"):
            lines += ["", f"- `{r['pack_id']}`: {r['note']}"]

    lines += ["", "## Failure cards", ""]
    if cards:
        for c in cards:
            lines.append(card_markdown(c))
    else:
        lines.append("_No new minimal failure was found within the budget._")
    return "\n".join(lines)


def replay_card(failure_id: str, scenario, packs) -> int:
    path = Path("outputs/failures") / f"{failure_id}.json"
    if not path.exists():
        print(f"no card at {path}", file=sys.stderr)
        return 2
    card = json.loads(path.read_text(encoding="utf-8"))
    rebuilt = build_card(scenario, packs, card["pack_id"], card["violated_property"],
                         card["mutations"], seed=card["seed"], runs_dir="runs/replay")
    if rebuilt is None:
        print(f"{failure_id} did NOT reproduce", file=sys.stderr)
        return 1
    print(f"{failure_id} reproduced: {rebuilt.violated_property} margin={rebuilt.margin:+g} "
          f"({rebuilt.gap_class}); passes under {rebuilt.passes_under_packs or 'no pack'}")
    print(f"margin matches saved card: {rebuilt.margin == card['margin']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
