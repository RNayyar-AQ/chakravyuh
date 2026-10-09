#!/usr/bin/env python3
"""Verify a run ledger's hash chain. Y.3172 node: SINK.

Exit 0 when the chain is intact, 1 when it is not. Editing, reordering, inserting or deleting any
line is detectable (spec §7).

  python scripts/verify_ledger.py runs/amphan_2020__india_current__rule__seed0.jsonl
  python scripts/verify_ledger.py --all
  python scripts/verify_ledger.py --tamper-demo runs/amphan_2020__india_current__rule__seed0.jsonl

`--tamper-demo` is the one that is worth watching: it copies a verified ledger, alters a single
character deep inside it, and re-verifies the copy. A chain that cannot be edited without
detection is the whole claim the audit trail makes, and the only convincing way to show it is to
break one on camera. The original is never touched.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.audit.ledger import verify

TAMPER_DIR = Path("outputs/tamper")


def tamper_demo(path: Path, out_dir: Path = TAMPER_DIR) -> int:
    """Copy a ledger, flip one character in one entry, re-verify. Returns 0 when detected.

    The edit is deliberately the smallest and most plausible one an attacker would want: the
    forged-order verdict is changed from BLOCK to ALLOW, or failing that a single digit in the
    middle entry is changed. Nothing is appended and nothing is reordered, so only the hash
    chain can notice.
    """
    ok, msg = verify(path)
    print(f"1. verify the original          : {'OK' if ok else 'FAIL'} {msg}")
    if not ok:
        print("   original does not verify; nothing to demonstrate", file=sys.stderr)
        return 2

    lines = path.read_text(encoding="utf-8").splitlines()
    target = None
    for i, line in enumerate(lines):
        if '"kind": "VERDICT"' in line and '"BLOCK"' in line:
            target, edited = i, line.replace('"BLOCK"', '"ALLOW"', 1)
            what = "changed one VERDICT from BLOCK to ALLOW"
            break
    if target is None:                       # no BLOCK in this run: edit any digit instead
        target = len(lines) // 2
        edited = lines[target].replace('0', '1', 1)
        what = "changed a single digit in one entry"

    out_dir.mkdir(parents=True, exist_ok=True)
    copy = out_dir / f"{path.stem}.tampered.jsonl"
    lines[target] = edited
    copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"2. {what}")
    print(f"   wrote the altered copy to    : {copy}")

    ok2, msg2 = verify(copy)
    print(f"3. verify the altered copy      : {'OK' if ok2 else 'FAIL'} {msg2}")
    if ok2:
        print("   TAMPERING WENT UNDETECTED -- the chain is not doing its job", file=sys.stderr)
        return 1
    print("\n   detected. The original is untouched and still verifies:")
    ok3, msg3 = verify(path)
    print(f"   {'OK' if ok3 else 'FAIL'} {path}: {msg3}")
    return 0 if ok3 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", help="ledger JSONL files")
    ap.add_argument("--all", action="store_true", help="verify every ledger under runs/")
    ap.add_argument("--tamper-demo", action="store_true",
                    help="copy one ledger, alter a character, show the chain catches it")
    args = ap.parse_args()

    if args.tamper_demo:
        paths = [Path(p) for p in args.paths] or sorted(Path("runs").glob("*.jsonl"))
        if not paths:
            print("no ledger to tamper with", file=sys.stderr)
            return 2
        return tamper_demo(paths[0])

    paths = [Path(p) for p in args.paths]
    if args.all:
        paths = sorted(Path("runs").rglob("*.jsonl"))
    if not paths:
        print("no ledger given; pass a path or --all", file=sys.stderr)
        return 2

    failed = 0
    for path in paths:
        ok, msg = verify(path)
        print(f"{'OK  ' if ok else 'FAIL'} {path}: {msg}")
        if not ok:
            failed += 1
    print(f"\n{len(paths) - failed}/{len(paths)} ledger(s) verified")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
