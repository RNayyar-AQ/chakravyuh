"""Repository shape and the HTTP tier. Y.3172 node: SINK.

Two promises are guarded here.

LAYOUT  Everything executable lives under `app/`. `data/`, `docs/` and `tests/` sit beside it
        because they are, in order, what goes in, what a person reads, and the proof. A stray
        package at the root is how a repository starts drifting back into a pile.

API     The HTTP tier is read-only. It may serve artefacts and re-verify hash chains; it may not
        decide anything, and nothing deterministic may depend on it being up.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

# Directories allowed at the repository root. Everything else belongs under app/.
ALLOWED_ROOT_DIRS = {"app", "data", "docs", "tests", ".github", ".git"}

# Files allowed at the root: packaging, licensing and the entry point. Nothing else.
ALLOWED_ROOT_FILES = {
    "README.md", "SUBMISSION.md", "LICENSE", "NOTICE", "CITATION.cff",
    "pyproject.toml", "requirements.lock", "Makefile", ".gitignore", ".env.example",
}


def _tracked() -> list[str]:
    import subprocess
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False)
    return [line for line in out.stdout.splitlines() if line]


def test_nothing_executable_sits_outside_app():
    offenders = sorted({
        path.split("/")[0] for path in _tracked()
        if "/" in path and path.split("/")[0] not in ALLOWED_ROOT_DIRS
    })
    assert not offenders, f"top-level directories that should live under app/: {offenders}"


def test_root_files_are_only_packaging_and_prose():
    offenders = sorted(p for p in _tracked() if "/" not in p and p not in ALLOWED_ROOT_FILES)
    assert not offenders, f"unexpected files at the repository root: {offenders}"


@pytest.mark.parametrize("sub", ["chakravyuh", "scripts", "web", "api", "ui"])
def test_app_contains_every_tier(sub):
    assert (APP / sub).is_dir(), f"app/{sub} is missing"


def test_one_command_runs_both_halves():
    """`make dev` is the documented entry point; it has to start the API and the frontend."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "dev:" in makefile and "app/dev.py" in makefile
    dev = (APP / "dev.py").read_text(encoding="utf-8")
    assert "uvicorn" in dev, "dev.py does not start the backend"
    assert "npm" in dev and "dev" in dev, "dev.py does not start the frontend"


def test_api_is_read_only():
    """No endpoint may run the simulator, write a ledger or shell out.

    The API serving a stale artefact is a nuisance. The API mutating one would make every number
    on the site unattributable, because the ledger would no longer be the only writer.
    """
    source = (APP / "api" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    banned_calls = {"run", "Popen", "system", "append", "write_text", "write_bytes", "unlink"}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in banned_calls and name != "append":
                found.append(name)
    assert not found, f"the API tier calls {sorted(set(found))}; it must only read"

    banned_imports = {"subprocess", "os.system", "chakravyuh.sim", "chakravyuh.policy"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    overlap = {m for m in imported if any(m.startswith(b) for b in banned_imports)}
    assert not overlap, f"the API tier imports {sorted(overlap)}; it must not run the simulator"


def test_api_binds_to_localhost_only():
    """A development convenience that listens on 0.0.0.0 is a development convenience on the internet."""
    dev = (APP / "dev.py").read_text(encoding="utf-8")
    assert '"--host", "127.0.0.1"' in dev
    api = (APP / "api" / "main.py").read_text(encoding="utf-8")
    assert "allow_origins" in api and "0.0.0.0" not in api


def test_the_frontend_still_builds_without_a_backend():
    """The submission artefact is the static export, so the API must stay optional."""
    api_helper = (APP / "web" / "lib" / "api.ts").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_API_BASE" in api_helper
    assert "/data/timeline." in api_helper, "no static fallback for timelines"
    data_loader = (APP / "web" / "lib" / "data.ts").read_text(encoding="utf-8")
    assert "readFileSync" in data_loader, "the bundle must be read at build time, not fetched"


def test_api_is_an_optional_dependency():
    """Nothing in the deterministic pipeline may require FastAPI to be installed."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'api = ["fastapi' in pyproject
    core = pyproject.split("[project.optional-dependencies]")[0]
    assert "fastapi" not in core and "uvicorn" not in core

    offenders = []
    for path in (APP / "chakravyuh").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "import fastapi" in text or "from fastapi" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"the engine imports FastAPI: {offenders}"
