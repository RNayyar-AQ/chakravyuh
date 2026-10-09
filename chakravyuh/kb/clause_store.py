"""Structured clause store: exact lookup by clause_id + verbatim/hash check. Y.3172 node: PP.

This is layer (1) of the hybrid KB (spec §0). Legality checks must NEVER go through
similarity search: rules cite clause IDs, the policy engine fetches clauses by ID from here,
and the verbatim check compares SHA-256 hashes (§1.3).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from ..schemas import Clause, sha256_text
from ..y3172 import node

DEFAULT_DB = Path("data/clauses/clauses.sqlite")
DEFAULT_JSONL = Path("data/clauses/clauses.jsonl")

SCHEMA = """
CREATE TABLE IF NOT EXISTS clauses (
    clause_id       TEXT PRIMARY KEY,
    instrument      TEXT NOT NULL,
    jurisdiction    TEXT NOT NULL,
    section         TEXT NOT NULL,
    text_verbatim   TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    sha256          TEXT NOT NULL,
    retrieved_at    TEXT NOT NULL,
    verbatim_status TEXT NOT NULL DEFAULT 'unverified_summary',
    page                    INTEGER,
    source_pdf_sha256       TEXT,
    text_raw                TEXT,
    sha256_raw              TEXT,
    pagebreak_artifact      INTEGER NOT NULL DEFAULT 0,
    marginal_note_candidate TEXT,
    parent_clause_id        TEXT,
    provenance      TEXT NOT NULL DEFAULT 'model_written'
);
CREATE INDEX IF NOT EXISTS idx_clauses_jurisdiction ON clauses(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_clauses_instrument   ON clauses(instrument);
"""

_COLS = ("clause_id", "instrument", "jurisdiction", "section", "text_verbatim",
         "source_url", "sha256", "retrieved_at", "verbatim_status",
         "page", "source_pdf_sha256", "text_raw", "sha256_raw",
         "pagebreak_artifact", "marginal_note_candidate", "parent_clause_id", "provenance")


def _row_to_clause(row) -> Clause:
    """sqlite3 stores booleans as integers; restore the typed shape Pydantic expects."""
    data = dict(row)
    data["pagebreak_artifact"] = bool(data.get("pagebreak_artifact", 0))
    return Clause(**data)


class ClauseNotFound(KeyError):
    """Asked for a clause_id that is not in the store. A rule citing one must fail compilation."""


class HashMismatch(ValueError):
    """Stored text no longer hashes to the recorded sha256: the source text drifted."""


@node("PP")
class ClauseStore:
    """Exact-lookup clause store over SQLite (stdlib sqlite3)."""

    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path)
        if str(db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- writes ------------------------------------------------------------
    def upsert(self, clause: Clause) -> None:
        if not clause.hash_matches():
            raise HashMismatch(f"{clause.clause_id}: sha256 does not match text_verbatim")
        self.conn.execute(
            f"INSERT OR REPLACE INTO clauses ({','.join(_COLS)}) VALUES ({','.join('?' * len(_COLS))})",
            tuple(int(v) if isinstance(v := getattr(clause, c), bool) else v for c in _COLS),
        )
        self.conn.commit()

    def upsert_many(self, clauses: Iterable[Clause]) -> int:
        n = 0
        for c in clauses:
            self.upsert(c)
            n += 1
        return n

    # -- reads -------------------------------------------------------------
    @node("PP")
    def get_clause(self, clause_id: str) -> Clause:
        """Exact lookup by clause_id. Raises ClauseNotFound -- never a fuzzy match."""
        row = self.conn.execute("SELECT * FROM clauses WHERE clause_id = ?", (clause_id,)).fetchone()
        if row is None:
            raise ClauseNotFound(clause_id)
        return _row_to_clause(row)

    def try_get(self, clause_id: str) -> Optional[Clause]:
        try:
            return self.get_clause(clause_id)
        except ClauseNotFound:
            return None

    def exists(self, clause_id: str) -> bool:
        return self.conn.execute("SELECT 1 FROM clauses WHERE clause_id = ?",
                                 (clause_id,)).fetchone() is not None

    def all_clauses(self) -> list[Clause]:
        rows = self.conn.execute("SELECT * FROM clauses ORDER BY clause_id").fetchall()
        return [_row_to_clause(r) for r in rows]

    def by_jurisdiction(self, jurisdiction: str) -> list[Clause]:
        rows = self.conn.execute("SELECT * FROM clauses WHERE jurisdiction = ? ORDER BY clause_id",
                                 (jurisdiction,)).fetchall()
        return [_row_to_clause(r) for r in rows]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM clauses").fetchone()[0]

    # -- integrity ---------------------------------------------------------
    @node("PP")
    def verify_verbatim(self, clause_id: str, expected_sha256: str) -> bool:
        """Hash-match check used by the policy compiler: does the cited text still hash as recorded?"""
        clause = self.get_clause(clause_id)
        return clause.sha256 == expected_sha256 and clause.hash_matches()

    def integrity_report(self) -> dict:
        """Counts for kb_report.md (§9.1): coverage of URL + hash, and verbatim-verification status."""
        clauses = self.all_clauses()
        total = len(clauses)
        per_instrument: dict[str, int] = {}
        per_jurisdiction: dict[str, int] = {}
        for c in clauses:
            per_instrument[c.instrument] = per_instrument.get(c.instrument, 0) + 1
            per_jurisdiction[c.jurisdiction] = per_jurisdiction.get(c.jurisdiction, 0) + 1
        with_url = sum(1 for c in clauses if c.source_url.startswith("http"))
        hash_ok = sum(1 for c in clauses if c.hash_matches())
        verified = sum(1 for c in clauses if c.is_real_text)
        quotable = sum(1 for c in clauses if c.quotable)
        per_provenance: dict[str, int] = {}
        per_status: dict[str, int] = {}
        for c in clauses:
            per_provenance[c.provenance] = per_provenance.get(c.provenance, 0) + 1
            per_status[c.verbatim_status] = per_status.get(c.verbatim_status, 0) + 1
        return {
            "total": total,
            "per_instrument": dict(sorted(per_instrument.items())),
            "per_jurisdiction": dict(sorted(per_jurisdiction.items())),
            "with_source_url": with_url,
            "pct_with_source_url": round(100.0 * with_url / total, 1) if total else 0.0,
            "hash_matching": hash_ok,
            "pct_hash_matching": round(100.0 * hash_ok / total, 1) if total else 0.0,
            "verbatim_verified": verified,
            "pct_verbatim_verified": round(100.0 * verified / total, 1) if total else 0.0,
            "quotable": quotable,
            "pct_quotable": round(100.0 * quotable / total, 1) if total else 0.0,
            "per_provenance": dict(sorted(per_provenance.items())),
            "per_verbatim_status": dict(sorted(per_status.items())),
            "with_source_pdf_hash": sum(1 for c in clauses if c.source_pdf_sha256),
        }

    def close(self) -> None:
        self.conn.close()


# -- JSONL interchange (data/clauses/clauses.jsonl is the reviewable, diffable form) --

def load_jsonl(path: str | Path = DEFAULT_JSONL) -> list[Clause]:
    """Read clauses from JSONL, recomputing sha256 when the file omits or stales it."""
    out: list[Clause] = []
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        raw = json.loads(line)
        raw["sha256"] = sha256_text(raw["text_verbatim"])
        out.append(Clause(**raw))
    return out


def write_jsonl(clauses: Iterable[Clause], path: str | Path = DEFAULT_JSONL) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8") as fh:
        for c in sorted(clauses, key=lambda x: x.clause_id):
            fh.write(json.dumps(c.model_dump(), sort_keys=True) + "\n")
            n += 1
    return n
