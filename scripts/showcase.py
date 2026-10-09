#!/usr/bin/env python3
"""Run the whole rubric showcase, in dependency order. Y.3172 node: SINK.

One command, to every artefact the rubric asks for:

    python scripts/showcase.py                 # the full sequence (fuzzing is the slow part)
    python scripts/showcase.py --fast           # skip the fuzz campaign (~3 min saved)
    python scripts/showcase.py --audit-only     # just re-run the rubric audit
    python scripts/showcase.py --strict         # a waived rubric check fails the run

Generators write straight to their final home: documents a judge reads go to `docs/`,
machine-readable data goes to `outputs/`. There is no intermediate build directory and no copy
step, so what you read is what was generated.

Stage order is the dependency order, not the rubric's phase order: the clause store has to exist
before a pack can compile, a pack has to compile before a run, and a run has to exist before the
gap register, the audit sample or the stats can be written. Each stage prints its own command, so
anything that fails can be re-run on its own without re-running the rest.

"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

# (stage, description, command). `slow` stages are skipped by --fast.
Stage = tuple[str, str, list[str], bool]

STAGES: list[Stage] = [
    ("sources", "verify every held primary source against its hash and required strings",
     [PY, "scripts/fetch_sources.py", "--verify"], False),
    ("kb", "build the clause store, chunk it, push to Chroma, compile every pack",
     [PY, "scripts/build_kb.py"], False),
    ("retrieval", "score BM25 / vector / hybrid / hybrid+rerank / tree, incl. abstention",
     [PY, "scripts/eval_retrieval.py"], False),
    ("adviser", "score the Adviser against the hand-labelled cases",
     [PY, "scripts/eval_adviser.py"], False),
    ("demo", "replay the Amphan timeline under every pack; write the gap register",
     [PY, "scripts/run_demo.py", "--seed", "0"], False),
    ("fuzz", "mutate the scenario until a property breaks, then shrink the failure",
     [PY, "scripts/run_fuzz.py"], True),
    ("audit_sample", "export the first 50 ledger entries as a self-verifying sample",
     [PY, "scripts/export_audit_sample.py"], False),
    ("y3172", "generate the Y.3172 node map from the @node decorators",
     [PY, "scripts/gen_y3172_map.py"], False),
    ("ai_readiness", "generate the AI Readiness map from ITU's dimensions.json",
     [PY, "scripts/gen_ai_readiness_map.py"], False),
    ("run_stats", "read back wall time, LLM calls and tokens per run",
     [PY, "scripts/gen_run_stats.py"], False),
    ("urls", "check every clause source URL still resolves",
     [PY, "scripts/check_sources.py"], True),
    ("ledgers", "verify every run ledger's hash chain",
     [PY, "scripts/verify_ledger.py", "--all"], False),
    ("tamper", "prove an edited ledger is detected",
     [PY, "scripts/verify_ledger.py", "--tamper-demo"], False),
    # Last, because it reads every artefact above. The web UI renders this bundle and nothing
    # else, so if a stage above did not run, the UI says so instead of showing a stale number.
    ("web", "export every artefact as the web UI's data bundle",
     [PY, "scripts/export_web.py"], False),
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
                # The stages are a dependency chain: continuing past a broken clause store or a
                # broken run would produce artefacts built on nothing.
                if name in ("kb", "demo"):
                    print("this stage is a dependency of everything after it; stopping",
                          file=sys.stderr)
                    break

    audit_cmd = [PY, "scripts/rubric_audit.py"] + (["--strict"] if args.strict else [])
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
