"""Ingest REAL clause text split from official gazette PDFs. Y.3172 node: C."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Optional

from ..schemas import Clause, sha256_text
from ..y3172 import node

DATA_DIR = Path("data/sources/IN")

REAL_SOURCES: tuple[dict, ...] = (
    {"path": DATA_DIR / "telecom_act_2023.jsonl", "instrument_id": "IN.TA2023",
     "expected_sections": 62},
    {"path": DATA_DIR / "dpdp_act_2023.jsonl", "instrument_id": "IN.DPDP2023",
     "expected_sections": 44},
)

STRUCTURAL = (
    re.compile(r"\[PART\s+[IVXL]+\s*[—–-]*\s*(?:SEC\.\s*\d+\])?"),
    re.compile(r"\bSEC\.\s*\d+\]"),
    re.compile(r"\bTHE GAZETTE OF INDIA\s+EXTRAORDINARY\b", re.I),
    re.compile(r"\bCHAPTER\s+[IVXL]+\b"),
    re.compile(r"\b\d{1,3} of (?:19|20)\d{2}\."),
)

MARGINAL_CANDIDATE = re.compile(
    r"(?:(?<=[a-z\)])\s|(?<=\.)\s)([A-Z][^.;,]{3,70}\.)\s*(?=\[PART|CHAPTER\s+[IVXL]+|SEC\.\s*\d+\])")

SUBSECTION = re.compile(r"\((\d{1,2})\)\s")
LETTERED = re.compile(r"\(([a-z])\)\s")


def _normalise_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@node("C")
def clean_gazette_text(raw: str) -> dict:
    """Remove structural debris only. Returns cleaned text plus what was found and left behind."""
    marginal = [m.group(1) for m in MARGINAL_CANDIDATE.finditer(raw)]
    cleaned = raw
    removed = 0
    for pattern in STRUCTURAL:
        cleaned, n = pattern.subn(" ", cleaned)
        removed += n
    cleaned = _normalise_ws(cleaned)
    return {
        "text": cleaned,
        "structural_removals": removed,
        "marginal_note_candidate": marginal[0] if marginal else None,
        "pagebreak_artifact": bool(marginal),
    }


@node("C")
def split_subsections(text: str, mode: str = "numeric") -> dict[str, str]:
    """Split a section into its top-level subsections."""
    pattern = SUBSECTION if mode == "numeric" else LETTERED
    marks = [(m.start(), m.group(1)) for m in pattern.finditer(text)]
    if not marks:
        return {}
    out: dict[str, str] = {}
    for i, (start, label) in enumerate(marks):
        if label in out:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = _normalise_ws(text[start:end])
        if len(body) > 25:
            out[label] = body
    return out


@node("C")
def load_real_clauses(sources: Iterable[dict] = REAL_SOURCES,
                      derive: Optional[dict[str, dict]] = None) -> tuple[list[Clause], dict]:
    """Load the gazette-derived corpora into Clause records, with provenance intact."""
    derive = derive or {}
    clauses: list[Clause] = []
    stats = {"sections": 0, "derived": 0, "with_artifacts": 0, "files": [], "missing_files": []}

    for src in sources:
        path = Path(src["path"])
        if not path.exists():
            stats["missing_files"].append(str(path))
            continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        stats["files"].append({"path": str(path), "records": len(rows),
                               "expected": src.get("expected_sections"),
                               "matches_expected": len(rows) == src.get("expected_sections")})

        for row in rows:
            raw = row["text_verbatim"]
            cleaned = clean_gazette_text(raw)
            status = "verified_with_artifacts" if cleaned["pagebreak_artifact"] else "verified"
            if cleaned["pagebreak_artifact"]:
                stats["with_artifacts"] += 1

            section = Clause(
                clause_id=row["clause_id"],
                instrument=row["instrument"],
                jurisdiction=row.get("jurisdiction", "IN"),
                section=f"s.{row['section']}",
                text_verbatim=cleaned["text"],
                source_url=row["source_url"],
                sha256=sha256_text(cleaned["text"]),
                retrieved_at=row.get("retrieved_at", "2026-10-09"),
                verbatim_status=status,
                page=row.get("page"),
                source_pdf_sha256=row.get("source_pdf_sha256"),
                text_raw=raw,
                sha256_raw=row.get("sha256") or sha256_text(raw),
                pagebreak_artifact=cleaned["pagebreak_artifact"],
                marginal_note_candidate=cleaned["marginal_note_candidate"],
                provenance="gazette_pdf",
            )
            clauses.append(section)
            stats["sections"] += 1

            spec = derive.get(row["clause_id"])
            if not spec:
                continue
            parts = split_subsections(cleaned["text"], spec.get("mode", "numeric"))
            for label in spec.get("labels", list(parts)):
                body = parts.get(label)
                if not body:
                    continue
                own = MARGINAL_CANDIDATE.search(section.text_raw or "")
                own_note = None
                if own and own.group(1) in body:
                    own_note = own.group(1)
                sub_status = "verified_with_artifacts" if own_note else "verified"
                clauses.append(section.model_copy(update={
                    "clause_id": f"{row['clause_id']}.{label}",
                    "section": f"s.{row['section']}({label})",
                    "text_verbatim": body,
                    "sha256": sha256_text(body),
                    "parent_clause_id": row["clause_id"],
                    "provenance": "gazette_pdf_subsection",
                    "verbatim_status": sub_status,
                    "pagebreak_artifact": bool(own_note),
                    "marginal_note_candidate": own_note,
                }))
                stats["derived"] += 1

    return clauses, stats
