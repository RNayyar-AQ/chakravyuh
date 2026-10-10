"""Repository shape and the HTTP tier. Y.3172 node: SINK."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"

# `api/` is the one executable thing allowed outside app/: it is the entrypoint the `api` service
# in vercel.json names, it holds no logic beyond re-exporting app.backend.main, and the deploy
# cannot find it anywhere else.
ALLOWED_ROOT_DIRS = {"app", "api", "data", "docs", "tests", ".github", ".git"}

ALLOWED_ROOT_FILES = {
    "README.md", "SUBMISSION.md", "LICENSE", "NOTICE", "CITATION.cff",
    "pyproject.toml", "requirements.lock", "requirements.txt", "Makefile",
    ".gitignore", ".env.example", "vercel.json",
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


@pytest.mark.parametrize("sub", ["chakravyuh", "scripts", "web", "backend", "ui"])
def test_app_contains_every_tier(sub):
    assert (APP / sub).is_dir(), f"app/{sub} is missing"


def test_one_command_runs_both_halves():
    """`make dev` is the documented entry point; it has to start the API and the frontend."""
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "dev:" in makefile and "app/dev.py" in makefile
    dev = (APP / "dev.py").read_text(encoding="utf-8")
    assert "uvicorn" in dev, "dev.py does not start the backend"
    assert "npm" in dev and "dev" in dev, "dev.py does not start the frontend"


def test_api_writes_nothing():
    """The API may read artefacts and it may start the narrator. It may not edit anything."""
    source = (APP / "backend" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    # `run` and `system` would let any command through; the write calls would let the API edit
    # the artefacts it is supposed to be reporting on. `Popen` is allowed, but only for the one
    # command checked below -- see test_the_api_may_only_shell_out_to_the_narrator.
    banned_calls = {"run", "system", "write_text", "write_bytes", "unlink", "mkdir", "rmtree"}
    found = [
        name
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for name in [node.func.attr if isinstance(node.func, ast.Attribute)
                     else getattr(node.func, "id", "")]
        if name in banned_calls
    ]
    assert not found, f"the API tier calls {sorted(set(found))}; it must not write"


def test_api_never_runs_the_simulator_in_process():
    """Importing the simulator into the web process would put a decision inside the API."""
    source = (APP / "backend" / "main.py").read_text(encoding="utf-8")
    banned_imports = {"os.system", "chakravyuh.sim", "chakravyuh.policy", "chakravyuh.agents",
                      "chakravyuh.world", "chakravyuh.fuzz"}
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    overlap = {m for m in imported if any(m.startswith(b) for b in banned_imports)}
    assert not overlap, (f"the API tier imports {sorted(overlap)}; a narrated run must be a "
                         f"subprocess, so the API cannot hold simulator state between requests")


def test_the_api_may_only_shell_out_to_the_narrator():
    """One subprocess, one script, and the script is the narrator -- not an argument from a client.

    `/api/narrate` is the single endpoint that executes anything. The command it builds has to
    be assembled from constants, so no request body can reach the shell: the only value a
    caller supplies is `pack`, and that is checked against the packs on disk before use.
    """
    source = (APP / "backend" / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    popens = [n for n in ast.walk(tree)
              if isinstance(n, ast.Call)
              and (n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""))
              == "Popen"]
    assert len(popens) == 1, f"expected exactly one Popen in the API tier, found {len(popens)}"

    call = popens[0]
    assert not any(kw.arg == "shell" and getattr(kw.value, "value", False) is True
                   for kw in call.keywords), "the API must never use shell=True"

    # The command list is built once, from constants. Find it and check what it is made of.
    assigns = [n for n in ast.walk(tree)
               if isinstance(n, ast.Assign)
               and any(getattr(t, "id", "") == "cmd" for t in n.targets)]
    assert len(assigns) == 1, "the narrate command should be built in exactly one place"
    literals = {e.value for e in ast.walk(assigns[0].value)
                if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    assert "--color" in literals, "the narrator is invoked with explicit flags, not a free string"
    names = {getattr(e, "id", "") for e in ast.walk(assigns[0].value) if isinstance(e, ast.Name)}
    assert "NARRATE" in names, "the script path must come from the module constant"

    assert "req.pack not in available" in source, (
        "the pack a caller asks for must be checked against the packs on disk before it is used")


def test_narration_is_refused_where_it_cannot_run():
    """The public deployment is a static export with a read-only function. It must say so."""
    source = (APP / "backend" / "main.py").read_text(encoding="utf-8")
    assert 'os.environ.get("VERCEL")' in source, (
        "the serverless deployment cannot execute the simulator; narration must refuse there")
    assert "503" in source, "an unavailable narrator should answer 503, not fail at the shell"


def test_api_binds_to_localhost_only():
    """A development convenience that listens on 0.0.0.0 is a development convenience on the internet."""
    dev = (APP / "dev.py").read_text(encoding="utf-8")
    assert '"--host", "127.0.0.1"' in dev
    api = (APP / "backend" / "main.py").read_text(encoding="utf-8")
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


# Build and runtime keys belong to a service in services mode; leaving one at the top level is
# accepted by the schema and then silently ignored, so the deploy builds the wrong thing.
SERVICE_ONLY_KEYS = {
    "functions", "installCommand", "buildCommand", "devCommand",
    "ignoreCommand", "outputDirectory", "framework",
}


def _vercel() -> dict:
    import json
    return json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))


def test_vercel_config_matches_the_repository():
    """Every path vercel.json names must exist, or the first deploy is the one that finds out."""
    cfg = _vercel()
    services = cfg["services"]
    assert set(services) == {"web", "api"}, f"unexpected services: {sorted(services)}"

    stray = sorted(SERVICE_ONLY_KEYS & set(cfg))
    assert not stray, f"build keys left at the top level in services mode: {stray}"

    for name, svc in services.items():
        root = ROOT / svc["root"]
        assert root.is_dir(), f"service {name} has root {svc['root']!r}, which does not exist"

    assert services["web"]["framework"] == "nextjs"
    # The static export reads the API on its own origin only when this is baked in at build time.
    assert "NEXT_PUBLIC_HAS_API=1" in services["web"]["buildCommand"]

    entry = services["api"]["entrypoint"]
    assert (ROOT / entry).exists(), f"vercel.json points at {entry}, which does not exist"
    assert (ROOT / "requirements.txt").exists(), "the Python function has no requirements.txt"


def test_every_service_is_reachable_or_deliberately_internal():
    """A service with no rewrite is unreachable; a catch-all before a prefix hides it."""
    cfg = _vercel()
    rewrites = cfg["rewrites"]

    targeted = {r["destination"]["service"] for r in rewrites
                if isinstance(r["destination"], dict)}
    assert targeted == set(cfg["services"]), (
        f"services with no public route: {sorted(set(cfg['services']) - targeted)}"
    )

    catch_all = [i for i, r in enumerate(rewrites) if r["source"] == "/(.*)"]
    assert catch_all == [len(rewrites) - 1], "the catch-all rewrite must come last"


def test_the_api_routes_agree_with_its_public_prefix():
    """The rewrite does not strip /api, so FastAPI must declare its routes with it."""
    cfg = _vercel()
    prefix = next(r["source"] for r in cfg["rewrites"]
                  if r["destination"] == {"service": "api"}).removesuffix("(.*)")

    source = (APP / "backend" / "main.py").read_text(encoding="utf-8")
    routes = [node for node in ast.walk(ast.parse(source))
              if isinstance(node, ast.Call)
              and isinstance(node.func, ast.Attribute)
              and isinstance(node.func.value, ast.Name)
              and node.func.value.id == "app"
              and node.args
              and isinstance(node.args[0], ast.Constant)]
    paths = [node.args[0].value for node in routes]
    assert paths, "no routes found on the FastAPI app"
    offenders = [p for p in paths if not p.startswith(prefix)]
    assert not offenders, f"routes that the {prefix!r} rewrite will never reach: {offenders}"


def test_the_serverless_entry_point_exposes_the_app():
    """The entry must import without the simulator's dependencies being installed."""
    src = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "from app.backend.main import app" in src
    # `api/` at the repo root and a package also named `api` under app/ cannot coexist: the
    # editable install's finder wins and shadows the one Vercel needs. The tier is `backend`.
    assert not (APP / "api").exists(), "app/api shadows the root api/ package Vercel requires"


