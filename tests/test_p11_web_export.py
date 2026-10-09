"""The web UI must render the pipeline's numbers, never its own. Y.3172 node: SINK."""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"
DATA = WEB / "public" / "data"
BUNDLE = DATA / "bundle.json"
EXPORTER = ROOT / "app" / "scripts" / "export_web.py"


@pytest.fixture(scope="module")
def bundle() -> dict:
    if not BUNDLE.exists():
        pytest.skip("no bundle; run app/scripts/showcase.py then app/scripts/export_web.py")
    return json.loads(BUNDLE.read_text())


def test_exporter_exists_and_is_wired_into_the_showcase():
    assert EXPORTER.exists()
    showcase = (ROOT / "app" / "scripts" / "showcase.py").read_text(encoding="utf-8")
    assert "app/scripts/export_web.py" in showcase, "export stage missing from the showcase run"


def test_scorecard_margins_match_the_comparison_artefact(bundle):
    """Every margin shown on the site must be the one run_demo wrote, to the digit."""
    comparison = json.loads((ROOT / "outputs" / "comparison.json").read_text())
    source = {d["property_id"]: d for d in comparison["divergences"]}
    assert source, "comparison.json has no divergences to check against"

    for prop in bundle["scorecard"]["properties"]:
        pid = prop["property_id"]
        assert pid in source, f"{pid} is on the site but not in comparison.json"
        assert prop["margins"] == source[pid]["margins"]
        assert sorted(prop["passes_under"]) == sorted(source[pid]["passes_under"])
        assert sorted(prop["fails_under"]) == sorted(source[pid]["fails_under"])


def test_gap_rows_are_the_csv_verbatim(bundle):
    with (ROOT / "outputs" / "gap_register.csv").open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert bundle["gaps"] == rows, "the site's gap table diverged from the register"


def test_no_finding_is_promoted_past_what_the_register_says(bundle):
    """Confidence is computed upstream. The export must not launder `likely` into `certain`."""
    for row in bundle["gaps"]:
        assert row["confidence"] in {"certain", "likely", "unverified"}
    with (ROOT / "outputs" / "gap_register.csv").open(newline="") as fh:
        csv_conf = [r["confidence"] for r in csv.DictReader(fh)]
    assert [r["confidence"] for r in bundle["gaps"]] == csv_conf


def test_ledger_verification_status_is_copied_not_assumed(bundle):
    """A tampered ledger must never be reported as intact, which is the whole demo."""
    assert bundle["ledger"]["runs"], "no run ledgers exported"
    assert all(r["verified"] for r in bundle["ledger"]["runs"])
    assert bundle["ledger"]["tamper"], "the tamper demonstration did not run"
    for t in bundle["ledger"]["tamper"]:
        assert t["verified"] is False
        assert "seq" in t["message"], "a tamper report must name where the chain broke"


def test_y3172_counts_are_non_empty(bundle):
    """The registry only fills on import; a zeroed map means the exporter skipped the walk."""
    nodes = {n["node"]: n["count"] for n in bundle["y3172"]}
    assert sum(nodes.values()) > 0
    for required in ("SRC", "M", "D", "SINK"):
        assert nodes.get(required, 0) > 0, f"node {required} registered nothing"


def test_bundle_is_json_serialisable_and_sorted():
    """Stable key order keeps a rebuild from showing as a diff when nothing changed."""
    raw = BUNDLE.read_text() if BUNDLE.exists() else pytest.skip("no bundle")
    assert raw == json.dumps(json.loads(raw), indent=1, sort_keys=True)


def _web_sources() -> list[Path]:
    if not (WEB / "app").exists():
        return []
    return [p for p in WEB.rglob("*.ts*")
            if "node_modules" not in p.parts and ".next" not in p.parts and "out" not in p.parts]


def test_the_ui_fetches_nothing_from_the_network():
    """The demo has to survive conference Wi-Fi, so every byte must come from /data."""
    offenders = []
    for path in _web_sources():
        for m in re.finditer(r"fetch\(\s*[`'\"]([^`'\"]*)", path.read_text(encoding="utf-8")):
            target = m.group(1)
            if target.startswith(("http://", "https://")):
                offenders.append(f"{path.relative_to(ROOT)}: {target}")
    assert not offenders, f"the UI reaches the network: {offenders}"


def test_the_ui_declares_every_bundle_key(bundle):
    """lib/types.ts is the contract. A key exported but undeclared will render as undefined."""
    types = (WEB / "lib" / "types.ts")
    if not types.exists():
        pytest.skip("web UI not present")
    text = types.read_text(encoding="utf-8")
    missing = [k for k in bundle if k not in text]
    assert not missing, f"bundle keys absent from lib/types.ts: {missing}"


def _tracked(*paths: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", *paths], cwd=ROOT,
                         capture_output=True, text=True, check=False)
    return [line for line in out.stdout.splitlines() if line]


def test_the_data_bundle_is_committed_so_vercel_can_build_it():
    """The one deliberate exception to "sources, not derivatives": Vercel builds from git."""
    tracked = _tracked("app/web/public/data")
    assert any(p.endswith("bundle.json") for p in tracked), (
        "app/web/public/data/bundle.json is not tracked; a Vercel build would have nothing "
        "to render. Run `make artefacts` and commit it.")
    assert any("timeline." in p for p in tracked), "no timelines tracked"


def test_no_other_build_product_is_committed():
    """The exception stops at the data bundle. Everything else stays out."""
    offenders = _tracked("app/web/out", "app/web/node_modules", "app/web/.next",
                         "outputs", "runs", "data/clauses", "data/chroma")
    assert not offenders, "build products are tracked:\n" + "\n".join(offenders)


def test_the_committed_bundle_matches_a_fresh_export():
    """A stale bundle would be a second source of truth. Regenerate and compare, byte for byte."""
    if not BUNDLE.exists():
        pytest.skip("no bundle")
    before = {p: p.read_bytes() for p in sorted(DATA.glob("*.json"))}
    proc = subprocess.run([sys.executable, str(EXPORTER)], cwd=ROOT,
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    drifted = [p.name for p, data in before.items() if p.read_bytes() != data]
    assert not drifted, (
        f"the committed bundle is stale: {drifted}. Run `make artefacts` and commit the result.")


def test_exporter_reruns_cleanly(tmp_path):
    """The export must be reproducible: running it twice changes nothing."""
    if not BUNDLE.exists():
        pytest.skip("no bundle to compare against")
    before = BUNDLE.read_bytes()
    proc = subprocess.run([sys.executable, str(EXPORTER)], cwd=ROOT,
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    after = BUNDLE.read_bytes()
    assert before == after, "the export is not byte-for-byte reproducible"

    for path in sorted(DATA.glob("timeline.*.json")):
        assert path.stat().st_size > 0
