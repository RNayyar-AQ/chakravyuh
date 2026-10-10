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


def _key_diff(before: bytes, after: bytes) -> list[str]:
    """Which top-level sections changed -- so a drift says what moved, not just that it did."""
    try:
        a, b = json.loads(before), json.loads(after)
    except json.JSONDecodeError:
        return ["<unparseable>"]
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def test_the_committed_bundle_matches_a_fresh_export():
    """A stale bundle would be a second source of truth. Regenerate and compare, byte for byte."""
    if not BUNDLE.exists():
        pytest.skip("no bundle")
    before = {p: p.read_bytes() for p in sorted(DATA.glob("*.json"))}
    proc = subprocess.run([sys.executable, str(EXPORTER)], cwd=ROOT,
                          capture_output=True, text=True, check=False)
    # A non-zero exit here means the pipeline did not finish: the exporter names the artefact
    # that is missing and the command that writes it, which is a far more useful failure than
    # the empty sections it used to emit and the "stale bundle" they looked like.
    assert proc.returncode == 0, proc.stderr
    drifted = {p.name: p.read_bytes() for p, data in before.items() if p.read_bytes() != data}
    detail = "; ".join(
        f"{name} (sections: {', '.join(_key_diff(before[DATA / name], data)) or 'n/a'})"
        for name, data in drifted.items())
    assert not drifted, (
        f"the committed bundle is stale: {detail}. Run `make artefacts` and commit the result.")


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


# --------------------------------------------------------------------------------------------
# The single page claims to show its own working. These pin that the working is real.


def test_every_margin_recomputes_to_the_one_the_run_recorded(bundle):
    """The page shows arithmetic. If the arithmetic disagreed with the ledger it would be theatre."""
    rows = bundle["derivations"]
    assert rows, "no derivations exported"
    disagreed = [f"{d['pack_id']}/{d['property_id']}" for d in rows if not d["agrees"]]
    assert not disagreed, f"recomputed margin differs from the recorded one: {disagreed}"


def test_the_arithmetic_string_is_the_arithmetic(bundle):
    """`360 - 7500 = -7140` must actually hold, or the page is showing a decorative subtraction."""
    for d in bundle["derivations"]:
        if not d["applicable"]:
            continue
        left, right = d["arithmetic"].split("=")
        a, b = (float(x) for x in left.split("-"))
        assert a - b == pytest.approx(float(right)), f"{d['property_id']}: {d['arithmetic']}"
        assert float(right) == pytest.approx(d["margin"])
        # P1 subtracts the threshold from what was observed; the timing properties do the reverse.
        expected = (d["observed"], d["threshold"]) if d["property_id"] == "P1" \
            else (d["threshold"], d["observed"])
        assert (a, b) == pytest.approx(expected)


def test_every_property_is_derived_for_every_pack(bundle):
    """A pack missing a property would quietly drop a failure from the comparison."""
    packs = {p["pack_id"] for p in bundle["packs"]}
    for pack in packs:
        got = {d["property_id"] for d in bundle["derivations"] if d["pack_id"] == pack}
        assert got == set(bundle["properties"]), f"{pack} is missing {set(bundle['properties']) - got}"