def test_function_requirements_stay_minimal():
    """The function must not quietly acquire the simulator's dependency tree."""
    reqs = [l.strip().split(">=")[0].split("==")[0]
            for l in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]
    assert set(reqs) <= {"fastapi", "pydantic"}, f"unexpected deploy dependencies: {reqs}"


def test_the_bundle_ships_a_verifiable_ledger_pair():
    """A deployed build has no runs/ directory, so the chains it walks must travel with it."""
    ledgers = sorted((APP / "web" / "public" / "data" / "ledgers").glob("*.jsonl"))
    names = [p.name for p in ledgers]
    assert any(not n.endswith(".tampered.jsonl") for n in names), "no intact ledger shipped"
    assert any(n.endswith(".tampered.jsonl") for n in names), "no tampered ledger shipped"


# --------------------------------------------------------------------------------------------
# The demo is one page plus the rubric. A reader with seven minutes should not have to find a tab.

WEB_APP = APP / "web" / "app"


def test_the_site_is_one_page_plus_the_rubric():
    routes = sorted(p.parent.name for p in WEB_APP.rglob("page.tsx"))
    assert routes == ["app", "rubric"], f"unexpected routes: {routes}"


def test_every_nav_anchor_is_a_section_that_exists():
    """A nav link to a section that was renamed scrolls nowhere and says nothing about it."""
    nav = (APP / "web" / "components" / "Nav.tsx").read_text(encoding="utf-8")
    page = (WEB_APP / "page.tsx").read_text(encoding="utf-8")
    linked = set(re.findall(r'\{\s*id:\s*"([a-z]+)"', nav))
    rendered = set(re.findall(r'\n\s+id="([a-z]+)"', page))
    assert linked, "the nav lists no sections"
    assert linked <= rendered, f"nav links to missing sections: {sorted(linked - rendered)}"


def test_the_page_renders_the_sections_that_explain_the_numbers():
    """These four are the ask: the flow, the knowledge base, the retrieval, and the arithmetic."""
    page = (WEB_APP / "page.tsx").read_text(encoding="utf-8")
    for component in ("<Flow", "<KnowledgeBase", "<Retrieval", "<TraceWalk", "<Derivations"):
        assert component in page, f"{component} is not on the page"
