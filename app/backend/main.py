"""Read-only HTTP tier over the artefacts. Y.3172 node: SINK."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

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

REBUILD = "python app/scripts/showcase.py --fast && python app/scripts/export_web.py"

app = FastAPI(
    title="CHAKRAVYUH API",
    version="0.1.0",
    description="Read-only access to artefacts the simulator produced. Decides nothing.",
)

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
        "bundle_fingerprint": (
            json.loads(bundle.read_text()).get("fingerprint") if bundle.exists() else None
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
