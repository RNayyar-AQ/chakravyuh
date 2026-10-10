"""Read-only HTTP tier over the artefacts. Y.3172 node: SINK."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.audit.ledger import verify

DATA = ROOT / "app" / "web" / "public" / "data"
RUNS = ROOT / "runs"
OUTPUTS = ROOT / "outputs"
# Ledgers shipped inside the committed bundle. A serverless deployment has no runs/ directory,
# so this is the only chain it can walk -- and because it is the same file locally, the endpoint
# answers the same way in both places.
SHIPPED = DATA / "ledgers"

PACKS = ROOT / "data" / "packs"
NARRATE = ROOT / "app" / "scripts" / "narrate_run.py"
CLAUSE_DB = ROOT / "data" / "clauses" / "clauses.sqlite"

REBUILD = "python app/scripts/showcase.py --fast && python app/scripts/export_web.py"

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# One narrated run at a time. The script writes a ledger to a path derived from its inputs, so
# two concurrent runs of the same pack would write the same file -- the lock is correctness,
# not politeness.
_narrating = threading.Lock()

app = FastAPI(
    title="CHAKRAVYUH API",
    version="0.1.0",
    description="Read-only access to artefacts the simulator produced. Decides nothing.",
)

# `app/dev.py` steps to the next free port when 3000 is held, so pinning the origin to :3000
# would silently break the buttons on exactly the machine that already had something running.
# The regex still admits loopback only, and the server itself binds to 127.0.0.1.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):(30[0-2][0-9])$",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _require(path: Path) -> Path:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{path.name} has not been generated. Run: {REBUILD}")
    return path


def narration_blocked() -> str | None:
    """Why a narrated run cannot be started here, or None when it can."""
    if os.environ.get("VERCEL"):
        return ("narration executes the simulator; this read-only serverless deployment cannot. "
                "Clone the repo and run `make dev`.")
    if not NARRATE.exists():
        return f"{NARRATE.relative_to(ROOT)} is missing from this deployment"
    if not CLAUSE_DB.exists():
        return "the clause store has not been built. Run: python app/scripts/build_kb.py"
    return None


@app.get("/api/health")
def health() -> dict:
    """Whether the artefacts this API serves exist, and how old they are."""
    bundle = DATA / "bundle.json"
    ledgers = sorted(RUNS.glob("*.jsonl"))
    return {
        "status": "ready" if bundle.exists() else "no_artefacts",
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bundle_present": bundle.exists(),
        "bundle_fingerprint": (
            json.loads(bundle.read_text()).get("fingerprint") if bundle.exists() else None
        ),
        "ledgers_on_disk": len(ledgers),
        "rebuild_command": REBUILD,
        "narration": {
            "available": narration_blocked() is None,
            "reason": narration_blocked(),
            "packs": sorted(p.stem for p in PACKS.glob("*.yaml")),
        },
    }


@app.get("/api/bundle")
def bundle() -> FileResponse:
    """The whole artefact bundle, exactly as scripts/export_web.py wrote it."""
    return FileResponse(_require(DATA / "bundle.json"), media_type="application/json")


@app.get("/api/timeline/{pack_id}")
def timeline(pack_id: str) -> FileResponse:
    """One run's condensed ledger. `pack_id` is validated against what is on disk, not trusted."""
    available = sorted(p.stem.split(".", 1)[1] for p in DATA.glob("timeline.*.json"))
    if pack_id not in available:
        raise HTTPException(status_code=404, detail=f"unknown pack {pack_id!r}; have {available}")
    return FileResponse(DATA / f"timeline.{pack_id}.json", media_type="application/json")


@app.post("/api/verify")
def verify_ledgers() -> dict:
    """Re-walk every hash chain on disk, right now."""
    seen: dict[str, Path] = {}
    for directory in (SHIPPED, RUNS, OUTPUTS / "tamper"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.jsonl")):
            seen.setdefault(path.stem, path)

    results = []
    for run_id, path in sorted(seen.items()):
        ok, message = verify(path)
        results.append({
            "run_id": run_id,
            "tampered_copy": run_id.endswith(".tampered"),
            "verified": ok,
            "message": message,
        })
    if not results:
        raise HTTPException(status_code=503, detail=f"no ledgers on disk. Run: {REBUILD}")
    intact = [r for r in results if r["verified"]]
    return {
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chains_checked": len(results),
        "scope": "bundled" if not RUNS.is_dir() else "bundled + local runs/",
        "chains_intact": len(intact),
        "results": results,
    }


class NarrateRequest(BaseModel):
    """What to narrate. `pack` is checked against the packs on disk, not trusted."""
    pack: str = "india_current"
    full: bool = False
    skip_retrieval: bool = False


@app.post("/api/narrate")
def narrate(req: NarrateRequest) -> dict:
    """Run the simulator and narrate it, line by line, into the terminal running this server.

    This is the one endpoint that is not read-only: it executes `app/scripts/narrate_run.py`,
    which runs the real pipeline and then reads back the ledger that run wrote. Output is
    streamed to this process's stdout as it arrives -- so the terminal tells the story live --
    and returned with the escape codes stripped so a browser can show the same lines.
    """
    blocked = narration_blocked()
    if blocked:
        raise HTTPException(status_code=503, detail=blocked)

    available = sorted(p.stem for p in PACKS.glob("*.yaml"))
    if req.pack not in available:
        raise HTTPException(status_code=404,
                            detail=f"unknown pack {req.pack!r}; have {available}")

    if not _narrating.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="a narrated run is already in progress")

    cmd = [sys.executable, str(NARRATE), "--pack", req.pack, "--color", "always"]
    if req.full:
        cmd.append("--full")
    if req.skip_retrieval:
        cmd.append("--skip-retrieval")

    started = time.perf_counter()
    lines: list[str] = []
    try:
        print(f"\n>>> /api/narrate pack={req.pack} full={req.full} "
              f"-- running {' '.join(cmd[1:])}\n", flush=True)
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            print(line, flush=True)          # the terminal running `make dev`
            lines.append(ANSI.sub("", line))  # the browser
        code = proc.wait()
    finally:
        _narrating.release()

    seconds = round(time.perf_counter() - started, 3)
    print(f"\n<<< /api/narrate finished: exit {code} in {seconds}s, {len(lines)} lines\n",
          flush=True)
    return {
        "pack": req.pack,
        "exit_code": code,
        "ok": code == 0,
        "seconds": seconds,
        "line_count": len(lines),
        "command": " ".join(["python", *cmd[1:]]),
        "lines": lines,
    }
