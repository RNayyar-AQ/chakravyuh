"""Policy & Legal Adviser: queryable RAG with a hard citation check. Y.3172 node: M."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from ..audit.ledger import Ledger
from ..audit.trace import llm_trace_payload
from ..kb.clause_store import ClauseStore, DEFAULT_DB
from ..kb.retrieve import Hit, Mode, Retriever
from ..llm.client import CacheMiss, LLMClient, extract_json
from ..y3172 import node

SYSTEM = """You are the Policy & Legal Adviser. Answer using ONLY the clauses provided.
Every claim must cite a clause_id from the context. If the clauses do not answer the question,
say so and name what is missing; this is a gap, report it as GAP: <description>.
Output JSON: {"answer": str, "cited_clause_ids": [str], "gaps": [str], "confidence": "high|medium|low"}"""

USER = """Question: {question}

{situation}Clauses retrieved for this question:
{context}

Answer in JSON only. Cite only clause_ids that appear above."""

REJECTION_NOTE = ("Your previous answer cited a clause_id that is not in the context above. "
                  "Cite only clause_ids listed, or say the clauses do not answer the question.")


class AdviserAnswer(BaseModel):
    question: str
    answer: str
    cited_clause_ids: list[str] = []
    gaps: list[str] = []
    confidence: Literal["high", "medium", "low"] = "low"
    retrieved_chunk_ids: list[str] = []
    retrieved_clause_ids: list[str] = []
    mode: Literal["llm", "extractive"] = "extractive"
    retrieval_mode: str = "hybrid"
    rejected_citations: list[str] = []
    attempts: int = 1

    def citations_markdown(self, store: Optional[ClauseStore] = None) -> str:
        if not self.cited_clause_ids:
            return "_(no clause cited)_"
        lines = []
        for cid in self.cited_clause_ids:
            clause = store.try_get(cid) if store else None
            if clause is None:
                lines.append(f"- `{cid}`")
                continue
            flag = "" if clause.verbatim_status == "verified" else " **[unverified summary]**"
            lines.append(f"- `{cid}` - {clause.instrument}, {clause.section}{flag}  \n"
                         f"  <{clause.source_url}>")
        return "\n".join(lines)


@node("M")
class Adviser:
    """Retrieve -> answer -> verify citations. Holds no powers and proposes no actions."""
    role_id = "adviser"
    tier = "adviser"

    def __init__(self, retriever: Optional[Retriever] = None, store: Optional[ClauseStore] = None,
                 client: Optional[LLMClient] = None, ledger: Optional[Ledger] = None,
                 retrieval_mode: Mode = "hybrid", k: int = 5, use_llm: bool = True):
        self.retriever = retriever or Retriever(mode=retrieval_mode)
        self.store = store or ClauseStore(DEFAULT_DB)
        self.client = client
        self.ledger = ledger
        self.retrieval_mode: Mode = retrieval_mode
        self.k = k
        self.use_llm = use_llm
        self.llm_calls = 0

    def retrieve(self, question: str) -> list[Hit]:
        return self.retriever.search(question, k=self.k, mode=self.retrieval_mode)

    def _context(self, hits: list[Hit]) -> str:
        lines = []
        for h in hits:
            clause = self.store.try_get(h.clause_id)
            status = ("" if clause and clause.verbatim_status == "verified"
                      else " [UNVERIFIED SUMMARY, not verbatim source text]")
            lines.append(f"clause_id: {h.clause_id}{status}\n{h.text}\n")
        return "\n".join(lines) if lines else "(no clauses retrieved)"

    @node("M")
    def ask(self, question: str, t: Optional[int] = None, situation: str = "") -> AdviserAnswer:
        """Answer a question with cited clauses. Falls back to extractive when no model is usable."""
        hits = self.retrieve(question)
        allowed = {h.clause_id for h in hits}
        situation_block = f"Current situation:\n{situation}\n\n" if situation else ""

        if not self.use_llm or self.client is None:
            answer = self._extractive(question, hits)
        else:
            answer = self._llm_answer(question, hits, allowed, situation_block, t)

        answer.retrieved_chunk_ids = [h.chunk_id for h in hits]
        answer.retrieved_clause_ids = sorted(allowed)
        answer.retrieval_mode = str(self.retrieval_mode)
        if self.ledger is not None:
            self.ledger.append("ADVISER_QA", answer.model_dump(), t or 0)
        return answer

    def _extractive(self, question: str, hits: list[Hit]) -> AdviserAnswer:
        """No generation: present the retrieved clauses verbatim and say that is what this is."""
        if not hits:
            return AdviserAnswer(question=question, answer="No clause in the knowledge base matches "
                                 "this question.", gaps=["No retrievable clause addresses the question."],
                                 confidence="low", mode="extractive")
        body = ["EXTRACTIVE ANSWER (retrieval only, no model reasoning). The most relevant clauses:"]
        for h in hits:
            clause = self.store.try_get(h.clause_id)
            if clause is None:
                continue
            body.append(f"\n[{h.clause_id}] {clause.instrument}, {clause.section}:\n"
                        f"{clause.text_verbatim}")
        return AdviserAnswer(question=question, answer="\n".join(body),
                             cited_clause_ids=[h.clause_id for h in hits],
                             gaps=[], confidence="low", mode="extractive")

    def _llm_answer(self, question: str, hits: list[Hit], allowed: set[str],
                    situation_block: str, t: Optional[int]) -> AdviserAnswer:
        user = USER.format(question=question, situation=situation_block, context=self._context(hits))
        rejected: list[str] = []

        for attempt in (1, 2):
            prompt = user if attempt == 1 else f"{user}\n\n{REJECTION_NOTE}"
            try:
                resp = self.client.complete(prompt, system=SYSTEM, schema_name="AdviserAnswer")
            except CacheMiss:
                fallback = self._extractive(question, hits)
                fallback.attempts = attempt
                fallback.gaps = fallback.gaps + [
                    "No recorded model answer for this question in replay mode; "
                    "answer is extractive only."]
                return fallback
            self.llm_calls += 1
            try:
                raw = extract_json(resp.text)
            except ValueError:
                raw = {}
            cited = raw.get("cited_clause_ids") or []
            cited = [cited] if isinstance(cited, str) else [str(c) for c in cited]

            bad = [c for c in cited if c not in allowed or not self.store.exists(c)]
            if self.ledger is not None:
                self.ledger.append("LLM_TRACE", llm_trace_payload(
                    model=self.client.model, prompt=f"{SYSTEM}\n\n---\n\n{prompt}",
                    raw_output=resp.text, parsed=raw, latency_s=resp.latency_s,
                    tokens=resp.tokens, retrieved_chunk_ids=[h.chunk_id for h in hits],
                    cache_status=resp.cache_status, role="adviser"), t or 0)
            if not bad:
                return AdviserAnswer(
                    question=question, answer=str(raw.get("answer", "")).strip(),
                    cited_clause_ids=cited, gaps=[str(g) for g in (raw.get("gaps") or [])],
                    confidence=str(raw.get("confidence", "low")).lower()
                    if str(raw.get("confidence", "low")).lower() in ("high", "medium", "low") else "low",
                    mode="llm", rejected_citations=rejected, attempts=attempt)
            rejected.extend(bad)

        return AdviserAnswer(
            question=question,
            answer=("Insufficient evidence. The retrieved clauses do not support an answer, and the "
                    "citations offered could not be verified against the clause store."),
            cited_clause_ids=[], gaps=[f"Unverifiable citations offered: {sorted(set(rejected))}"],
            confidence="low", mode="llm", rejected_citations=sorted(set(rejected)), attempts=2)
