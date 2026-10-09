"""Per-call trace capture. Y.3172 node: SINK.

Every LLM call writes an LLM_TRACE ledger entry: model, prompt sha256, retrieved chunk ids,
raw output, parsed object, latency, tokens. Prompt bodies live in traces/<sha>.txt so the
ledger stays small while remaining fully reconstructible (§7).
"""
from __future__ import annotations

from pathlib import Path

from ..schemas import sha256_text
from ..y3172 import node

TRACE_DIR = Path("traces")


@node("SINK")
def store_prompt(prompt: str, trace_dir: str | Path = TRACE_DIR) -> str:
    """Write a prompt to traces/<sha>.txt and return its sha256."""
    sha = sha256_text(prompt)
    d = Path(trace_dir)
    d.mkdir(parents=True, exist_ok=True)
    target = d / f"{sha}.txt"
    if not target.exists():
        target.write_text(prompt, encoding="utf-8")
    return sha


def load_prompt(sha: str, trace_dir: str | Path = TRACE_DIR) -> str | None:
    p = Path(trace_dir) / f"{sha}.txt"
    return p.read_text(encoding="utf-8") if p.exists() else None


@node("SINK")
def llm_trace_payload(*, model: str, prompt: str, raw_output: str, parsed: dict | None,
                      latency_s: float, tokens: dict, retrieved_chunk_ids: list[str],
                      cache_status: str, role: str = "", trace_dir: str | Path = TRACE_DIR) -> dict:
    """Build the LLM_TRACE payload. The prompt itself is stored out-of-band by sha."""
    return {
        "role": role,
        "model": model,
        "prompt_sha256": store_prompt(prompt, trace_dir),
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "raw_output": raw_output,
        "parsed": parsed,
        "latency_s": round(latency_s, 4),
        "tokens": tokens,
        "cache_status": cache_status,
    }
