#!/usr/bin/env python3
"""Check every clause's source_url actually resolves. Y.3172 node: SRC.

WHY THIS EXISTS
---------------
The clause corpus was written from a language model's own knowledge. The provision summaries were
not transcribed from the instruments, and the URLs were not copied from a browser -- they were
recalled. Recalled URLs rot and recalled URLs are invented, so "has a source_url" is worth nothing
on its own: the question is whether that URL is real and whether it holds the provision claimed.

This script answers the first half mechanically. The second half -- does the page actually contain
the section cited -- needs a human, and `verbatim_status` tracks it.

  python app/scripts/check_sources.py              # check and report
  python app/scripts/check_sources.py --strict     # exit 1 if any URL is dead (for CI)

Exit codes: 0 all reachable (or only blocked), 1 at least one dead URL and --strict given.
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.kb.ingest import SEED_PATH

DOCS = Path("docs")
DATA = Path("outputs")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 403/429 usually means bot protection, not a dead link. Reported separately so a WAF does not
# masquerade as an invented URL -- and so a real 404 is never excused as "probably blocked".
BLOCKED_CODES = {401, 403, 405, 429}


def check(url: str, timeout: int = 15) -> dict:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return {"state": "reachable", "code": resp.status,
                    "content_type": (resp.headers.get("Content-Type") or "?").split(";")[0]}
    except urllib.error.HTTPError as exc:
        state = "blocked" if exc.code in BLOCKED_CODES else "dead"
        return {"state": state, "code": exc.code, "content_type": ""}
    except Exception as exc:
        # A timeout is NOT evidence of a dead URL. Some sites are simply slow or redirect through
        # several hops; curl resolves these fine. Conflating "slow" with "invented" would overstate
        # the corpus's problems, which is the opposite of the point of this check.
        name = type(exc).__name__
        state = "timeout" if ("Timeout" in name or "timed out" in str(exc).lower()) else "unreachable"
        return {"state": state, "code": 0, "content_type": "",
                "error": f"{name}: {exc}"[:120]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed-path", default=str(SEED_PATH))
    ap.add_argument("--strict", action="store_true", help="exit 1 if any URL is dead")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--offline", action="store_true",
                    help="skip the network and report the last saved result, if any")
    args = ap.parse_args()

    # Read the STORE, not just the seed file: the gazette-derived records are the majority of the
    # corpus and their eGazette URLs need checking too. Falls back to the seed if the store is
    # not built yet.
    try:
        from chakravyuh.kb.clause_store import ClauseStore
        store = ClauseStore()
        rows = [{"clause_id": c.clause_id, "instrument": c.instrument, "section": c.section,
                 "source_url": c.source_url, "provenance": c.provenance,
                 "verbatim_status": c.verbatim_status} for c in store.all_clauses()]
        store.close()
        if not rows:
            raise RuntimeError("empty store")
        print(f"checking {len(rows)} clause records from the clause store")
    except Exception:
        rows = [json.loads(l) for l in
                Path(args.seed_path).read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"clause store unavailable; checking {len(rows)} seed records "
              f"(run app/scripts/build_kb.py for full coverage)")
    saved = DATA / "source_check.json"
    if args.offline:
        if not saved.exists():
            print("no saved result to report; run without --offline once", file=sys.stderr)
            return 2
        data = json.loads(saved.read_text(encoding="utf-8"))
    else:
        socket.setdefaulttimeout(args.timeout + 5)
        per_url = {}
        for url in sorted({r["source_url"] for r in rows}):
            per_url[url] = check(url, args.timeout)
            s = per_url[url]
            print(f"  {s['state']:12s} {s['code'] or '-':>4}  {url}")
        data = {"per_url": per_url, "records": len(rows)}

    per_url = data["per_url"]
    # Attribute each URL's state back to the clause records that depend on it.
    by_state: dict[str, list[str]] = {}
    for r in rows:
        state = per_url.get(r["source_url"], {}).get("state", "unknown")
        by_state.setdefault(state, []).append(r["clause_id"])

    url_states = Counter(v["state"] for v in per_url.values())
    data["url_states"] = dict(url_states)
    data["records_by_state"] = {k: sorted(v) for k, v in by_state.items()}

    DOCS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    saved.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    (DOCS / "source_check.md").write_text(report(rows, per_url, url_states, by_state),
                                         encoding="utf-8")

    dead = url_states.get("dead", 0) + url_states.get("unreachable", 0)
    n_rec = len(by_state.get("dead", [])) + len(by_state.get("unreachable", []))
    print(f"\n{url_states.get('reachable', 0)}/{len(per_url)} URLs reachable, "
          f"{url_states.get('blocked', 0)} blocked, {url_states.get('timeout', 0)} timed out, "
          f"{dead} dead")
    if dead:
        print(f"{n_rec}/{len(rows)} clause records cite a URL that does not resolve.")
    print(f"wrote {DOCS / 'source_check.md'}")
    return 1 if (dead and args.strict) else 0


def report(rows, per_url, url_states, by_state) -> str:
    n = len(rows)
    dead_recs = sorted(by_state.get("dead", []) + by_state.get("unreachable", []))
    lines = [
        "# Source URL check (generated by app/scripts/check_sources.py -- do not edit)",
        "",
        "## What this checks, and what it does not",
        "",
        "**Checks:** does each `source_url` resolve over HTTP.",
        "",
        "**Does not check:** whether the page holds the section cited, or whether the summary in",
        "`text_verbatim` is a faithful statement of that provision. A reachable URL is necessary and",
        "nowhere near sufficient.",
        "",
        "**Provenance you must know when reading any number below:** the clause corpus was written",
        "from a language model's own knowledge. Provision summaries were not transcribed from the",
        "instruments, and these URLs were recalled rather than copied. That is why this check exists.",
        "",
        "## URLs",
        "",
        "| State | URLs | Meaning |",
        "|---|---|---|",
        f"| reachable | {url_states.get('reachable', 0)} | HTTP 200 |",
        f"| blocked | {url_states.get('blocked', 0)} | 401/403/405/429 -- bot protection, not "
        f"necessarily wrong; verify in a browser |",
        f"| timeout | {url_states.get('timeout', 0)} | slow or multi-hop redirect; NOT evidence "
        f"the URL is wrong -- re-check with curl or a browser |",
        f"| dead | {url_states.get('dead', 0)} | 404 or similar -- **the URL is wrong** |",
        f"| unreachable | {url_states.get('unreachable', 0)} | DNS or TLS failure |",
        "",
        "## Clause records affected",
        "",
        "| State of cited URL | Records | Share |",
        "|---|---|---|",
    ]
    for state in ("reachable", "blocked", "timeout", "dead", "unreachable", "unknown"):
        ids = by_state.get(state, [])
        if ids:
            lines.append(f"| {state} | {len(ids)} | {100.0 * len(ids) / n:.0f}% |")
    if dead_recs:
        lines += ["", "### Records citing a URL that does not resolve",
                  "", "These must be corrected before the clause is cited anywhere:", ""]
        for cid in dead_recs:
            row = next(r for r in rows if r["clause_id"] == cid)
            prov = row.get("provenance", "?")
            lines.append(f"- `{cid}` — {row['instrument']}, {row['section']} "
                         f"_(provenance: {prov})_  \n"
                         f"  broken: <{row['source_url']}>")
        lines += ["", "A dead URL on a `gazette_pdf` record is less serious than on a summary: "
                      "its text came from a PDF whose SHA-256 is recorded, so the document is "
                      "pinned even when the link rots. A dead URL on a model-written record "
                      "means there is nothing behind the claim at all."]
    lines += ["", "## Per-URL detail", "", "| State | Code | Type | URL |", "|---|---|---|---|"]
    for url in sorted(per_url):
        s = per_url[url]
        lines.append(f"| {s['state']} | {s['code'] or '-'} | {s.get('content_type') or '-'} | {url} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