def test_the_traces_are_entries_in_a_real_ledger(bundle):
    """Each step the page walks must be a sequence number in the chain, in order."""
    path = ROOT / "runs" / "amphan_2020__india_current__rule__seed0.jsonl"
    if not path.exists():
        pytest.skip("no India run to check against")
    seqs = {json.loads(line)["seq"]: json.loads(line)["kind"]
            for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    assert bundle["traces"], "no traces exported"
    for trace in bundle["traces"]:
        assert trace["event"], f"{trace['event_id']} has no event entry"
        assert seqs.get(trace["event"]["seq"]) == "EVENT"
        for d in trace["deliveries"]:
            assert seqs.get(d["seq"]) == "DELIVERY"
            assert d["arrives_t"] >= d["released_t"]
        for p in trace["proposals"]:
            assert seqs.get(p["seq"]) == "PROPOSAL"
            assert p["seq"] > trace["event"]["seq"], "a proposal cannot precede its trigger"
            if p["verdict"]:
                assert seqs.get(p["verdict"]["seq"]) == "VERDICT"
                assert p["verdict"]["seq"] > p["seq"], "a verdict cannot precede its proposal"


def test_the_forged_order_is_still_marked_forged(bundle):
    """The adversarial trace is the demo's sharpest claim; it must not soften in export."""
    forged = [t for t in bundle["traces"] if t["event"] and t["event"]["authentic"] is False]
    assert forged, "no inauthentic event is traced on the page"
    for t in forged:
        assert t["hidden_from_agents"], "ground truth must be recorded as hidden, not absent"
        delivered = json.dumps([d["visible_payload"] for d in t["deliveries"]])
        assert "forged" not in delivered, "the forged flag leaked into what an agent can see"
        assert any(m["property_id"] == "P2" for m in t["moves"]), "P2 does not see the forgery"


def test_every_clause_the_page_can_open_is_a_real_record(bundle):
    """A citation the reader can expand must come from the store, with its provenance attached."""
    cited = set()
    for t in bundle["traces"]:
        for p in t["proposals"]:
            cited.update(p["cited_clause_ids"])
    assert cited, "no clause is cited anywhere in the traces"
    missing = sorted(c for c in cited if c not in bundle["clauses"])
    assert not missing, f"the page cites clauses it cannot show: {missing}"
    for record in bundle["clauses"].values():
        assert record["text"], f"{record['clause_id']} has no text"
        assert record["provenance"], f"{record['clause_id']} has no provenance"


def test_the_rrf_worked_example_adds_up(bundle):
    """The page writes out 1/(k+rank) per retriever. Recompute it here."""
    ex = bundle["retrieval_example"]
    if not ex:
        pytest.skip("no retrieval evaluation to build an example from")
    assert ex["question"], "the worked example has no question text"
    for row in ex["fused"]:
        total = sum(1.0 / (ex["k"] + part["rank"]) for part in row["parts"])
        assert row["score"] == pytest.approx(total, abs=1e-6), row["clause_id"]
        for part in row["parts"]:
            assert part["contribution"] == pytest.approx(1.0 / (ex["k"] + part["rank"]), abs=1e-6)
    scores = [r["score"] for r in ex["fused"]]
    assert scores == sorted(scores, reverse=True), "fused rows are not in rank order"


def test_the_flow_reports_the_run_it_was_built_from(bundle):
    """A stage's headline number must be the one in the ledger, not a round figure."""
    stages = {s["title"]: s for s in bundle["flow"]}
    assert stages, "no flow stages exported"
    india = next(r for r in bundle["ledger"]["runs"] if "india_current" in r["run_id"])
    assert str(india["kinds"]["PROPOSAL"]) in stages["Agents propose"]["measure"]
    assert str(india["kinds"]["VERDICT"]) in stages["The engine decides"]["measure"]
    assert str(bundle["kb_graph"]["clauses"]) in stages["Ingest"]["measure"]
    for stage in bundle["flow"]:
        assert stage["command"], f"{stage['title']} does not say how to reproduce it"
        assert stage["node"] in {n["node"] for n in bundle["y3172"]}


def test_the_rubric_shown_is_the_audit_that_ran(bundle):
    """The rubric page must be the audit's own output, not a transcription of it."""
    source = ROOT / "outputs" / "rubric_status.json"
    if not source.exists():
        pytest.skip("rubric audit has not been run")
    recorded = json.loads(source.read_text(encoding="utf-8"))
    assert bundle["rubric"] == recorded
    totals = bundle["rubric"]["totals"]
    assert totals["checks"] == len(bundle["rubric"]["checks"])
    counted = {s: sum(1 for c in bundle["rubric"]["checks"] if c["status"] == s)
               for s in ("PASS", "WAIVED", "FAIL")}
    assert (counted["PASS"], counted["WAIVED"], counted["FAIL"]) == \
        (totals["pass"], totals["waived"], totals["fail"])
    for check in bundle["rubric"]["checks"]:
        if check["status"] == "WAIVED":
            assert check["waiver"], f"{check['id']} is waived without a reason"


def test_the_kb_graph_agrees_with_the_clause_store_summary(bundle):
    """Two views of the same corpus; if they drifted, one of them would be decoration."""
    g = bundle["kb_graph"]
    assert g["clauses"] == bundle["kb"]["total"]
    assert sum(r["clauses"] for r in g["instruments"]) == g["clauses"]
    real = bundle["kb"]["total"] - bundle["kb"]["verbatim_status"].get("unverified_summary", 0)
    assert g["real_text"] == real
    assert g["quotable"] <= g["real_text"]
    assert g["chunks"] >= g["clauses"], "fewer chunks than clauses means a clause was dropped"


# --------------------------------------------------------------------------------------------
# The bundle is only committable after a full run. These pin the two halves of that: the export
# refuses to write a partial one, and CI runs the pipeline that makes it whole.


def _exporter_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("export_web_probe", EXPORTER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_exporter_refuses_to_write_a_partial_bundle(tmp_path, monkeypatch):
    """A missing stage used to produce an empty section, which then read as a stale bundle."""
    mod = _exporter_module()
    required = dict(mod.REQUIRED)
    for rel in ("outputs/retrieval_eval.json", "outputs/adviser_eval.json",
                "outputs/fuzz_summary.json", "outputs/rubric_status.json"):
        assert rel in required, f"{rel} feeds a section of the bundle but is not required"
        assert required[rel].startswith("python app/scripts/"), \
            f"{rel} does not say which command writes it"

    assert mod.missing_artefacts() == [], \
        "this checkout is missing an artefact the bundle needs; run `make artefacts`"

    # main() pins the working directory to its own ROOT, which is patched below. monkeypatch
    # restores the attribute but never the process cwd, so without this the rest of the session
    # runs from tmp_path and every path-relative fixture -- the clause store first -- reads empty.
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["export_web.py"])
    assert [rel for rel, _ in mod.missing_artefacts()] == [rel for rel, _ in mod.REQUIRED]
    assert mod.main() == 1, "the exporter wrote a bundle with every artefact missing"

    monkeypatch.setattr(sys, "argv", ["export_web.py", "--allow-incomplete"])
    assert mod.missing_artefacts(), "--allow-incomplete must still report what is absent"


def test_ci_runs_the_pipeline_that_the_bundle_is_checked_against():
    """Checking the bundle against a half-run pipeline is a test of the pipeline, not the bundle."""
    ci = ROOT / ".github" / "workflows" / "ci.yml"
    if not ci.exists():
        pytest.skip("no CI workflow")
    text = ci.read_text(encoding="utf-8")
    assert "app/scripts/showcase.py" in text, "CI does not run the pipeline end to end"
    assert "--fast" not in text, "CI skips stages, so its export cannot match the committed bundle"
    assert text.index("showcase.py") < text.index("pytest"), "the pipeline must precede the tests"


def test_the_showcase_audits_before_it_exports():
    """outputs/rubric_status.json is a bundle input, so the audit cannot run after the export."""
    text = (ROOT / "app" / "scripts" / "showcase.py").read_text(encoding="utf-8")
    assert text.index("rubric_audit.py") < text.index("export_web.py"), \
        "the rubric audit runs after the export, so the bundle would ship the previous audit"


def test_the_export_does_not_depend_on_where_it_is_run_from(tmp_path):
    """The clause store is declared relative to the root; a stray cwd used to empty the bundle."""
    if not BUNDLE.exists():
        pytest.skip("no bundle")
    before = BUNDLE.read_bytes()
    proc = subprocess.run([sys.executable, str(EXPORTER)], cwd=tmp_path,
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert BUNDLE.read_bytes() == before, (
        "running the exporter from another directory produced a different bundle")


def test_the_bundle_holds_no_number_a_rerun_would_change(bundle):
    """A randomised search's sample count and wall clock differ every run; they cannot be here.

    This is the defect that made the committed bundle look permanently stale: the fuzz campaign
    reported `runs_completed` and `wall_seconds`, both of which move between two runs of the same
    command on the same machine. The measurements stay in outputs/fuzz_summary.json, where a
    measurement belongs. What the bundle carries is the declared budget and the counterexamples.
    """
    volatile = {"runs_completed", "wall_seconds"}
    for run in bundle["fuzz"]["runs"]:
        present = volatile & set(run)
        assert not present, f"{run['pack_id']} exports {sorted(present)}, which a rerun changes"
        assert "examples_budgeted" in run, "the reproducible budget is missing"
        # A campaign excluded at baseline searched nothing, and must not claim a budget.
        expected = run["max_examples"] if run["asserted_properties"] else 0
        assert run["examples_budgeted"] == expected

    summary = ROOT / "outputs" / "fuzz_summary.json"
    if summary.exists():
        rows = json.loads(summary.read_text(encoding="utf-8"))
        assert any("wall_seconds" in r for r in rows), (
            "the measurement was deleted rather than moved; it belongs in the artefact")
