#!/usr/bin/env python3
"""Adviser eval on a 4-point rubric. Y.3172 node: M/SINK."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.agents.adviser import Adviser
from chakravyuh.kb.clause_store import ClauseStore
from chakravyuh.llm.client import CacheMiss, LLMClient, extract_json, missing_credential

DOCS = Path("docs")
DATA = Path("outputs")
CASES = Path("data/eval/adviser_cases.jsonl")

JUDGE_SYSTEM = """You score a legal adviser's answer against a rubric. You are not the adviser.
Return JSON: {"c2_correct_actor": true|false, "c3_flags_uncertainty": true|false, "why": "one line"}
c2: does the answer identify the right actor, body or mandate for the question?
c3: where the provided clauses cannot answer the question, does the answer SAY SO rather than
    asserting an answer anyway? If the question is fully answerable, c3 is true by default."""

JUDGE_USER = """Question: {question}
Gold clause ids: {gold}
Expected gap (empty if the question is answerable): {gap}
Rubric note for a human marker: {notes}

The adviser answered:
{answer}

Cited clause ids: {cited}

Score it. JSON only."""

UNCERTAINTY_MARKERS = ("insufficient evidence", "do not answer", "does not answer", "no clause",
                       "unverified", "cannot confirm", "out of scope", "not in the knowledge base",
                       "gap:", "missing")


def mechanical_scores(case: dict, ans) -> dict:
    gold = set(case["gold_clause_ids"])
    cited = set(ans.cited_clause_ids)
    store = ClauseStore()
    c1 = bool(gold & cited) if gold else not cited
    retrieved = set(ans.retrieved_clause_ids)
    c4 = all(store.exists(c) and c in retrieved for c in cited)
    store.close()
    text = (ans.answer or "").lower() + " " + " ".join(ans.gaps).lower()
    expects_gap = bool(case.get("expected_gap"))
    c3_heuristic = any(m in text for m in UNCERTAINTY_MARKERS) if expects_gap else True
    return {"c1_correct_clause": c1, "c4_no_invented_clause": c4,
            "c3_heuristic": c3_heuristic, "expects_gap": expects_gap,
            "gold": sorted(gold), "cited": sorted(cited),
            "invented": sorted(c for c in cited if c not in retrieved)}


def judge(client: LLMClient, case: dict, ans) -> dict:
    user = JUDGE_USER.format(question=case["question"], gold=case["gold_clause_ids"],
                             gap=case.get("expected_gap", ""), notes=case.get("rubric_notes", ""),
                             answer=(ans.answer or "")[:3000], cited=ans.cited_clause_ids)
    try:
        resp = client.complete(user, system=JUDGE_SYSTEM, schema_name="AdviserJudgement")
    except CacheMiss:
        return {"judged": False, "reason": "no recorded judgement in replay mode"}
    try:
        raw = extract_json(resp.text)
    except ValueError:
        return {"judged": False, "reason": "judge output unparseable"}
    return {"judged": True,
            "c2_correct_actor": bool(raw.get("c2_correct_actor")),
            "c3_flags_uncertainty": bool(raw.get("c3_flags_uncertainty")),
            "why": str(raw.get("why", ""))[:300]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", default=str(CASES))
    ap.add_argument("--use-llm", action="store_true", help="adviser generates answers via LiteLLM")
    ap.add_argument("--model", default=None, help="adviser model id (overrides the env default)")
    ap.add_argument("--hosted", action="store_true", help="use CHAKRAVYUH_HOSTED_MODEL")
    ap.add_argument("--judge-model", default="", help="model id for the LLM judge (must differ "
                                                      "from the adviser's model)")
    ap.add_argument("--retrieval-mode", default="hybrid")
    args = ap.parse_args()

    cases = [json.loads(l) for l in Path(args.cases).read_text(encoding="utf-8").splitlines() if l.strip()]
    adviser_client = (LLMClient(model=args.model, prefer_hosted=args.hosted)
                      if args.use_llm else None)
    for client in (adviser_client,):
        if client is not None and client.mode != "replay":
            missing = missing_credential(client.model)
            if missing:
                raise SystemExit(f"model {client.model!r} needs {missing} and it is unset")
    adviser = Adviser(retrieval_mode=args.retrieval_mode, client=adviser_client,
                      use_llm=args.use_llm)
    judge_client = None
    if args.judge_model:
        if adviser_client and args.judge_model == adviser_client.model:
            raise SystemExit("judge model must differ from the adviser's model")
        judge_client = LLMClient(model=args.judge_model)

    rows = []
    for case in cases:
        ans = adviser.ask(case["question"])
        row = {"cid": case["cid"], "question": case["question"], "mode": ans.mode,
               "confidence": ans.confidence, "rubric_notes": case.get("rubric_notes", ""),
               **mechanical_scores(case, ans)}
        row.update(judge(judge_client, case, ans) if judge_client else
                   {"judged": False, "reason": "no judge model configured"})
        row["answer_excerpt"] = (ans.answer or "")[:400]
        row["human_check"] = ""
        rows.append(row)
        flag = "ok " if row["c1_correct_clause"] and row["c4_no_invented_clause"] else "ATT"
        print(f"{flag} {row['cid']}: C1={row['c1_correct_clause']} C4={row['c4_no_invented_clause']} "
              f"C3h={row['c3_heuristic']} cited={len(row['cited'])}")

    n = len(rows)
    summary = {
        "cases": n,
        "adviser_mode": rows[0]["mode"] if rows else "n/a",
        "retrieval_mode": args.retrieval_mode,
        "c1_correct_clause": sum(r["c1_correct_clause"] for r in rows),
        "c4_no_invented_clause": sum(r["c4_no_invented_clause"] for r in rows),
        "c3_heuristic": sum(r["c3_heuristic"] for r in rows),
        "judged": sum(bool(r.get("judged")) for r in rows),
        "c2_correct_actor": sum(1 for r in rows if r.get("judged") and r.get("c2_correct_actor")),
        "c3_flags_uncertainty": sum(1 for r in rows if r.get("judged") and r.get("c3_flags_uncertainty")),
        "human_checked": 0,
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "adviser_eval.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2),
                                           encoding="utf-8")
    (DOCS / "adviser_eval.md").write_text(report(summary, rows), encoding="utf-8")
    print(f"\nC1 {summary['c1_correct_clause']}/{n}  C4 {summary['c4_no_invented_clause']}/{n}  "
          f"judged {summary['judged']}/{n}  human-checked 0/{n}")
    print(f"wrote {DOCS / 'adviser_eval.md'}")
    return 0


def report(summary: dict, rows: list[dict]) -> str:
    n = summary["cases"]
    lines = [
        "# Adviser eval (generated by app/scripts/eval_adviser.py -- do not edit)",
        "",
        f"{n} mid-scenario questions. Adviser mode: **`{summary['adviser_mode']}`**, "
        f"retrieval `{summary['retrieval_mode']}`.",
        "",
        "## Rubric",
        "",
        "| Criterion | Decided by | Score |",
        "|---|---|---|",
        f"| C1 correct clause cited | mechanically (gold clause in citations) | "
        f"**{summary['c1_correct_clause']}/{n}** |",
        f"| C2 correct actor / mandate | LLM judge + human | "
        f"{summary['c2_correct_actor']}/{summary['judged']} judged |",
        f"| C3 flags uncertainty when the KB lacks an answer | LLM judge + human "
        f"(heuristic shown separately) | {summary['c3_flags_uncertainty']}/{summary['judged']} judged "
        f"(heuristic {summary['c3_heuristic']}/{n}) |",
        f"| C4 no invented clause | mechanically (citation exists AND was retrieved) | "
        f"**{summary['c4_no_invented_clause']}/{n}** |",
        "",
        "## How to read this honestly",
        "",
        "- **C1 and C4 are the trustworthy rows.** They are decided by exact lookup against the",
        "  clause store, not by judgement. C4 at full marks means the citation gate held: the",
        "  adviser never cited a clause it had not retrieved and that does not exist.",
        f"- **C2 and C3 are {'unjudged in this run' if not summary['judged'] else 'judge-scored'}.**",
        "  A row with no judge is reported as `unjudged`, never as a pass. Configure",
        "  `--judge-model` with a model DIFFERENT from the adviser's to score them.",
        "- **The `human_check` column ships empty.** The spec's own lesson is that humans catch what",
        "  judges miss, so all 20 rows are meant to be hand-marked and every disagreement with the",
        "  judge reported. An eval with that column empty is not finished.",
    ]
    if summary["adviser_mode"] == "extractive":
        lines += ["- This run used the **extractive** adviser: it quotes retrieved clauses and",
                  "  generates no prose. C1 and C4 therefore measure retrieval and the citation gate,",
                  "  not legal reasoning. Re-run with `--use-llm` against a populated cache to",
                  "  measure the reasoning."]
    lines += ["", "## Per-case", "",
              "| Case | C1 | C4 | C3 heuristic | Expects a gap | Cited | Judge | Human |",
              "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        judged = ("-" if not r.get("judged") else
                  f"C2={'Y' if r.get('c2_correct_actor') else 'N'} "
                  f"C3={'Y' if r.get('c3_flags_uncertainty') else 'N'}")
        lines.append(f"| {r['cid']} | {'Y' if r['c1_correct_clause'] else 'N'} "
                     f"| {'Y' if r['c4_no_invented_clause'] else 'N'} "
                     f"| {'Y' if r['c3_heuristic'] else 'N'} | {'yes' if r['expects_gap'] else 'no'} "
                     f"| {len(r['cited'])} | {judged} | _(blank)_ |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
