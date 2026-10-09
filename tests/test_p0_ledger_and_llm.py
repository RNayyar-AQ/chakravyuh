"""P0 gate (spec §10): ledger tamper detection, LLM replay-cache miss raises."""
from __future__ import annotations

import json

import pytest

from chakravyuh.audit.ledger import Ledger, verify
from chakravyuh.llm.client import CacheMiss, LLMClient, cache_key, extract_json


def test_ledger_tamper_detected(tmp_path):
    path = tmp_path / "l.jsonl"
    led = Ledger(path)
    led.append("EVENT", {"a": 1}, 0)
    led.append("PROPOSAL", {"b": 2}, 15)
    led.append("VERDICT", {"c": 3}, 15)
    assert verify(path)[0]

    lines = path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["payload"]["b"] = 999
    lines[1] = json.dumps(entry, sort_keys=True)
    path.write_text("\n".join(lines) + "\n")

    ok, msg = verify(path)
    assert not ok
    assert "seq 1" in msg


def test_ledger_detects_deleted_line(tmp_path):
    path = tmp_path / "l.jsonl"
    led = Ledger(path)
    for i in range(4):
        led.append("EVENT", {"i": i}, i)
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:2] + lines[3:]) + "\n")
    assert not verify(path)[0]


def test_ledger_detects_reordered_lines(tmp_path):
    path = tmp_path / "l.jsonl"
    led = Ledger(path)
    for i in range(3):
        led.append("EVENT", {"i": i}, i)
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[1], lines[0], lines[2]]) + "\n")
    assert not verify(path)[0]


def test_replay_cache_miss_raises(tmp_path):
    client = LLMClient(mode="replay", cache_dir=tmp_path)
    with pytest.raises(CacheMiss):
        client.complete("a question", schema_name="Proposal")
    assert client.misses == 1


def test_replay_cache_hit_is_deterministic(tmp_path):
    client = LLMClient(mode="replay", cache_dir=tmp_path)
    client.seed_cache("a question", '{"action_type": "NOOP"}', "Proposal")
    first = client.complete("a question", schema_name="Proposal")
    second = client.complete("a question", schema_name="Proposal")
    assert first.text == second.text
    assert first.cache_status == "hit"


def test_cache_key_depends_on_model_prompt_and_schema():
    base = cache_key("m1", "p1", "s1")
    assert base != cache_key("m2", "p1", "s1")
    assert base != cache_key("m1", "p2", "s1")
    assert base != cache_key("m1", "p1", "s2")
    assert base == cache_key("m1", "p1", "s1")


@pytest.mark.parametrize("text,expected", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": {"b": 2}}\n```', {"a": {"b": 2}}),
    ('here you go: {"a": "}"} trailing', {"a": "}"}),
])
def test_extract_json(text, expected):
    assert extract_json(text) == expected


def test_extract_json_rejects_garbage():
    with pytest.raises(ValueError):
        extract_json("no object here")


# ------------------------------------------------- model selection and credentials

def test_resolve_model_prefers_explicit_then_hosted_then_local(monkeypatch):
    from chakravyuh.llm.client import DEFAULT_LOCAL_MODEL, resolve_model

    monkeypatch.delenv("CHAKRAVYUH_HOSTED_MODEL", raising=False)
    monkeypatch.delenv("CHAKRAVYUH_LOCAL_MODEL", raising=False)
    assert resolve_model() == DEFAULT_LOCAL_MODEL
    assert resolve_model(prefer_hosted=True) == DEFAULT_LOCAL_MODEL, \
        "asking for hosted with none configured must fall back, not fail"

    monkeypatch.setenv("CHAKRAVYUH_LOCAL_MODEL", "ollama/local-x")
    monkeypatch.setenv("CHAKRAVYUH_HOSTED_MODEL", "anthropic/hosted-y")
    assert resolve_model() == "ollama/local-x"
    assert resolve_model(prefer_hosted=True) == "anthropic/hosted-y"
    assert resolve_model(prefer_hosted=True, explicit="openai/gpt-z") == "openai/gpt-z"


