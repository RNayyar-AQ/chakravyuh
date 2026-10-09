"""Read-only HTTP tier over the artefacts. Y.3172 node: SINK.

WHAT THIS IS NOT
    Not a place where anything is decided. It serves files the pipeline already wrote and runs
    verification that is already implemented in `chakravyuh.audit.ledger`. It computes no margin,
    no verdict and no confidence, and it cannot write to the ledger. Everything here would still
    be true if this process were switched off -- which is the point: the frontend's production
    build reads the same artefacts straight off disk and needs no server at all.

WHY IT EXISTS ANYWAY
    `make dev` runs the frontend against a live backend, so the demo can re-verify the hash chains
    on request instead of showing a verification result baked in at build time. A judge asking
    "is that still true right now?" gets the answer from the chain, not from a cached number.

    uvicorn app.api.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[2]           # repo root: data/, outputs/, runs/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # app/: the chakravyuh package

from chakravyuh.audit.ledger import verify

DATA = ROOT / "app" / "web" / "public" / "data"
RUNS = ROOT / "runs"
OUTPUTS = ROOT / "outputs"

REBUILD = "python app/scripts/showcase.py --fast && python app/scripts/export_web.py"

app = FastAPI(
    title="CHAKRAVYUH API",
    version="0.1.0",
    description="Read-only access to artefacts the simulator produced. Decides nothing.",
)

# The frontend dev server is a different origin. Locked to localhost: this tier is a development
# and demo convenience, never something to expose.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _require(path: Path) -> Path:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{path.name} has not been generated. Run: {REBUILD}")
    return path


@app.get("/api/health")
def health() -> dict:
    """Whether the artefacts this API serves exist, and how old they are."""
    bundle = DATA / "bundle.json"
    ledgers = sorted(RUNS.glob("*.jsonl"))
    return {
        "status": "ready" if bundle.exists() else "no_artefacts",
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bundle_present": bundle.exists(),
        "bundle_generated_utc": (
            json.loads(bundle.read_text()).get("generated_utc") if bundle.exists() else None
        ),
        "ledgers_on_disk": len(ledgers),
        "rebuild_command": REBUILD,
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
    """Re-walk every hash chain on disk, right now.

    This is the one endpoint that does work rather than serving a file, and it is still only
    reading: `verify` recomputes sha256(prev | seq | t | kind | canonical_json(payload)) for each
    entry and reports the first sequence number where the chain breaks.
    """
    results = []
    for path in sorted(RUNS.glob("*.jsonl")) + sorted((OUTPUTS / "tamper").glob("*.jsonl")):
        ok, message = verify(path)
        results.append({
            "run_id": path.stem,
            "tampered_copy": path.parent.name == "tamper",
            "verified": ok,
            "message": message,
        })
    if not results:
        raise HTTPException(status_code=503, detail=f"no ledgers on disk. Run: {REBUILD}")
    intact = [r for r in results if r["verified"]]
    return {
        "checked_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "chains_checked": len(results),
        "chains_intact": len(intact),
        "results": results,
    }
