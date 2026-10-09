#!/usr/bin/env python3
"""Run the whole rubric showcase, in dependency order. Y.3172 node: SINK."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

Stage = tuple[str, str, list[str], bool]

STAGES: list[Stage] = [
    ("sources", "verify every held primary source against its hash and required strings",
     [PY, "app/scripts/fetch_sources.py", "--verify"], False),
    ("kb", "build the clause store, chunk it, push to Chroma, compile every pack",
     [PY, "app/scripts/build_kb.py"], False),
    ("retrieval", "score BM25 / vector / hybrid / hybrid+rerank / tree, incl. abstention",
     [PY, "app/scripts/eval_retrieval.py"], False),
    ("adviser", "score the Adviser against the hand-labelled cases",
     [PY, "app/scripts/eval_adviser.py"], False),
    ("demo", "replay the Amphan timeline under every pack; write the gap register",
     [PY, "app/scripts/run_demo.py", "--seed", "0"], False),
    ("fuzz", "mutate the scenario until a property breaks, then shrink the failure",
     [PY, "app/scripts/run_fuzz.py"], True),
    ("audit_sample", "export the first 50 ledger entries as a self-verifying sample",
     [PY, "app/scripts/export_audit_sample.py"], False),
    ("y3172", "generate the Y.3172 node map from the @node decorators",
     [PY, "app/scripts/gen_y3172_map.py"], False),
    ("ai_readiness", "generate the AI Readiness map from ITU's dimensions.json",
     [PY, "app/scripts/gen_ai_readiness_map.py"], False),
    ("run_stats", "read back wall time, LLM calls and tokens per run",
     [PY, "app/scripts/gen_run_stats.py"], False),
    ("urls", "check every clause source URL still resolves",
     [PY, "app/scripts/check_sources.py"], True),
    ("ledgers", "verify every run ledger's hash chain",
     [PY, "app/scripts/verify_ledger.py", "--all"], False),
    ("tamper", "prove an edited ledger is detected",
     [PY, "app/scripts/verify_ledger.py", "--tamper-demo"], False),
    ("web", "export every artefact as the web UI's data bundle",
     [PY, "app/scripts/export_web.py"], False),
]


def run(cmd: list[str], label: str) -> tuple[int, float]:
    started = time.perf_counter()
    print(f"\n\033[1m=== {label} ===\033[0m\n    $ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode, time.perf_counter() - started


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true", help="skip the slow stages (fuzz, URL check)")
    ap.add_argument("--audit-only", action="store_true", help="only re-run the rubric audit")
    ap.add_argument("--strict", action="store_true", help="a waived rubric check fails the run")
    ap.add_argument("--only", nargs="*", help="run only these stage names")
    args = ap.parse_args()

    failures: list[tuple[str, int]] = []
    timings: list[tuple[str, float]] = []

    if not args.audit_only:
        for name, desc, cmd, slow in STAGES:
            if args.only and name not in args.only:
                continue
            if args.fast and slow:
                print(f"\n=== {name} === skipped (--fast): {desc}")
                continue
            code, secs = run(cmd, f"{name}  —  {desc}")
            timings.append((name, secs))
            if code != 0:
                failures.append((name, code))
                print(f"\n\033[31mstage {name} exited {code}\033[0m", file=sys.stderr)
                if name in ("kb", "demo"):
                    print("this stage is a dependency of everything after it; stopping",
                          file=sys.stderr)
                    break

    audit_cmd = [PY, "app/scripts/rubric_audit.py"] + (["--strict"] if args.strict else [])
    code, secs = run(audit_cmd, "rubric_audit  —  check A1..G4 and write docs/rubric_status.html")
    timings.append(("rubric_audit", secs))
    if code != 0:
        failures.append(("rubric_audit", code))

    print("\n\033[1m=== timings ===\033[0m")
    for name, secs in timings:
        print(f"    {name:<14} {secs:7.2f}s")
    print(f"    {'total':<14} {sum(s for _, s in timings):7.2f}s")

    if failures:
        print(f"\n\033[31m{len(failures)} stage(s) failed: "
              f"{', '.join(n for n, _ in failures)}\033[0m", file=sys.stderr)
        return 1
    html = (ROOT / "docs/rubric_status.html").resolve()
    print("\n\033[32mall stages succeeded.\033[0m The scorecard is at")
    print(f"    file://{html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