def test_client_honours_prefer_hosted(monkeypatch, tmp_path):
    monkeypatch.setenv("CHAKRAVYUH_HOSTED_MODEL", "anthropic/claude-sonnet-5")
    monkeypatch.setenv("CHAKRAVYUH_LOCAL_MODEL", "ollama/qwen2.5:14b")
    assert LLMClient(cache_dir=tmp_path).model == "ollama/qwen2.5:14b"
    assert LLMClient(cache_dir=tmp_path, prefer_hosted=True).model == "anthropic/claude-sonnet-5"


@pytest.mark.parametrize("model,expected", [
    ("ollama/qwen2.5:14b", None),                     # local: no credential at all
    ("anthropic/claude-sonnet-5", "ANTHROPIC_API_KEY"),
    ("openai/gpt-4o", "OPENAI_API_KEY"),
    ("gemini/gemini-2.0-flash", "GEMINI_API_KEY"),
    ("some-unknown/model", None),                      # unknown: defer to LiteLLM, do not guess
])
def test_credential_env_for(model, expected):
    from chakravyuh.llm.client import credential_env_for
    assert credential_env_for(model) == expected


def test_missing_credential_respects_the_environment(monkeypatch):
    from chakravyuh.llm.client import missing_credential
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert missing_credential("anthropic/claude-sonnet-5") == "ANTHROPIC_API_KEY"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert missing_credential("anthropic/claude-sonnet-5") is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert missing_credential("anthropic/claude-sonnet-5") == "ANTHROPIC_API_KEY", \
        "an empty string is not a credential"
    assert missing_credential("ollama/qwen2.5:14b") is None


def test_replay_mode_needs_no_credential_at_all(monkeypatch, tmp_path):
    """The whole point of replay: the demo runs with no provider and no key."""
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    client = LLMClient(model="anthropic/claude-sonnet-5", mode="replay", cache_dir=tmp_path)
    client.seed_cache("q", '{"action_type": "NOOP"}', "Proposal")
    assert client.complete("q", schema_name="Proposal").text == '{"action_type": "NOOP"}'


def test_record_mode_names_the_missing_variable(monkeypatch, tmp_path):
    from chakravyuh.llm.client import LLMUnavailable
    pytest.importorskip("litellm", reason="preflight only fires once litellm is installed")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = LLMClient(model="anthropic/claude-sonnet-5", mode="record", cache_dir=tmp_path)
    with pytest.raises(LLMUnavailable, match="ANTHROPIC_API_KEY"):
        client.complete("q", schema_name="Proposal")


def test_env_example_documents_every_variable_the_code_reads():
    """A documented-but-unread variable is a trap; so is an undocumented one."""
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    # Count commented-out declarations too: `# OPENAI_API_KEY=` still documents the variable.
    declared = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", (root / ".env.example").read_text(),
                              flags=re.M))
    read: set[str] = set()
    for src in (root / "app" / "chakravyuh").rglob("*.py"):
        read |= set(re.findall(r'environ(?:\.get)?\(\s*"([A-Z][A-Z0-9_]+)"', src.read_text()))
    # Provider keys are read by LiteLLM and checked by credential_env_for, never by os.environ
    # here, so they are legitimately documented without appearing in `read`.
    from chakravyuh.llm.client import PROVIDER_CREDENTIALS
    provider_keys = {var for _prefix, var in PROVIDER_CREDENTIALS if var}

    assert read - declared == set(), f"undocumented variables: {sorted(read - declared)}"
    assert declared - read - provider_keys == set(), \
        f"documented but never read: {sorted(declared - read - provider_keys)}"
    # Every credential the code can demand must be documented somewhere the user will find it.
    env_text = (root / ".env.example").read_text()
    for var in sorted(provider_keys):
        if var in {"GOOGLE_APPLICATION_CREDENTIALS", "AWS_ACCESS_KEY_ID", "AZURE_API_KEY",
                   "MISTRAL_API_KEY", "GROQ_API_KEY"}:
            continue   # supported via LiteLLM but not among the documented showcase options
        assert var in env_text, f"{var} can be demanded but is not in .env.example"
