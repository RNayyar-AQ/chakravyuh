"""P1 gate (spec §10): every clause has a URL and a matching hash; exact lookup only."""
from __future__ import annotations

import pytest

from chakravyuh.kb.clause_store import ClauseNotFound, ClauseStore, HashMismatch
from chakravyuh.kb.retrieve import Retriever
from chakravyuh.schemas import Clause, sha256_text


def test_every_clause_has_url_and_hash(built_kb):
    store = ClauseStore()
    clauses = store.all_clauses()
    assert len(clauses) >= 40, "spec asks for ~40 hand-picked clauses"
    for c in clauses:
        assert c.source_url.startswith("http"), c.clause_id
        assert c.hash_matches(), c.clause_id
        assert c.text_verbatim.strip()
    store.close()


def test_get_clause_is_exact(built_kb):
    store = ClauseStore()
    assert store.get_clause("IN.SUSP2024.r2.4").section == "r.2(4)"
    with pytest.raises(ClauseNotFound):
        store.get_clause("IN.SUSP2024.r2")
    with pytest.raises(ClauseNotFound):
        store.get_clause("totally.made.up")
    store.close()


def test_upsert_rejects_hash_mismatch(tmp_path):
    store = ClauseStore(tmp_path / "c.sqlite")
    bad = Clause(clause_id="X.1", instrument="I", jurisdiction="IN", section="s.1",
                 text_verbatim="real text", source_url="https://example.org",
                 sha256=sha256_text("different text"), retrieved_at="2026-10-07")
    with pytest.raises(HashMismatch):
        store.upsert(bad)
    store.close()


def test_jurisdictions_cover_in_bd_us_intl(built_kb):
    store = ClauseStore()
    for j in ("IN", "BD", "US", "INTL"):
        assert store.by_jurisdiction(j), f"no clauses for {j}"
    store.close()


def test_integrity_report_counts_unverified_honestly(built_kb):
    """The corpus is now MIXED: real gazette text plus model-written summaries. Report both."""
    store = ClauseStore()
    rep = store.integrity_report()
    assert rep["pct_hash_matching"] == 100.0
    assert rep["pct_with_source_url"] == 100.0

    prov = rep["per_provenance"]
    assert prov.get("gazette_pdf", 0) > 0, "the real gazette corpus must be ingested"
    assert prov.get("model_written", 0) > 0, "model-written records still exist; do not hide them"
    assert sum(prov.values()) == rep["total"], "every record lands in exactly one bucket"

    assert 0 < rep["pct_verbatim_verified"] < 100.0
    assert rep["quotable"] <= rep["verbatim_verified"]
    assert rep["with_source_pdf_hash"] == rep["verbatim_verified"], \
        "every record with real text must name the PDF hash it came from"
    store.close()
    store.close()


def test_retrieval_returns_results(built_kb):
    r = Retriever(mode="bm25")
    hits = r.search("Who can order temporary suspension of telecom services?", k=5)
    assert hits
    assert "IN.SUSP2024.r2.1" in {h.clause_id for h in hits}


def test_only_gazette_derived_records_claim_verification(built_kb):
    """A record may claim real text ONLY if it came from a source PDF whose hash it carries."""
    store = ClauseStore()
    offenders = [(c.clause_id, c.provenance, bool(c.source_pdf_sha256))
                 for c in store.all_clauses()
                 if c.is_real_text and not (c.provenance.startswith("gazette_pdf")
                                            and c.source_pdf_sha256)]
    summaries_claiming_real = [c.clause_id for c in store.all_clauses()
                               if c.provenance in ("model_written", "secondary_source")
                               and c.is_real_text]
    store.close()
    assert offenders == [], f"claim real text without a source PDF hash: {offenders}"
    assert summaries_claiming_real == [], \
        f"model-written/secondary records claiming real text: {summaries_claiming_real}"


def test_real_records_preserve_the_raw_extraction(built_kb):
    """Cleaning must stay auditable: raw text and its hash survive alongside the cleaned text."""
    store = ClauseStore()
    real = [c for c in store.all_clauses() if c.provenance == "gazette_pdf"]
    assert real
    for c in real:
        assert c.text_raw, c.clause_id
        assert c.sha256_raw, c.clause_id
        assert c.page and c.page > 0, c.clause_id
        assert c.hash_matches(), c.clause_id
    store.close()


def test_pagebreak_artifacts_are_flagged_not_silently_quoted(built_kb):
    """A record with an interpolated marginal heading must not be marked quotable."""
    store = ClauseStore()
    for c in store.all_clauses():
        if c.pagebreak_artifact:
            assert not c.quotable, f"{c.clause_id} has a page-break artifact but claims quotable"
            assert c.verbatim_status == "verified_with_artifacts"
    store.close()


def test_provenance_doc_describes_the_mixed_corpus(built_kb):
    """The disclosure must name BOTH halves and keep the model-written half visible."""
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1]
           / "data/sources/CLAUSES_PROVENANCE.md").read_text(encoding="utf-8").lower()
    for phrase in ("mixed", "gazette_pdf", "model_written", "source_pdf_sha256",
                   "negative finding", "not legal advice"):
        assert phrase in doc, f"provenance doc no longer states: {phrase!r}"


def test_provenance_doc_records_what_the_real_data_corrected(built_kb):
    """The s.24 error must stay documented: it is the evidence that verification matters."""
    from pathlib import Path
    doc = (Path(__file__).resolve().parents[1]
           / "data/sources/CLAUSES_PROVENANCE.md").read_text(encoding="utf-8")
    assert "Digital Bharat Nidhi" in doc
    assert "IN.TA2023.s24" in doc


def test_no_pack_rule_cites_the_uso_fund_section_for_priority_routing(built_kb, packs):
    """Regression: s.24 is the USO fund. Only s.20(1) carries priority routing."""
    for pack in packs.values():
        for rule in pack.rules:
            if rule.action_type == "PRIORITISE_RELIEF_SLICE":
                assert "IN.TA2023.s24" not in rule.clause_ids, rule.rule_id


def test_kb_report_carries_the_provenance_warning(built_kb):
    """A reader who only ever opens kb_report.md must still learn where the clauses came from."""
    from pathlib import Path
    report = Path(__file__).resolve().parents[1] / "docs/kb_report.md"
    if not report.exists():
        import pytest
        pytest.skip("run app/scripts/build_kb.py first")
    body = report.read_text(encoding="utf-8")
    assert "PROVENANCE" in body
