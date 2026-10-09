"""Minimal failing case -> FailureCard. Y.3172 node: SINK.

Hypothesis shrinks a failure to a minimal mutation sequence; this module turns that into the
artefact the demo shows and the report cites: a card carrying the seed, the mutation list, the
violated property with its margin, the gap class, the responsible clause IDs, which packs survive
the same seed, and a replay command that actually reproduces it.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping, Optional, Sequence

from ..analysis.compare import passes_under, run_across_packs
from ..analysis.gaps import classify
from ..schemas import FailureCard, PolicyPack
from ..sim.events import Scenario
from ..sim.runner import context_for, run
from ..y3172 import node
from .mutations import apply_mutations

OUT_DIR = Path("outputs/failures")


def failure_id(pack_id: str, property_id: str, mutations: Sequence[dict]) -> str:
    """Stable id from the minimal mutation list, so the same minimal case is never double-counted."""
    canonical = json.dumps([[m.get("op"), m.get("args", {})] for m in mutations], sort_keys=True)
    digest = hashlib.sha256(f"{pack_id}|{property_id}|{canonical}".encode()).hexdigest()[:10]
    return f"F-{property_id}-{digest}"


@node("SINK")
def build_card(base: Scenario, packs: Mapping[str, PolicyPack], pack_id: str,
               property_id: str, mutations: Sequence[dict], seed: int = 0,
               runs_dir: str = "runs/failures") -> Optional[FailureCard]:
    """Re-run the minimal case, classify it, compare across packs, return the card.

    Returns None if the minimal case does not actually reproduce the failure -- a card that does
    not replay is worse than no card, so it is dropped rather than reported.
    """
    mutated = apply_mutations(base, list(mutations))
    pack = packs[pack_id]
    fid = failure_id(pack_id, property_id, mutations)

    result = run(mutated, pack, seed=seed, mutations=list(mutations), runs_dir=runs_dir,
                 run_suffix=fid)
    prop = next((p for p in result.properties if p.property_id == property_id), None)
    if prop is None or prop.passed:
        return None   # did not reproduce

    ctx = context_for(result)
    finding = classify(prop, pack, ctx["world"], ctx["gm"], mutated, result.run_id)

    across = run_across_packs(mutated, packs, seed=seed, mutations=list(mutations),
                              runs_dir=runs_dir, run_suffix=fid)
    survives = passes_under(across, property_id)

    return FailureCard(
        failure_id=fid, pack_id=pack_id, seed=seed, mutations=list(mutations),
        violated_property=property_id, margin=prop.margin,
        gap_class=finding.gap_class if finding else "policy",
        responsible_clause_ids=finding.responsible_clause_ids if finding else [],
        passes_under_packs=survives,
        replay_cmd=(f"python app/scripts/run_fuzz.py --replay {fid} "
                    f"--pack {pack_id} --scenario {base.scenario_id}"),
    )


@node("SINK")
def dedupe(cards: Sequence[FailureCard]) -> list[FailureCard]:
    """Keep one card per (property, gap class, minimal mutation set), worst margin first."""
    best: dict[str, FailureCard] = {}
    for card in cards:
        key = card.failure_id
        if key not in best or card.margin < best[key].margin:
            best[key] = card
    return sorted(best.values(), key=lambda c: (c.violated_property, c.margin))


@node("SINK")
def write_cards(cards: Sequence[FailureCard], out_dir: str | Path = OUT_DIR) -> list[Path]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    for card in cards:
        p = d / f"{card.failure_id}.json"
        p.write_text(json.dumps(card.model_dump(), indent=2, sort_keys=True), encoding="utf-8")
        paths.append(p)
    index = d / "index.json"
    index.write_text(json.dumps([c.model_dump() for c in cards], indent=2, sort_keys=True),
                     encoding="utf-8")
    paths.append(index)
    return paths


@node("SINK")
def card_markdown(card: FailureCard) -> str:
    """A failure card as the demo shows it: what broke, which law, and how to reproduce it."""
    survives = ", ".join(card.passes_under_packs) or "no pack in this set"
    muts = "\n".join(
        f"  {i + 1}. {m.get('op')}("
        + ", ".join(f"{k}={v}" for k, v in sorted((m.get("args") or {}).items())) + ")"
        for i, m in enumerate(card.mutations)) or "  (none: the base scenario fails)"
    return (
        f"### {card.failure_id} - {card.violated_property} violated under `{card.pack_id}`\n\n"
        f"- **Gap class:** {card.gap_class}\n"
        f"- **Margin:** {card.margin} (negative = violated)\n"
        f"- **Responsible clauses:** {', '.join(card.responsible_clause_ids) or 'n/a'}\n"
        f"- **Same seed passes under:** {survives}\n"
        f"- **Minimal mutation sequence:**\n{muts}\n"
        f"- **Replay:** `{card.replay_cmd}`\n"
    )
