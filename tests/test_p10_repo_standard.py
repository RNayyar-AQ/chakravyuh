"""Repo-standard guarantees: engine purity, forbidden claims, submission surface.

Each test here protects a promise the submission makes to a judge. They are cheap to run and
they fail loudly, which is the point: the claims they guard are exactly the ones nobody can
re-check by eye the morning of a demo.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Any import reaching the policy engine from one of these is a failure. `jev` is included
# pre-emptively: it is a typed-answer model and the engine must not acquire one by any route.
FORBIDDEN_ROOTS = ("chakravyuh.llm", "ollama", "openai", "anthropic", "litellm",
                   "langchain", "jev", "transformers", "chromadb", "sentence_transformers")

ENGINE_ENTRY = "chakravyuh.policy.engine"


def _project_imports(module: str) -> list[str]:
    """Every module name imported by `module`, with relative imports resolved."""
    path = ROOT.joinpath("app", *module.split(".")).with_suffix(".py")
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # relative: resolve against this module
                parts = module.split(".")[: -node.level] or ["chakravyuh"]
                base = ".".join(parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            if base:
                names.append(base)
                names += [f"{base}.{a.name}" for a in node.names]
    return names


def test_policy_engine_cannot_reach_any_model_transitively():
    """The P node must be a pure function. Checked across the whole import graph, not one file."""
    seen: set[str] = set()
    came_from: dict[str, str] = {}
    stack = [ENGINE_ENTRY]
    while stack:
        module = stack.pop()
        if module in seen:
            continue
        seen.add(module)
        for name in _project_imports(module):
            for bad in FORBIDDEN_ROOTS:
                if name == bad or name.startswith(bad + "."):
                    route, hop = [module], module
                    while hop in came_from:
                        hop = came_from[hop]
                        route.append(hop)
                    pytest.fail(f"policy engine reaches {name!r} via "
                                + " -> ".join(reversed(route)))
            if name.startswith("chakravyuh") and name not in seen:
                came_from.setdefault(name, module)
                stack.append(name)
    assert len(seen) > 5, "the import walk found almost nothing; the test is not doing its job"


def test_the_purity_check_would_actually_catch_a_violation():
    """Positive control: a test that cannot fail is not a test."""
    tainted = "chakravyuh.agents.adviser"            # legitimately imports the LLM client
    names = _project_imports(tainted)
    assert any(n.startswith("chakravyuh.llm") for n in names), (
        "the positive control no longer imports chakravyuh.llm; pick another module or the "
        "purity test above is unfalsifiable")


# ----------------------------------------------------------------- forbidden claims
SPEC_FILES = {"CHAKRAVYUH_REPO_STANDARD.md", "CHAKRAVYUH_RUBRIC_SHOWCASE.md",
              "CHAKRAVYUH_IMPLEMENTATION.md", "CHAKRAVYUH_REAL_DATA.md",
              "CHAKRAVYUH_KB_HARDENING.md", "test_p10_repo_standard.py", "LICENSE"}

# "certified"/"approved"/"compliant with" about ITU would be a false claim about endorsement.
OVERCLAIM = re.compile(r"(itu[- ]?(certified|approved|endorsed))"
                       r"|(certified\s+(by\s+)?(the\s+)?itu)"
                       r"|(compliant\s+with\s+(itu|y\.3172|x\.1303))", re.I)


def _repo_files(*suffixes: str):
    for path in ROOT.rglob("*"):
        if path.suffix not in suffixes or not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith((".venv", ".git", "out/", "docs/rubric_status", "kb_raw")):
            continue
        if path.name in SPEC_FILES:
            continue
        yield path, rel


def test_no_claim_of_itu_certification_or_compliance():
    """We are ALIGNED WITH and MAPPED TO ITU recommendations. Nothing more may be claimed."""
    bad = []
    for path, rel in _repo_files(".md", ".py", ".yaml", ".html"):
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if OVERCLAIM.search(line):
                bad.append(f"{rel}:{i}: {line.strip()[:90]}")
    assert not bad, "overclaimed ITU endorsement:\n" + "\n".join(bad)


# Mentioning a confidence interval to DISCLAIM it is correct and must not trip the check --
# the repo says "no money, no casualties, no confidence intervals" in several places on purpose.
# What would be wrong is ASSERTING one. A denial is a line carrying a negation near the phrase.
_DENIAL = re.compile(r"\b(no|not|never|without|rather than|neither|nor|none)\b", re.I)


def test_no_accuracy_or_confidence_interval_claims():
    """We hold no ground truth, so an asserted CI or accuracy figure is unsupportable."""
    pattern = re.compile(r"confidence interval|95%\s*(ci|confidence)|margin of error"
                         r"|accuracy of \d", re.I)
    bad = []
    for path, rel in _repo_files(".md", ".py", ".yaml"):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines, 1):
            if not pattern.search(line):
                continue
            # A disclaimer routinely wraps: "No money, no casualties, no / confidence intervals."
            # so the negation can sit on the line above. Check the sentence, not the line.
            window = " ".join(lines[max(0, i - 2):i + 1])
            if not _DENIAL.search(window):
                bad.append(f"{rel}:{i}: {line.strip()[:90]}")
    assert not bad, ("a confidence interval or accuracy figure is asserted rather than "
                     "disclaimed:\n" + "\n".join(bad))


def test_the_ci_check_would_catch_a_real_assertion():
    """Positive control for the test above."""
    assert _DENIAL.search("no confidence intervals are reported")
    assert not _DENIAL.search("we report a 95% confidence interval of 12-18 minutes")


# ----------------------------------------------------------------- submission surface
@pytest.mark.parametrize("name", [
    "LICENSE", "NOTICE", "CITATION.cff", "SUBMISSION.md", "README.md",
    "requirements.lock", ".env.example", "app/scripts/replay_demo.sh",
    "docs/limits.md", "docs/architecture.md", "data/sources/MANIFEST.yaml",
])
def test_submission_file_exists(name):
    assert (ROOT / name).exists(), f"{name} is missing; a judge is told it is there"


def test_replay_script_pins_replay_mode_and_is_executable():
    """The stage script must not be able to call a provider, whatever the environment says."""
    script = ROOT / "app/scripts/replay_demo.sh"
    text = script.read_text(encoding="utf-8")
    assert "CHAKRAVYUH_LLM_MODE=replay" in text
    assert script.stat().st_mode & 0o111, "replay_demo.sh is not executable"


def test_env_example_contains_no_real_secret():
    """A pasted key in .env.example is the classic way to publish one."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    leaked = re.findall(r"(sk-[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_\-]{30,})", text)
    assert not leaked, f".env.example contains what looks like a real key: {leaked}"


def test_submission_links_resolve():
    """Every repo-relative link in SUBMISSION.md must point at something that exists."""
    text = (ROOT / "SUBMISSION.md").read_text(encoding="utf-8")
    missing = []
    for target in re.findall(r"\]\(([^)#:]+)\)", text):
        if target.startswith(("http", "mailto")):
            continue
        if not (ROOT / target).exists():
            missing.append(target)
    assert not missing, f"SUBMISSION.md links to missing paths: {missing}"


def test_source_manifest_never_claims_an_unverified_document_is_held():
    """A `held` source must carry a sha256; `partial`/`wanted` must say what they block."""
    import yaml
    manifest = yaml.safe_load((ROOT / "data/sources/MANIFEST.yaml").read_text(encoding="utf-8"))
    for source in manifest["sources"]:
        status = source.get("status")
        if status == "held":
            assert source.get("sha256"), f"{source['id']} is marked held with no sha256"
            assert source.get("must_contain"), (
                f"{source['id']} is marked held with no must_contain check — a PDF that "
                f"downloads is not the same as the right PDF")
        else:
            assert source.get("partial_reason") or source.get("wanted_from"), (
                f"{source['id']} is {status} but does not say why or where to get it")
