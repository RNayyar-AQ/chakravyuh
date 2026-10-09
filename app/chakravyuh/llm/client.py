"""LiteLLM wrapper + record/replay cache. Y.3172 node: M.

Replayability (spec §0): LLMs are not bit-deterministic, so the cache is what makes
"replay from seed" true. Cache key = sha256(model, prompt, schema). Modes:

  record  -- call the provider, write cache/<sha>.json
  replay  -- read the cache; a miss raises CacheMiss (fails loudly, never silently calls out)
  live    -- call the provider, do not persist (development only)

The demo runs in replay mode: identical every time and immune to Wi-Fi.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Optional

from ..y3172 import node

DEFAULT_CACHE = Path(os.environ.get("CHAKRAVYUH_LLM_CACHE", "cache"))

# Which credential each provider needs, by model-id prefix. LiteLLM reads these variables itself;
# they are listed here only so a `record` run fails in one second with the name of the missing
# variable, instead of failing deep inside a provider SDK after the first prompt is built.
#
# NOTHING in the deterministic pipeline needs any of these: rule twins, the policy engine, the
# clause store, properties, gaps, fuzzing and the extractive Adviser all run with no credential.
PROVIDER_CREDENTIALS: tuple[tuple[str, str], ...] = (
    ("ollama/", ""),                      # local, no key; needs OLLAMA_BASE_URL reachable
    ("openai/", "OPENAI_API_KEY"),
    ("gpt-", "OPENAI_API_KEY"),
    ("o1-", "OPENAI_API_KEY"),
    ("gemini/", "GEMINI_API_KEY"),
    ("vertex_ai/", "GOOGLE_APPLICATION_CREDENTIALS"),
    ("azure/", "AZURE_API_KEY"),
    ("bedrock/", "AWS_ACCESS_KEY_ID"),
    ("mistral/", "MISTRAL_API_KEY"),
    ("groq/", "GROQ_API_KEY"),
)

DEFAULT_LOCAL_MODEL = "ollama/qwen2.5:14b"


def credential_env_for(model: str) -> Optional[str]:
    """Name of the env var this model needs, or None when it needs no credential."""
    for prefix, var in PROVIDER_CREDENTIALS:
        if model.startswith(prefix):
            return var or None
    return None     # unknown provider: let LiteLLM decide rather than guessing wrong


def missing_credential(model: str) -> Optional[str]:
    """Name of the required env var that is absent or empty, or None when the model is usable."""
    var = credential_env_for(model)
    if var and not os.environ.get(var):
        return var
    return None


def credential_help(model: str, missing: str) -> str:
    """One message that names the missing variable and every way out of it."""
    return (
        f"model {model!r} needs {missing} in the environment and it is unset.\n"
        f"  export {missing}=...                     use that provider, or\n"
        f"  export CHAKRAVYUH_LOCAL_MODEL=ollama/qwen2.5:14b   use a local model (no key), or\n"
        f"  export CHAKRAVYUH_LLM_MODE=replay                  replay a recorded cache, or\n"
        f"  drop --tier llm                                    use the deterministic twins."
    )


def _is_connection_error(exc: Exception) -> bool:
    """True when a provider call failed to reach the endpoint at all, rather than being refused."""
    name = type(exc).__name__
    if name in ("APIConnectionError", "ConnectionError", "ConnectError", "Timeout",
                "APITimeoutError"):
        return True
    text = str(exc).lower()
    return any(m in text for m in ("connection refused", "connection error", "failed to connect",
                                   "max retries exceeded", "cannot connect"))


@node("M")
def resolve_model(prefer_hosted: bool = False, explicit: Optional[str] = None) -> str:
    """Pick the model id: an explicit one wins, then the hosted/local env var, then the default.

    Spec §3 wants the same code to run against the ITU Sandbox's local Ollama `qwen2.5:14b` and
    against one hosted model used for the showcase run only. `prefer_hosted` is how a caller asks
    for the latter without hard-coding a provider anywhere.
    """
    if explicit:
        return explicit
    if prefer_hosted:
        hosted = os.environ.get("CHAKRAVYUH_HOSTED_MODEL")
        if hosted:
            return hosted
    return os.environ.get("CHAKRAVYUH_LOCAL_MODEL", DEFAULT_LOCAL_MODEL)


class CacheMiss(RuntimeError):
    """Replay mode asked for a completion that was never recorded."""


class LLMUnavailable(RuntimeError):
    """record/live mode requested but LiteLLM or credentials are absent."""


def cache_key(model: str, prompt: str, schema_name: str) -> str:
    h = hashlib.sha256()
    for part in (model, prompt, schema_name):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class LLMResponse:
    __slots__ = ("text", "model", "latency_s", "tokens", "cache_status")

    def __init__(self, text: str, model: str, latency_s: float, tokens: dict, cache_status: str):
        self.text = text
        self.model = model
        self.latency_s = latency_s
        self.tokens = tokens
        self.cache_status = cache_status


@node("M")
class LLMClient:
    """Deterministic-by-cache LLM client (LiteLLM -> Ollama or a hosted model)."""

    def __init__(self, model: Optional[str] = None, mode: Optional[str] = None,
                 cache_dir: str | Path = DEFAULT_CACHE, temperature: float = 0.0,
                 prefer_hosted: bool = False):
        self.model = resolve_model(prefer_hosted=prefer_hosted, explicit=model)
        self.mode = (mode or os.environ.get("CHAKRAVYUH_LLM_MODE", "replay")).lower()
        if self.mode not in ("record", "replay", "live"):
            raise ValueError(f"unknown LLM mode {self.mode!r}; expected record|replay|live")
        self.cache_dir = Path(cache_dir)
        self.temperature = temperature
        self.calls = 0
        self.hits = 0
        self.misses = 0

    # -- cache -------------------------------------------------------------
    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> dict | None:
        p = self._cache_path(key)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return None

    def _write_cache(self, key: str, record: dict) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path(key).write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")

    def seed_cache(self, prompt: str, text: str, schema_name: str = "", model: Optional[str] = None) -> str:
        """Record a completion without a provider. Used by tests and offline demo fixtures."""
        model = model or self.model
        key = cache_key(model, prompt, schema_name)
        self._write_cache(key, {"model": model, "schema": schema_name, "text": text,
                                "tokens": {"prompt": 0, "completion": 0}, "source": "seeded"})
        return key

    # -- completion --------------------------------------------------------
    @node("M")
    def complete(self, prompt: str, *, system: str = "", schema_name: str = "",
                 max_tokens: int = 1024) -> LLMResponse:
        """Return a completion. In replay mode a cache miss raises CacheMiss."""
        full_prompt = f"{system}\n\n---\n\n{prompt}" if system else prompt
        key = cache_key(self.model, full_prompt, schema_name)
        self.calls += 1

        if self.mode in ("replay", "record"):
            cached = self._read_cache(key)
            if cached is not None:
                self.hits += 1
                return LLMResponse(cached["text"], cached.get("model", self.model), 0.0,
                                   cached.get("tokens", {}), "hit")
            if self.mode == "replay":
                self.misses += 1
                raise CacheMiss(
                    f"replay cache miss for model={self.model} schema={schema_name or '-'} key={key[:16]}...\n"
                    f"Run with CHAKRAVYUH_LLM_MODE=record to populate cache/{key}.json"
                )

        started = time.perf_counter()
        text, tokens = self._call_provider(full_prompt, max_tokens)
        latency = time.perf_counter() - started
        if self.mode == "record":
            self._write_cache(key, {"model": self.model, "schema": schema_name, "text": text,
                                    "tokens": tokens, "source": "recorded"})
        return LLMResponse(text, self.model, latency, tokens, "miss")

    def _call_provider(self, prompt: str, max_tokens: int) -> tuple[str, dict]:
        try:
            import litellm  # noqa: PLC0415  (optional dependency)
        except ImportError as exc:  # pragma: no cover - exercised only without litellm
            raise LLMUnavailable(
                "litellm is not installed; install the 'llm' extra or use CHAKRAVYUH_LLM_MODE=replay"
            ) from exc

        # Fail now, with the name of the variable, rather than inside the provider SDK.
        missing = missing_credential(self.model)
        if missing:
            raise LLMUnavailable(credential_help(self.model, missing))

        # LiteLLM prints its own feedback banner to stderr on any exception. We raise a message
        # that already says what to do, so the banner is just noise on a demo screen.
        litellm.suppress_debug_info = True

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if self.model.startswith("ollama/"):
            kwargs["api_base"] = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            resp = litellm.completion(**kwargs)
        except Exception as exc:
            # A local model needs no key but does need Ollama running; a raw provider traceback
            # on build day is the wrong thing to be reading. Name the cause and the fix.
            if self.model.startswith("ollama/") and _is_connection_error(exc):
                base = kwargs.get("api_base")
                raise LLMUnavailable(
                    f"cannot reach Ollama at {base} for model {self.model!r}.\n"
                    f"  ollama serve                      start it, then\n"
                    f"  ollama pull {self.model.split('/', 1)[1]}\n"
                    f"No API key is needed for a local model, only a running Ollama. "
                    f"Alternatively use CHAKRAVYUH_LLM_MODE=replay, which needs no provider."
                ) from exc
            raise LLMUnavailable(
                f"provider call failed for model {self.model!r}: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        text = resp["choices"][0]["message"]["content"]
        usage = resp.get("usage") or {}
        tokens = {"prompt": usage.get("prompt_tokens", 0), "completion": usage.get("completion_tokens", 0)}
        return text, tokens


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response (handles ```json fences and prose)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start = cleaned.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(cleaned[start:], start):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(cleaned[start:i + 1])
    raise ValueError(f"unterminated JSON object in model output: {text[:200]!r}")
