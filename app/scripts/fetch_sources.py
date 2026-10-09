#!/usr/bin/env python3
"""Fetch, hash and completeness-check the primary source PDFs. Y.3172 node: SRC.

    python app/scripts/fetch_sources.py              # fetch anything missing, verify everything held
    python app/scripts/fetch_sources.py --verify     # verify what is on disk; fetch nothing
    python app/scripts/fetch_sources.py --force      # re-fetch even if the file is present

WHY VERIFICATION IS THE POINT, NOT THE DOWNLOAD

A PDF that returns HTTP 200 and has a text layer can still be the wrong document, a partial
extract, or two documents spliced together. All three happened the first time this manifest was
run, and one of them would have produced a confidently FALSE finding: a copy of the Telecom
Cyber Security Rules containing only rules 4-8 yields zero hits for "authenticate", which looks
exactly like the evidence of absence our property P2 depends on -- while being missing most of
the instrument.

So every source declares `must_contain` strings that only the real instrument carries, and the
script refuses to mark a document verified unless its extracted text carries all of them. A
document whose checks fail is reported, never silently used.

Hashes: on first fetch the sha256 is recorded into the manifest if absent. On every later run a
changed hash is an ERROR, not an update -- a gazette PDF that changes under a stable URL is
either a re-notification or a different document, and both need a human.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data/sources/MANIFEST.yaml"
RAW = ROOT / "kb_raw"
REPORT = ROOT / "docs/source_manifest.html"

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, dest: Path, timeout: int = 90) -> tuple[bool, str]:
    """curl the URL to dest. Returns (ok, message). Refuses anything that is not a PDF."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    proc = subprocess.run(
        ["curl", "-sS", "-L", "-m", str(timeout), "--retry", "2", "-o", str(tmp),
         "-w", "%{http_code}", url],
        capture_output=True, text=True)
    code = (proc.stdout or "").strip()
    if not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return False, f"http {code}: empty response"
    if tmp.open("rb").read(4) != b"%PDF":
        tmp.unlink(missing_ok=True)
        return False, f"http {code}: response is not a PDF"
    tmp.replace(dest)
    return True, f"http {code}, {dest.stat().st_size} bytes"


def extract(path: Path) -> tuple[str, int]:
    """Full text and page count. A non-PDF is read as text and counts as a single page."""
    if path.suffix.lower() != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace"), 1
    proc = subprocess.run(["pdftotext", "-q", str(path), "-"],
                          capture_output=True, text=True, check=False)
    text = proc.stdout or ""
    return text, text.count("\f") + 1 if text else 0


def source_path(source: dict) -> Path:
    """Where this source actually lives: a repo-relative `local_path`, else kb_raw/<id>.pdf."""
    local = source.get("local_path")
    return (ROOT / local) if local else (RAW / f"{source['id']}.pdf")


def check(source: dict, path: Path) -> dict:
    """Run every declared check against the file on disk. Returns a result dict."""
    result = {"id": source["id"], "problems": [], "notes": [], "ok": False}
    if not path.exists():
        result["problems"].append(f"file not present at {path}")
        return result

    digest = sha256_file(path)
    result["sha256"] = digest
    declared = source.get("sha256")
    if declared and declared != digest:
        result["problems"].append(
            f"sha256 CHANGED: manifest {declared[:16]}… file {digest[:16]}… — a stable URL "
            f"serving different bytes needs a human, not an auto-update")

    text, pages = extract(path)
    result["pages"] = pages
    result["chars"] = len(text)
    if path.suffix.lower() == ".pdf" and len(text) < 50 * max(pages, 1):
        result["problems"].append(f"only {len(text)} chars over {pages} pages — likely a scan; "
                                  f"OCR needed before this can be ingested")
    if source.get("pages") and pages != source["pages"]:
        result["problems"].append(f"page count {pages}, manifest says {source['pages']}")

    # Collapse all runs of whitespace before matching. A gazette title wraps mid-phrase
    # ("Mandatory Disaster Response\nInitiative"), and the fix is to normalise, not to shorten
    # the required string until it happens to fit on one line.
    flat = re.sub(r"\s+", " ", text).lower()
    missing = [s for s in source.get("must_contain", [])
               if re.sub(r"\s+", " ", s).lower() not in flat]
    if missing:
        result["problems"].append(f"missing required text: {missing}")
    result["must_contain_ok"] = len(source.get("must_contain", [])) - len(missing)
    result["must_contain_n"] = len(source.get("must_contain", []))

    deva = sum(1 for line in text.splitlines() if DEVANAGARI.search(line))
    result["devanagari_lines"] = deva
    if deva and not source.get("bilingual"):
        result["notes"].append(f"{deva} Devanagari lines but manifest does not mark it bilingual")
    if source.get("bilingual") and not deva:
        result["notes"].append("marked bilingual but no Devanagari found")

    result["ok"] = not result["problems"]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="verify what is on disk; fetch nothing")
    ap.add_argument("--force", action="store_true", help="re-fetch even when present")
    ap.add_argument("--only", nargs="*", help="limit to these source ids")
    args = ap.parse_args()

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    sources = [s for s in manifest["sources"] if not args.only or s["id"] in args.only]
    results: list[dict] = []

    for source in sources:
        sid, status = source["id"], source.get("status", "wanted")
        path = source_path(source)

        if status == "wanted" and not source.get("url"):
            print(f"WANT   {sid:20s} no URL in the manifest — obtain it by hand:")
            for where in source.get("wanted_from", []):
                print(f"       {where}")
            results.append({"id": sid, "status": "wanted", "ok": False, "problems": [],
                            "notes": [source.get("blocks") or ""]})
            continue

        if (source.get("url") and not source.get("local_path")
                and (args.force or not path.exists()) and not args.verify):
            ok, msg = fetch(source["url"], path)
            print(f"{'FETCH ' if ok else 'FAIL  '}{sid:20s} {msg}")
            if not ok:
                results.append({"id": sid, "status": "fetch_failed", "ok": False,
                                "problems": [msg], "notes": []})
                continue

        res = check(source, path)
        res["status"] = status
        results.append(res)
        mark = "OK    " if res["ok"] else ("PARTIAL" if status == "partial" else "PROBLEM")
        print(f"{mark:6s} {sid:20s} {res.get('pages', 0)}p  "
              f"{res.get('must_contain_ok', 0)}/{res.get('must_contain_n', 0)} required strings  "
              f"sha {res.get('sha256', '')[:12]}…")
        for p in res["problems"]:
            print(f"       ! {p}")
        for n in res["notes"]:
            if n:
                print(f"       · {n}")

    held = [r for r in results if r.get("ok")]
    print(f"\n{len(held)}/{len(results)} sources verified and usable")
    blocked = [s for s in sources if s.get("status") in ("partial", "wanted")]
    if blocked:
        print(f"{len(blocked)} still blocking a finding:")
        for s in blocked:
            print(f"  {s['id']:20s} feeds {s.get('feeds', [])} — {s.get('status')}")
    return 0 if all(r.get("ok") or r.get("status") in ("partial", "wanted") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
