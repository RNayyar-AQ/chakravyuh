#!/usr/bin/env python3
"""Generate y3172_map.md from the @node decorators in the source. Y.3172 node: (meta)."""
from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chakravyuh
from chakravyuh.y3172 import REGISTRY, render_map

OUT = Path("docs/y3172_map.md")

OPTIONAL = {"chakravyuh.fuzz.machine": "hypothesis"}


def main() -> int:
    skipped: list[str] = []
    for mod in pkgutil.walk_packages(chakravyuh.__path__, prefix="chakravyuh."):
        try:
            importlib.import_module(mod.name)
        except ImportError as exc:
            skipped.append(f"{mod.name} ({OPTIONAL.get(mod.name, str(exc)[:60])})")

    text = render_map()
    if skipped:
        text += "\n## Modules not imported in this environment\n\n"
        text += "\n".join(f"- `{s}`" for s in skipped) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")

    counts = {node: len(entries) for node, entries in REGISTRY.items()}
    print(f"wrote {OUT}")
    print("registered entry points per node: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    empty = [k for k, v in counts.items() if v == 0]
    if empty:
        print(f"NOTE: no entry point registered for node(s) {empty}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
