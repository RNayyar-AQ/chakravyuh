#!/usr/bin/env python3
"""Retrieval eval: BM25 vs vector vs hybrid vs hybrid+rerank vs tree. Y.3172 node: PP.

Scores the rubric's "knowledge base quality" criterion (spec §9.2). Reports recall@5 and MRR over
data/eval/retrieval_qa.jsonl and writes docs/retrieval_eval.md. The best mode is what the Adviser
should use -- the table is the evidence, not the assertion.

  python scripts/eval_retrieval.py            # all available modes
  python scripts/eval_retrieval.py --k 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.kb.retrieve import Retriever

DOCS = Path("docs")
DATA = Path("outputs")
QA_PATH = Path("data/eval/retrieval_qa.jsonl")
ALL_MODES = ["bm25", "vector", "hybrid", "hybrid_rerank", "tree"]


def load_qa(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def evaluate(retriever: Retriever, qa: list[dict], mode: str, k: int) -> dict:
    """recall@k = fraction of questions with at least one gold clause in the top k.
    MRR = mean of 1/rank of the first gold clause (0 when absent)."""
    hits_at_k = 0
    rr_total = 0.0
    per_question: list[dict] = []
    answered = 0
    abstain_scores: list[float] = []
    answerable_scores: list[float] = []
    for row in qa:
        gold = set(row["gold_clause_ids"])
        if not gold:
            # An unanswerable question. A retriever always returns its k best matches -- it has
            # no way to return nothing -- so the only honest thing to measure here is the TOP
            # SCORE: if the best match for a question with no answer scores as high as the best
            # match for one that has an answer, then no downstream threshold can tell them
            # apart and the Adviser's abstention cannot be grounded in retrieval at all.
            try:
                hits = retriever.search(row["question"], k=k, mode=mode)
            except Exception as exc:
                per_question.append({"qid": row["qid"], "error": str(exc)[:120]})
                continue
            abstain_scores.append(hits[0].score if hits else 0.0)
            per_question.append({"qid": row["qid"], "gold": [], "abstain_expected": True,
                                 "retrieved": [h.clause_id for h in hits],
                                 "top_score": round(hits[0].score, 4) if hits else 0.0})
            continue
        answered += 1
        try:
            hits = retriever.search(row["question"], k=k, mode=mode)
        except Exception as exc:
            per_question.append({"qid": row["qid"], "error": str(exc)[:120]})
            continue
        got = [h.clause_id for h in hits]
        found = gold & set(got)
        rank = next((i + 1 for i, c in enumerate(got) if c in gold), None)
        if found:
            hits_at_k += 1
        if rank:
            rr_total += 1.0 / rank
        if hits:
            answerable_scores.append(hits[0].score)
        per_question.append({"qid": row["qid"], "gold": sorted(gold), "retrieved": got,
                             "hit": bool(found), "first_gold_rank": rank,
                             "top_score": round(hits[0].score, 4) if hits else 0.0})
    if answered == 0:
        return {"mode": mode, "questions": 0, "recall_at_k": 0.0, "mrr": 0.0, "per_question": []}
    # Abstention separability: the fraction of (answerable, unanswerable) pairs in which the
    # answerable question's top score is the higher of the two. 1.0 means a single threshold
    # separates them perfectly; 0.5 means the top score carries no signal about answerability.
    separable = None
    if abstain_scores and answerable_scores:
        pairs = len(answerable_scores) * len(abstain_scores)
        wins = sum(1 for a in answerable_scores for b in abstain_scores
                   if a > b) + 0.5 * sum(1 for a in answerable_scores for b in abstain_scores
                                         if a == b)
        separable = round(wins / pairs, 3)
    return {"mode": mode, "questions": answered,
            "recall_at_k": round(hits_at_k / answered, 3),
            "mrr": round(rr_total / answered, 3),
            "abstention_questions": len(abstain_scores),
            "abstention_separability": separable,
            "mean_top_score_answerable": (round(sum(answerable_scores) / len(answerable_scores), 4)
                                          if answerable_scores else None),
            "mean_top_score_unanswerable": (round(sum(abstain_scores) / len(abstain_scores), 4)
                                            if abstain_scores else None),
            "per_question": per_question}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--qa", default=str(QA_PATH))
    ap.add_argument("--modes", nargs="*", default=ALL_MODES)
    args = ap.parse_args()

    qa = load_qa(Path(args.qa))
    retriever = Retriever()
    if not retriever.chunks:
        print("no chunks found: run scripts/build_kb.py first", file=sys.stderr)
        return 1

    vector_ready = retriever.chroma_ready()
    results = []
    for mode in args.modes:
        res = evaluate(retriever, qa, mode, args.k)
        if mode in ("vector",) and not vector_ready:
            res["note"] = "ChromaDB not available in this environment; scored 0 by definition"
        if mode == "hybrid" and not vector_ready:
            res["note"] = "degenerates to BM25 here: no vector index to fuse with"
        if mode == "hybrid_rerank":
            try:
                import sentence_transformers  # noqa: F401,PLC0415
            except ImportError:
                res["note"] = "reranker absent (sentence-transformers not installed): same as hybrid"
        results.append(res)
        sep = res.get("abstention_separability")
        print(f"{mode:16s} recall@{args.k}={res['recall_at_k']:.3f}  MRR={res['mrr']:.3f}  "
              f"abstain-sep={sep if sep is not None else '-'}  "
              f"(n={res['questions']})")

    best = max((r for r in results if r["questions"]), key=lambda r: (r["recall_at_k"], r["mrr"]),
               default=None)

    DOCS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Retrieval eval (generated by scripts/eval_retrieval.py -- do not edit)",
        "",
        f"{len(qa)} hand-labelled questions over the clause store; "
        f"{results[0]['questions'] if results else 0} have a gold clause and are scored here.",
        f"Gold labels live in `{args.qa}`. Metric: recall@{args.k} and MRR of the first gold clause.",
        "",
        f"- ChromaDB vector index available: **{'yes' if vector_ready else 'no'}**",
        "",
        f"| Retrieval mode | recall@{args.k} | MRR | Abstain. sep. | Questions | Note |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        sep = r.get("abstention_separability")
        lines.append(f"| `{r['mode']}` | {r['recall_at_k']:.3f} | {r['mrr']:.3f} "
                     f"| {sep if sep is not None else '-'} "
                     f"| {r['questions']} | {r.get('note', '')} |")
    if best:
        lines += ["", f"**Best mode in this environment: `{best['mode']}`** "
                      f"(recall@{args.k}={best['recall_at_k']:.3f}, MRR={best['mrr']:.3f}).", ""]
    lines += [
        "## How to read this honestly",
        "",
        "- **Abstention separability** is the fraction of (answerable, unanswerable) question",
        "  pairs in which the answerable one's top-1 score is higher. A retriever cannot return",
        "  nothing -- it always hands back its k best matches -- so this is what decides whether",
        "  the Adviser's abstention can rest on retrieval scores at all. 1.0 = one threshold",
        "  separates them cleanly; 0.5 = the top score says nothing about whether an answer",
        "  exists. The five unanswerable questions are not trick questions: each one asks about",
        "  something the gap register records as genuinely absent (battery backup, restoration",
        "  deadlines, Tampere party status, EU Art. 110, per-cell outage data).",
        "- **A saturated score is not a validated method.** With 157 clauses and lexically",
        "  distinctive questions, recall@5 has very little room to discriminate: a mode can reach",
        "  1.000 here and still be the wrong choice on a corpus of thousands of clauses. Treat this",
        "  table as a smoke test of the retrieval path, and re-run it after the clause store grows",
        "  before drawing any conclusion about which mode is better. MRR is the more informative",
        "  column at this size.",
        "- Statute text is lexical: section numbers and defined terms are exactly what BM25 is good",
        "  at, so BM25 is a serious baseline here and not a straw man.",
        "- Where the vector index is absent, `vector` scores 0 and `hybrid` degenerates to BM25.",
        "  Those rows measure this environment, not the methods.",
        "- `tree` is the vectorless section-tree navigator (P2 priority). It is reported whatever",
        "  it scores; most of the corpus is flat section records, so it has little tree to exploit.",
        "- Retrieval is used ONLY by the Adviser for free-text questions. No legality decision goes",
        "  through it: the policy engine fetches clauses by exact ID from the structured store.",
        "",
    ]
    (DOCS / "retrieval_eval.md").write_text("\n".join(lines), encoding="utf-8")
    (DATA / "retrieval_eval.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {DOCS / 'retrieval_eval.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
