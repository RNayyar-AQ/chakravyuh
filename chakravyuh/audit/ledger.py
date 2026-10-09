"""Append-only, hash-chained JSONL ledger. Y.3172 node: SINK.

hash = sha256(prev_hash + canonical_json(payload)). `verify` recomputes the whole chain,
so editing, reordering, inserting or deleting any line is detectable (§7).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

from ..schemas import LedgerEntry, canonical_json
from ..y3172 import node

GENESIS = "0" * 64


def _entry_hash(prev_hash: str, seq: int, t_minutes: int, kind: str, payload: dict) -> str:
    # seq/t/kind are inside the hash too, so a line cannot be moved or relabelled undetected.
    material = f"{prev_hash}|{seq}|{t_minutes}|{kind}|{canonical_json(payload)}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@node("SINK")
class Ledger:
    """Append-only hash-chained run ledger."""

    def __init__(self, path: str | Path, run_id: str = ""):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self._seq = 0
        self._head = GENESIS
        if self.path.exists():
            for entry in read(self.path):
                self._seq = entry.seq + 1
                self._head = entry.hash
        else:
            self.path.touch()

    @property
    def head_hash(self) -> str:
        return self._head

    @property
    def length(self) -> int:
        return self._seq

    def append(self, kind: str, payload: dict, t_minutes: int = 0) -> LedgerEntry:
        h = _entry_hash(self._head, self._seq, t_minutes, kind, payload)
        entry = LedgerEntry(seq=self._seq, prev_hash=self._head, hash=h,
                            t_minutes=t_minutes, kind=kind, payload=payload)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.model_dump(), sort_keys=True, default=str) + "\n")
        self._seq += 1
        self._head = h
        return entry

    def entries(self, kind: str | None = None) -> list[LedgerEntry]:
        return [e for e in read(self.path) if kind is None or e.kind == kind]


def read(path: str | Path) -> Iterator[LedgerEntry]:
    p = Path(path)
    if not p.exists():
        return
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield LedgerEntry.model_validate_json(line)


@node("SINK")
def verify(path: str | Path) -> tuple[bool, str]:
    """Recompute the chain. Returns (ok, message); message names the first bad sequence number."""
    prev = GENESIS
    count = 0
    for expected_seq, entry in enumerate(read(path)):
        if entry.seq != expected_seq:
            return False, f"seq gap at {entry.seq}: expected {expected_seq}"
        if entry.prev_hash != prev:
            return False, f"broken link at seq {entry.seq}: prev_hash does not match seq {entry.seq - 1}"
        recomputed = _entry_hash(entry.prev_hash, entry.seq, entry.t_minutes, entry.kind, entry.payload)
        if recomputed != entry.hash:
            return False, f"payload tampered at seq {entry.seq}: hash mismatch"
        prev = entry.hash
        count += 1
    return True, f"OK: {count} entries, head {prev[:16]}..."
