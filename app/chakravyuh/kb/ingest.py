"""Ingest: source documents -> ITU reference Chroma KB + structured clause store. Y.3172 node: C."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

from ..schemas import Clause
from ..y3172 import node
from .clause_store import DEFAULT_DB, ClauseStore, load_jsonl, write_jsonl
from .real_sources import REAL_SOURCES, load_real_clauses

DERIVE_SUBSECTIONS = {
    "IN.TA2023.s20": {"mode": "numeric", "labels": ["1", "2"]},
    "IN.DPDP2023.s7": {"mode": "lettered", "labels": ["g", "h"]},
}

SEED_PATH = Path("data/sources/clause_seed.jsonl")
CHUNKS_PATH = Path("data/clauses/chunks.jsonl")
CHROMA_PATH = Path(os.environ.get("CHROMA_PATH", "data/chroma"))

COLLECTIONS = ("kb_main", "kb_decisions", "kb_framework")


@dataclass
class Chunk:
    """A retrievable unit of text. One chunk per clause, plus window chunks for long documents."""
    chunk_id: str
    text: str
    clause_id: str
    instrument: str
    jurisdiction: str
    section: str
    source_url: str
    collection: str
    page: int = -1
    sha256: str = ""
    verbatim_status: str = ""

    def metadata(self) -> dict:
        d = asdict(self)
        d.pop("text")
        return d


def _collection_for(clause: Clause) -> str:
    """Route a clause to an ITU reference collection."""
    if clause.jurisdiction == "INTL" and clause.instrument.startswith("ITU-T"):
        return "kb_framework"
    if "Review Committee" in clause.text_verbatim or clause.section.startswith("Direction"):
        return "kb_decisions"
    return "kb_main"


@node("C")
def chunk_clauses(clauses: Iterable[Clause], window_chars: int = 900) -> list[Chunk]:
    """One chunk per clause; split only clauses longer than window_chars, on sentence bounds."""
    chunks: list[Chunk] = []
    for c in clauses:
        header = f"[{c.instrument} -- {c.section}]"
        body = c.text_verbatim.strip()
        coll = _collection_for(c)
        if len(body) <= window_chars:
            parts = [body]
        else:
            sentences = re.split(r"(?<=[.;])\s+", body)
            parts, buf = [], ""
            for s in sentences:
                if buf and len(buf) + len(s) + 1 > window_chars:
                    parts.append(buf)
                    buf = s
                else:
                    buf = f"{buf} {s}".strip()
            if buf:
                parts.append(buf)
        for i, part in enumerate(parts):
            chunks.append(Chunk(
                chunk_id=f"{c.clause_id}#{i}",
                text=f"{header} {part}",
                clause_id=c.clause_id,
                instrument=c.instrument,
                jurisdiction=c.jurisdiction,
                section=c.section,
                source_url=c.source_url,
                collection=coll,
                page=c.page if c.page is not None else -1,
                sha256=c.sha256,
                verbatim_status=c.verbatim_status,
            ))
    return chunks


def write_chunks(chunks: Iterable[Chunk], path: str | Path = CHUNKS_PATH) -> int:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with p.open("w", encoding="utf-8") as fh:
        for ch in chunks:
            fh.write(json.dumps(asdict(ch), sort_keys=True) + "\n")
            n += 1
    return n


def load_chunks(path: str | Path = CHUNKS_PATH) -> list[Chunk]:
    p = Path(path)
    if not p.exists():
        return []
    return [Chunk(**json.loads(line)) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def chroma_available() -> bool:
    try:
        import chromadb  # noqa: F401,PLC0415
        return True
    except ImportError:
        return False


@node("C")
def ingest_to_chroma(chunks: list[Chunk], chroma_path: str | Path = CHROMA_PATH,
                     embed_model: Optional[str] = None) -> dict:
    """Push chunks into the ITU reference Chroma collections. Returns per-collection counts."""
    if not chroma_available():
        return {"status": "skipped", "reason": "chromadb not installed", "counts": {}}

    import chromadb  # noqa: PLC0415
    from chromadb.config import Settings  # noqa: PLC0415

    embed_model = embed_model or os.environ.get("CHAKRAVYUH_EMBED_MODEL", "ollama/nomic-embed-text")
    embedder, embedder_name = _build_embedder(embed_model)

    Path(chroma_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_path), settings=Settings(anonymized_telemetry=False))

    counts: dict[str, int] = {}
    for coll_name in COLLECTIONS:
        subset = [c for c in chunks if c.collection == coll_name]
        coll = client.get_or_create_collection(name=coll_name, metadata={"hnsw:space": "cosine"})
        if subset:
            kwargs = {
                "ids": [c.chunk_id for c in subset],
                "documents": [c.text for c in subset],
                "metadatas": [c.metadata() for c in subset],
            }
            if embedder is not None:
                kwargs["embeddings"] = embedder([c.text for c in subset])
            coll.upsert(**kwargs)
        counts[coll_name] = coll.count()
    return {"status": "ok", "embedder": embedder_name, "counts": counts, "path": str(chroma_path)}


def _build_embedder(embed_model: str):
    """Return (callable|None, name). None means 'let Chroma embed with its default'."""
    if not embed_model.startswith("ollama/"):
        return None, f"chroma-default (requested {embed_model})"
    try:
        import litellm  # noqa: PLC0415
        probe = litellm.embedding(model=embed_model, input=["probe"],
                                 api_base=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        _ = probe["data"][0]["embedding"]
    except Exception:
        return None, f"chroma-default (Ollama {embed_model} unreachable)"

    def embed(texts: list[str]) -> list[list[float]]:
        resp = litellm.embedding(model=embed_model, input=texts,
                                 api_base=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        return [row["embedding"] for row in resp["data"]]

    return embed, embed_model


@node("C")
def build(seed_path: str | Path = SEED_PATH, db_path: str | Path = DEFAULT_DB,
          push_chroma: bool = True, include_real: bool = True) -> dict:
    """Full ingest: real gazette clauses + model-written seed -> store, clauses.jsonl, chunks.jsonl."""
    seeded = load_jsonl(seed_path)
    real: list = []
    real_stats: dict = {"sections": 0, "derived": 0, "with_artifacts": 0, "files": [],
                        "missing_files": [], "skipped": not include_real}
    if include_real:
        real, real_stats = load_real_clauses(REAL_SOURCES, derive=DERIVE_SUBSECTIONS)

    merged: dict[str, object] = {c.clause_id: c for c in seeded}
    superseded = sorted(set(merged) & {c.clause_id for c in real})
    for c in real:
        merged[c.clause_id] = c
    clauses = [merged[k] for k in sorted(merged)]
    if not clauses:
        raise FileNotFoundError(f"no clauses from {seed_path} or {[s['path'] for s in REAL_SOURCES]}")
    real_stats["superseded_model_written"] = superseded

    store = ClauseStore(db_path)
    n_clauses = store.upsert_many(clauses)
    write_jsonl(clauses)

    chunks = chunk_clauses(clauses)
    n_chunks = write_chunks(chunks)

    chroma = ingest_to_chroma(chunks) if push_chroma else {"status": "skipped", "reason": "disabled", "counts": {}}
    report = store.integrity_report()
    store.close()
    return {"clauses": n_clauses, "chunks": n_chunks, "chroma": chroma, "integrity": report,
            "real": real_stats}
