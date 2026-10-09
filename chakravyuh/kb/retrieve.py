"""Hybrid retrieval: BM25 + vector (+ tree) fused with RRF. Y.3172 node: PP.

Used ONLY by the Policy & Legal Adviser to answer free-text questions. The policy engine
never calls this -- legality is decided from clause IDs fetched exactly (§1.3).

Modes, all selectable so §9.2 can measure them against each other:
  bm25    -- lexical only (rank_bm25). Section numbers and defined terms are lexical,
             which is why this is a serious baseline on statute text, not a straw man.
  vector  -- ITU reference Chroma collections
  hybrid  -- reciprocal rank fusion of bm25 + vector
  tree    -- section-tree navigation (kb/tree_index.py, P2)
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Sequence

from ..y3172 import node
from .ingest import CHROMA_PATH, COLLECTIONS, Chunk, load_chunks

Mode = Literal["bm25", "vector", "hybrid", "tree", "hybrid_rerank"]
RRF_K = 60  # standard reciprocal-rank-fusion damping constant


@dataclass
class Hit:
    chunk_id: str
    clause_id: str
    text: str
    score: float
    instrument: str
    section: str
    source_url: str
    source: str  # which retriever produced it: bm25 | vector | rrf | tree


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens, keeping statute-style section tokens like `s.20(2)` joined."""
    text = text.lower()
    text = re.sub(r"[^\w().\-/]+", " ", text)
    return [t.strip(".") for t in text.split() if t.strip(".")]


@node("PP")
class Retriever:
    """Hybrid clause retriever over the ingested chunks."""

    def __init__(self, chunks: Optional[Sequence[Chunk]] = None,
                 chroma_path: str | Path = CHROMA_PATH, mode: Mode = "hybrid"):
        self.chunks: list[Chunk] = list(chunks) if chunks is not None else load_chunks()
        self.mode: Mode = mode
        self.chroma_path = Path(chroma_path)
        self._by_id = {c.chunk_id: c for c in self.chunks}
        self._bm25 = None
        self._chroma_client = None
        self._tree = None
        if self.chunks:
            self._build_bm25()

    # -- BM25 --------------------------------------------------------------
    def _build_bm25(self) -> None:
        try:
            from rank_bm25 import BM25Okapi  # noqa: PLC0415
            self._bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])
        except ImportError:
            self._bm25 = None  # falls back to the tf-idf scorer below

    def search_bm25(self, query: str, k: int = 5) -> list[Hit]:
        q = tokenize(query)
        if self._bm25 is not None:
            scores = self._bm25.get_scores(q)
        else:
            scores = self._tfidf_scores(q)
        order = sorted(range(len(self.chunks)), key=lambda i: -scores[i])[:k]
        return [self._hit(self.chunks[i], float(scores[i]), "bm25") for i in order if scores[i] > 0]

    def _tfidf_scores(self, q: list[str]) -> list[float]:
        """Minimal tf-idf, so retrieval works even without rank_bm25 installed."""
        docs = [tokenize(c.text) for c in self.chunks]
        n = len(docs)
        df: dict[str, int] = {}
        for d in docs:
            for t in set(d):
                df[t] = df.get(t, 0) + 1
        out = []
        for d in docs:
            score = 0.0
            for t in q:
                if t in d and t in df:
                    score += (d.count(t) / len(d)) * math.log(1 + n / df[t])
            out.append(score)
        return out

    # -- vector (Chroma) ---------------------------------------------------
    def chroma_ready(self) -> bool:
        try:
            import chromadb  # noqa: PLC0415,F401
        except ImportError:
            return False
        return self.chroma_path.exists()

    def search_vector(self, query: str, k: int = 5) -> list[Hit]:
        if not self.chroma_ready():
            return []
        import chromadb  # noqa: PLC0415
        from chromadb.config import Settings  # noqa: PLC0415
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(
                path=str(self.chroma_path), settings=Settings(anonymized_telemetry=False))
        hits: list[Hit] = []
        for name in COLLECTIONS:
            try:
                coll = self._chroma_client.get_collection(name)
            except Exception:
                continue
            if coll.count() == 0:
                continue
            res = coll.query(query_texts=[query], n_results=min(k, coll.count()))
            distances = res.get("distances") or [[0.0] * len(res["ids"][0])]
            for cid, dist in zip(res["ids"][0], distances[0], strict=False):
                chunk = self._by_id.get(cid)
                if chunk is None:
                    continue
                hits.append(self._hit(chunk, 1.0 - float(dist), "vector"))
        hits.sort(key=lambda h: -h.score)
        return hits[:k]

    # -- tree (P2) ---------------------------------------------------------
    def search_tree(self, query: str, k: int = 5) -> list[Hit]:
        from .tree_index import SectionTree  # noqa: PLC0415
        if self._tree is None:
            self._tree = SectionTree.from_chunks(self.chunks)
        return [self._hit(self._by_id[cid], score, "tree")
                for cid, score in self._tree.navigate(query, k) if cid in self._by_id]

    # -- fusion ------------------------------------------------------------
    @node("PP")
    def search(self, query: str, k: int = 5, mode: Optional[Mode] = None) -> list[Hit]:
        """Retrieve k chunks. `hybrid` fuses BM25 and vector ranks with RRF."""
        mode = mode or self.mode
        if mode == "bm25":
            return self.search_bm25(query, k)
        if mode == "vector":
            return self.search_vector(query, k)
        if mode == "tree":
            return self.search_tree(query, k)
        if mode in ("hybrid", "hybrid_rerank"):
            pool = 4 * k
            ranked = [self.search_bm25(query, pool), self.search_vector(query, pool)]
            fused = rrf([r for r in ranked if r])
            if mode == "hybrid_rerank":
                fused = self._rerank(query, fused, k)
            return fused[:k]
        raise ValueError(f"unknown retrieval mode {mode!r}")

    def _rerank(self, query: str, hits: list[Hit], k: int) -> list[Hit]:
        """Cross-encoder rerank (P2). No-op when sentence-transformers is absent."""
        try:
            from sentence_transformers import CrossEncoder  # noqa: PLC0415
        except ImportError:
            return hits
        model_name = os.environ.get("CHAKRAVYUH_RERANKER", "BAAI/bge-reranker-base")
        model = CrossEncoder(model_name)
        scores = model.predict([(query, h.text) for h in hits[: 4 * k]])
        rescored = [Hit(**{**h.__dict__, "score": float(s), "source": "rerank"})
                    for h, s in zip(hits, scores, strict=False)]
        rescored.sort(key=lambda h: -h.score)
        return rescored

    def _hit(self, chunk: Chunk, score: float, source: str) -> Hit:
        return Hit(chunk_id=chunk.chunk_id, clause_id=chunk.clause_id, text=chunk.text,
                   score=score, instrument=chunk.instrument, section=chunk.section,
                   source_url=chunk.source_url, source=source)


def rrf(rankings: list[list[Hit]], k: int = RRF_K) -> list[Hit]:
    """Reciprocal rank fusion: score(d) = sum over lists of 1/(k + rank(d))."""
    scores: dict[str, float] = {}
    best: dict[str, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            best.setdefault(hit.chunk_id, hit)
    out = []
    for cid, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        h = best[cid]
        out.append(Hit(**{**h.__dict__, "score": score, "source": "rrf"}))
    return out
