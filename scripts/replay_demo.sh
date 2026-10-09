#!/usr/bin/env bash
# Replay the demo with the network off. This is the script to run on stage.
#
# Everything here is deterministic and offline by construction: the agent twins need no model,
# the policy engine is a pure function, the clause store is local SQLite, and the LLM client is
# pinned to replay mode so it cannot reach out even if something asks it to. Venue Wi-Fi and
# borrowed laptops fail; a replay does not.
#
#   bash scripts/replay_demo.sh            # full replay + verification
#   bash scripts/replay_demo.sh --quick    # skip the test suite
set -euo pipefail
cd "$(dirname "$0")/.."

export CHAKRAVYUH_LLM_MODE=replay       # a cache miss raises rather than calling a provider
PY="${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}"
QUICK=""; [ "${1:-}" = "--quick" ] && QUICK=1

step () { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

step "1/5  knowledge base — 157 clauses, chunks, vector index, pack compilation"
$PY scripts/build_kb.py

step "2/5  replay Cyclone Amphan under every policy pack"
$PY scripts/run_demo.py --seed 0

step "3/5  verify every ledger's hash chain"
$PY scripts/verify_ledger.py --all

step "4/5  prove the chain catches an edit"
$PY scripts/verify_ledger.py --tamper-demo runs/amphan_2020__india_current__rule__seed0.jsonl

step "5/5  rubric scorecard"
$PY scripts/rubric_audit.py

if [ -z "$QUICK" ]; then
  step "tests"
  $PY -m pytest -q -m "not slow"
fi

cat <<'DONE'

Replay complete. Nothing above touched the network.

  Scorecard   docs/rubric_status.html      (open in a browser)
  Findings    docs/gap_register.md
  Report      docs/demo_report.md
  Limits      docs/limits.md

  UI          streamlit run app/streamlit_app.py
DONE
