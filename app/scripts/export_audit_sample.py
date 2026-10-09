#!/usr/bin/env python3
"""Export the head of a run ledger as a standalone, self-verifying audit sample. Y.3172 node: SINK.

Why a prefix and not a selection. A hash-chained ledger is verifiable from its first entry
forward, so the first N lines are themselves a valid chain and `verify_ledger.py` accepts the
sample on its own. A hand-picked subset of interesting entries would NOT verify -- the chain
would show gaps -- and a reviewer would have to take our word for it. The prefix is the only
excerpt that keeps the guarantee it is meant to demonstrate.

  python app/scripts/export_audit_sample.py                     # default run, first 50 entries
  python app/scripts/export_audit_sample.py --n 200 --run runs/....jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.audit.ledger import verify

DEFAULT_RUN = Path("runs/amphan_2020__india_current__rule__seed0.jsonl")
OUT = Path("outputs/audit_sample.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--n", type=int, default=50, help="number of leading ledger entries")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.run.exists():
        print(f"no such run: {args.run}; run app/scripts/run_demo.py first", file=sys.stderr)
        return 2

    ok, msg = verify(args.run)
    if not ok:
        print(f"source ledger does not verify ({msg}); refusing to export", file=sys.stderr)
        return 1

    lines = args.run.read_text(encoding="utf-8").splitlines()[: args.n]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ok2, msg2 = verify(args.out)
    if not ok2:
        print(f"exported sample does not verify ({msg2}) -- the chain is not prefix-verifiable",
              file=sys.stderr)
        return 1


    print(f"wrote {args.out} ({len(lines)} entries)")
    print(f"  sample verifies: {msg2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
