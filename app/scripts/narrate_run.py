#!/usr/bin/env python3
"""Narrate one full run in plain English: retrieval -> agents -> policy engine -> Game Master.

This is the explainer path. It runs the real pipeline -- the same retriever, the same compiled
pack, the same simulation -- and then reads back the hash-chained ledger that run wrote, saying
what each entry means. Every number printed is read from an artefact on disk, never recomputed
for display, so what you see is what the audit trail holds.

    python app/scripts/narrate_run.py                      # india_current, the story view
    python app/scripts/narrate_run.py --pack fcc_mdri      # the same cyclone, US-shaped rules
    python app/scripts/narrate_run.py --full               # every proposal, nothing collapsed
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.audit.ledger import read as read_ledger, verify
from chakravyuh.kb.clause_store import ClauseStore
from chakravyuh.kb.ingest import load_chunks
from chakravyuh.kb.retrieve import Retriever
from chakravyuh.narrate import Narrator
from chakravyuh.policy.compiler import compile_pack
from chakravyuh.schemas import sha256_text
from chakravyuh.sim.events import load_scenario
from chakravyuh.sim.runner import run

PACKS_DIR = Path("data/packs")
SCENARIO = "data/scenarios/amphan_2020.yaml"

# What a reader of the policy pack would actually go looking for. Each one is answered by
# retrieval over the clause store, and the answer is shown with its digest.
QUESTIONS = [
    "Who may order suspension of telecom services and what must the order contain?",
    "Must a cyclone alert be issued in the local language of the affected district?",
    "Is there any obligation to enable disaster roaming across operators?",
]

# Proposals these roles repeat on nearly every tick. Shown in full once, then counted.
COLLAPSE_AFTER = 1


def clock_for(epoch_iso: str | None, t: int) -> str:
    if not epoch_iso:
        return f"{t // 60:02d}h{t % 60:02d}"
    try:
        base = datetime.fromisoformat(epoch_iso.replace("Z", "+00:00"))
    except ValueError:
        return f"{t // 60:02d}h{t % 60:02d}"
    return (base + timedelta(minutes=t)).strftime("%d %b %H:%M")


# --------------------------------------------------------------------------- stage 1: the KB

def narrate_kb(n: Narrator, store: ClauseStore) -> dict:
    n.stage("KNOWLEDGE BASE",
            "157 clause records, each one the text of an instrument plus the digest of that text.")
    clauses = store.all_clauses()
    report = store.integrity_report()
    chunks = load_chunks()

    n.step("C", f"clause store  {len(clauses)} clauses from "
                f"{len({c.instrument for c in clauses})} instruments, "
                f"{len({c.jurisdiction for c in clauses})} jurisdictions")
    by_prov: dict[str, int] = {}
    for c in clauses:
        by_prov[c.provenance] = by_prov.get(c.provenance, 0) + 1
    for prov, count in sorted(by_prov.items(), key=lambda kv: -kv[1]):
        real = prov.startswith("gazette")
        mark = n.good("the instrument's own words") if real else n.warn("a summary, not the text")
        n.detail(f"{count:>4}  {prov:<26} {mark}")

    n.step("C", f"chunk index   {len(chunks)} retrievable chunks "
                f"(one per clause; only clauses over 900 chars are split)")
    n.step("C", f"integrity     {report['hash_matching']}/{report['total']} clause records "
                f"still hash to their recorded digest; "
                f"{report['quotable']} are quotable primary text")
    n.faint("every clause is stored with sha256(text_verbatim); a drifted source changes the digest")
    return {"clauses": len(clauses), "chunks": len(chunks)}


# ----------------------------------------------------------------- stage 2: retrieval + citation

def narrate_retrieval(n: Narrator, store: ClauseStore, questions: list[str], k: int) -> None:
    n.stage("RETRIEVAL",
            "BM25 and vector search over the chunks, fused with reciprocal rank fusion (k=60).")
    retriever = Retriever(mode="hybrid")
    vector = retriever.chroma_ready()
    n.step("PP", f"lexical  BM25 over {len(retriever.chunks)} chunks "
                 f"(tokeniser keeps `s.20(2)` as one token)")
    n.step("PP", "vector   " + ("ChromaDB, cosine, all-MiniLM-L6-v2 (384 dims), collections "
                                "kb_main / kb_decisions / kb_framework"
                                if vector else n.warn("ChromaDB unavailable; lexical only")))
    n.step("PP", "fusion   RRF over both rankings, score(chunk) = Σ 1/(60 + rank)")

    for qi, question in enumerate(questions, start=1):
        n.blank()
        n.write(f"  {n.good(f'Q{qi}')}  {question}")
        # The same two rankings `search` fuses, so the fused score can be read back to its parts.
        pool = 4 * k
        bm25_rank = {h.chunk_id: i for i, h in enumerate(retriever.search_bm25(question, pool), 1)}
        vec_rank = {h.chunk_id: i for i, h in enumerate(retriever.search_vector(question, pool), 1)}
        hits = retriever.search(question, k=k)
        if not hits:
            n.detail(n.warn("no chunk retrieved"))
            continue
        for rank, hit in enumerate(hits, start=1):
            clause = store.try_get(hit.clause_id)
            n.blank()
            n.write(f"      {n.good(f'#{rank}')}  {hit.clause_id}"
                    f"   {n.muted(f'rrf={hit.score:.6f}  chunk {hit.chunk_id}')}")
            n.detail(f"{hit.instrument} — {hit.section}")
            parts = []
            for label, table in (("BM25", bm25_rank), ("vector", vec_rank)):
                r = table.get(hit.chunk_id)
                parts.append(f"{label} #{r} → 1/(60+{r}) = {1 / (60 + r):.6f}" if r
                             else f"{label} did not return it")
            n.detail("fusion    " + "  +  ".join(parts) + f"  =  {hit.score:.6f}")
            if clause is None:
                n.detail(n.bad("not in the clause store"))
                continue
            live = sha256_text(clause.text_verbatim)
            ok = live == clause.sha256
            n.detail(f"sha256    {n.hash_(clause.sha256, 24)}  "
                     + (n.good("recomputed now, matches") if ok
                        else n.bad(f"MISMATCH, text now hashes to {live[:24]}…")))
            status = clause.verbatim_status
            n.detail("provenance " + (n.good(f"{clause.provenance} / {status}")
                                      if clause.is_real_text
                                      else n.warn(f"{clause.provenance} / {status} "
                                                  f"— summary, not quotable")))
            n.detail(f"source    {clause.source_url}")
            n.quote(clause.text_verbatim)


# ------------------------------------------------------------------- stage 3: compiling the pack

def narrate_pack(n: Narrator, pack_path: Path, store: ClauseStore):
    n.stage("POLICY PACK",
            "Clause text is not executable. A pack turns selected clauses into deontic rules.")
    pack = compile_pack(pack_path, store=store, strict_clauses=True)
    effects: dict[str, int] = {}
    for r in pack.rules:
        effects[r.effect] = effects.get(r.effect, 0) + 1
    cited = sorted({cid for r in pack.rules for cid in r.clause_ids})

    n.step("PP", f"compiled  {pack.pack_id} v{pack.version} ({pack.jurisdiction}), "
                 f"mode={pack.mode}")
    n.detail(f"{len(pack.rules)} rules: "
             + ", ".join(f"{v} {k}" for k, v in sorted(effects.items())))
    n.detail(f"citing {len(cited)} distinct clauses — "
             + n.good("compilation refuses any rule that cites no clause, "
                      "or a clause whose hash drifted"))
    auth = [r for r in pack.rules if r.requires_authenticated_order]
    n.detail(f"{len(auth)} rule(s) require an authenticated order: "
             + (", ".join(r.rule_id for r in auth) if auth
                else n.bad("none — nothing in this pack checks who sent an order")))

    n.blank()
    n.faint("    a rule, in full:", 4)
    sample = next((r for r in pack.rules if r.rule_id.endswith("ORDER_SUSPENSION")), pack.rules[0])
    n.kv("rule_id", sample.rule_id, indent=6)
    n.kv("actor / action", f"{sample.actor_role} may {sample.action_type}", indent=6)
    n.kv("effect", sample.effect, indent=6)
    n.kv("conditions", str(sample.conditions), indent=6)
    n.kv("reversible", str(sample.reversible), indent=6)
    n.kv("requires auth order", str(sample.requires_authenticated_order), indent=6)
    for cid in sample.clause_ids:
        c = store.try_get(cid)
        n.kv("cites", f"{cid}  {n.hash_(c.sha256) if c else n.bad('missing')}", indent=6)
    return pack


# ----------------------------------------------------------------------- stage 4: the scenario

def narrate_scenario(n: Narrator, scenario) -> None:
    n.stage("SCENARIO",
            "The world the agents will see. Timings are the IMD release's own; cells are ours.")
    real = [e for e in scenario.events if not e.synthetic]
    synth = [e for e in scenario.events if e.synthetic]
    n.step("SRC", f"{scenario.scenario_id} — {scenario.title}")
    n.detail(f"horizon {scenario.horizon_min} min at {scenario.tick_min}-min ticks "
             f"= {scenario.horizon_min // scenario.tick_min} ticks")
    n.detail(f"{len(scenario.areas)} areas, "
             f"{sum(scenario.cells_per_area.values())} cells, "
             f"{len(scenario.cross_border_areas)} cross-border")
    n.detail(f"{len(real)} events from the source release, "
             + n.warn(f"{len(synth)} constructed by us (synthetic: true)"))
    n.blank()
    for e in sorted(scenario.events, key=lambda e: (e.t_minutes, e.event_id)):
        tag = n.warn("SYNTHETIC") if e.synthetic else n.good("REAL     ")
        forged = n.bad("  ← authentic=False: no authority issued this") if not e.authentic else ""
        n.write(f"      T+{e.t_minutes:<6d} {clock_for(scenario.epoch_iso, e.t_minutes):<13}"
                f" {tag}  {e.type:<18} {e.area or '-':<12} {e.event_id}{forged}")


# ------------------------------------------------- stage 5: agents, engine and GM, from the ledger

def pinned_proposals(ledger_path: str) -> set[str]:
    """Proposal ids a reader must not miss: the forged chain, and anything a human had to clear.

    The collapse rule hides a role's repeated proposals, and the forged suspension happens to be
    the TSP's second SUSPEND_SERVICE. Without this pass the one finding the demo exists to show
    would be the one line collapsed away.
    """
    keep: set[str] = set()
    for entry in read_ledger(ledger_path):
        p = entry.payload
        if entry.kind == "VERDICT" and p.get("decision") == "NEEDS_HUMAN":
            keep.add(p["proposal_id"])
        elif entry.kind == "EFFECT" and (
                p.get("trigger_authentic") is False
                or p.get("status") in ("held_for_human", "deferred_for_approval_delay")):
            keep.add(p.get("proposal_id", ""))
    keep.discard("")
    return keep


def world_change_lines(changed: dict, width: int = 96) -> list[str]:
    """One `world <- key = value` line per changed key, long lists counted rather than dumped."""
    out: list[str] = []
    for key, value in sorted(changed.items()):
        if isinstance(value, list) and len(value) > 4:
            out.append(f"world ← {key} = {len(value)} items: {value[:3]} …")
            continue
        text = f"world ← {key} = {value}"
        out.append(text if len(text) <= width else text[: width - 1] + "…")
    return out



def narrate_run(n: Narrator, result, scenario, pack, store: ClauseStore, full: bool) -> dict:
    n.stage("THE RUN — agent, policy engine, Game Master",
            "Read back from the ledger the run just wrote. Order is the order it happened in.")
    n.step("D", f"run_id    {result.run_id}")
    n.detail(f"{result.tick_count} ticks in {result.wall_seconds}s, "
             f"{result.llm_calls} LLM calls "
             + n.good("(zero — every decision below is deterministic code)"))
    n.blank()
    n.faint("    [M] an agent proposes · [P] the policy engine decides · "
            "[D] the Game Master is the only writer of world state", 4)

    sha = {c.clause_id: c.sha256 for c in store.all_clauses()}
    pinned = pinned_proposals(result.ledger_path)
    if pinned:
        n.detail(f"{len(pinned)} proposal(s) carry a finding and are never collapsed, "
                 f"however often their role repeats itself")
    proposals: dict[str, dict] = {}
    repeats: dict[tuple, int] = {}
    shown: dict[tuple, int] = {}
    counts = {"proposals": 0, "allow": 0, "block": 0, "human": 0, "effects": 0, "forged": 0}
    current_t = None

    def open_tick(t: int) -> None:
        nonlocal current_t
        if t != current_t:
            n.tick(t, clock_for(scenario.epoch_iso, t))
            current_t = t

    for entry in read_ledger(result.ledger_path):
        p, t = entry.payload, entry.t_minutes

        if entry.kind == "EVENT" and p.get("kind") not in ("RUN_HEADER", "RUN_FOOTER"):
            ev = p.get("event", {})
            open_tick(t)
            auth = "" if ev.get("authentic", True) else n.bad("  authentic=False (forged)")
            n.step("SRC", f"EVENT      {ev.get('event_id')}  {ev.get('type')}  "
                          f"area={ev.get('area') or '-'}{auth}")
            for line in world_change_lines(p.get("world_change") or {}):
                n.faint(line)

        elif entry.kind == "DELIVERY" and full:
            open_tick(t)
            n.step("D", f"DELIVERY   {p.get('event_id')} → {p.get('role')}  "
                        f"(sent T+{p.get('sent_t', '?')}, arrives T+{p.get('arrives_t', t)})")

        elif entry.kind == "PROPOSAL":
            counts["proposals"] += 1
            proposals[p["proposal_id"]] = p
            key = (p["actor_role"], p["action_type"])
            shown[key] = shown.get(key, 0) + 1
            if not full and shown[key] > COLLAPSE_AFTER and p["proposal_id"] not in pinned:
                repeats[key] = repeats.get(key, 0) + 1
                continue
            open_tick(t)
            n.step("M", f"AGENT      {n.good(p['actor_role'])} proposes "
                        f"{n.good(p['action_type'])}  ({p['proposal_id']})")
            n.detail(f'reasoning  "{p.get("reasoning", "")}"')
            if p.get("params"):
                n.detail(f"params     {p['params']}")
            if p.get("triggered_by_event_ids"):
                n.detail(f"because of {p['triggered_by_event_ids']}")
            n.detail(f"cites rule {p.get('cited_rule_ids') or '(none)'}")
            n.faint("the agent cites a rule. It cannot apply one — it holds no reference "
                    "to the world.")

        elif entry.kind == "VERDICT":
            d = p["decision"]
            counts[{"ALLOW": "allow", "BLOCK": "block", "NEEDS_HUMAN": "human"}[d]] += 1
            prop = proposals.get(p["proposal_id"], {})
            key = (prop.get("actor_role"), prop.get("action_type"))
            if (not full and shown.get(key, 0) > COLLAPSE_AFTER
                    and p["proposal_id"] not in pinned):
                continue
            open_tick(t)
            n.step("P", f"ENGINE     {n.decision(d)}  ← {p['proposal_id']}")
            n.detail(f"rules      {p.get('rule_ids') or '(none applied)'}")
            for cid in p.get("clause_ids", [])[:4]:
                n.detail(f"clause     {cid}  {n.hash_(sha.get(cid, '?' * 12))}")
            if len(p.get("clause_ids", [])) > 4:
                n.faint(f"… and {len(p['clause_ids']) - 4} further clause(s)")
            n.detail(f"because    {p.get('explanation', '')}")
            n.faint(f"pack mode {p.get('mode')}: a BLOCK here stops the action reaching the world")

        elif entry.kind == "EFFECT":
            kind = p.get("kind") or p.get("status") or p.get("action_type")
            if kind == "WORLD_STEP" and not full:
                continue
            prop = proposals.get(p.get("proposal_id", ""), {})
            key = (prop.get("actor_role"), prop.get("action_type"))
            forged = p.get("trigger_authentic") is False
            if forged:
                counts["forged"] += 1
            if (not full and shown.get(key, 0) > COLLAPSE_AFTER and not forged
                    and p.get("proposal_id") not in pinned):
                continue
            counts["effects"] += 1
            open_tick(t)
            if p.get("status") == "held_for_human":
                n.step("D", f"GM         {n.warn('HELD for human authorisation')}  "
                            f"{p['proposal_id']} (gate={p.get('gate_mode')})")
            elif p.get("status") == "deferred_for_approval_delay":
                n.step("D", f"GM         {n.warn('DEFERRED')} {p['proposal_id']} for "
                            f"{p.get('delay_min')} min — the pack's own approval delay, "
                            f"effective T+{p.get('effective_t')}")
            else:
                n.step("D", f"GM         {n.good('EXECUTED')}  {kind}  "
                            f"→ world state changed")
                for line in world_change_lines(
                        {k2: v2 for k2, v2 in p.items()
                         if k2 not in ("proposal_id", "rule_ids", "clause_ids",
                                       "trigger_authentic", "action_type", "kind", "status")}):
                    n.faint(line)
            if forged:
                n.detail(n.bad("⚠ this action was driven by an order that failed authentication, "
                               "and it still executed"))

        elif entry.kind == "PROPERTY":
            pass  # reported in its own stage

    if repeats:
        n.blank()
        n.rule()
        n.write(n.muted("  repeats collapsed")
                + n.dim("  (the twins re-propose every tick; --full shows each one)"))
        for (role, action), count in sorted(repeats.items(), key=lambda kv: -kv[1]):
            n.detail(f"{count:>4}  further {role} / {action} proposals, "
                     f"identical reasoning, identical verdict", 6)
    return counts


# -------------------------------------------------------------------- stage 6: what was measured

def narrate_properties(n: Narrator, result, scenario) -> None:
    n.stage("PROPERTIES",
            "Four things an emergency response must not get wrong. Margin is signed slack.")
    for p in result.properties:
        mark = n.good("PASS") if p.passed else n.bad("FAIL")
        n.step("SINK", f"{p.property_id}  {mark}  margin {p.margin:+g} {p.unit}")
        n.detail(p.description)
        for k, v in sorted(p.detail.items()):
            text = str(v)
            n.faint(f"{k} = {text[:150]}{'…' if len(text) > 150 else ''}")
    n.blank()
    n.faint("    thresholds are illustrative, not legal standards; a margin is a distance from "
            "the threshold", 4)
    n.faint("    inside this model, not a prediction about the 2020 cyclone", 4)


# --------------------------------------------------------------------- stage 7: the audit trail

def narrate_ledger(n: Narrator, result, counts: dict) -> bool:
    n.stage("AUDIT TRAIL",
            "The ledger is hash-chained: entry n's hash covers entry n-1's hash.")
    entries = list(read_ledger(result.ledger_path))
    kinds: dict[str, int] = {}
    for e in entries:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    ok, message = verify(result.ledger_path)

    n.step("SINK", f"file      {result.ledger_path}")
    n.detail(f"{len(entries)} entries: "
             + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])))
    n.detail(f"head      {n.hash_(result.ledger_head_hash, 32)}")
    n.detail("chain     " + (n.good(f"VERIFIED — {message}") if ok else n.bad(f"BROKEN — {message}")))
    n.faint("hash(entry) = sha256(prev_hash | seq | t | kind | canonical_json(payload))")
    n.blank()
    n.step("SINK", "this run in one line")
    n.detail(f"{counts['proposals']} proposals → "
             f"{n.good(str(counts['allow']) + ' allowed')}, "
             f"{n.bad(str(counts['block']) + ' blocked')}, "
             f"{n.warn(str(counts['human']) + ' held for a human')} → "
             f"{counts['effects']} effects on the world")
    if counts["forged"]:
        was = "was" if counts["forged"] == 1 else "were"
        n.detail(n.bad(f"{counts['forged']} of those effects {was} driven by an order that "
                       f"failed authentication"))
    return ok


# ------------------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", default="india_current", help="pack id under data/packs")
    ap.add_argument("--scenario", default=SCENARIO)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--k", type=int, default=2, help="retrieval hits to show per question")
    ap.add_argument("--full", action="store_true",
                    help="show every proposal and delivery, collapsing nothing")
    ap.add_argument("--skip-retrieval", action="store_true",
                    help="skip the retrieval stage (it loads ChromaDB, which takes a few seconds)")
    ap.add_argument("--color", default="auto", choices=["auto", "always", "never"])
    args = ap.parse_args(argv)

    n = Narrator(colour=args.color)
    pack_path = PACKS_DIR / f"{args.pack}.yaml"
    if not pack_path.exists():
        print(f"no such pack {args.pack!r}; have "
              f"{sorted(p.stem for p in PACKS_DIR.glob('*.yaml'))}", file=sys.stderr)
        return 2

    n.banner("CHAKRAVYUH — narrated run",
             f"pack {args.pack} · scenario {Path(args.scenario).stem} · seed {args.seed} · "
             f"agent tier rule (no LLM)")
    n.write("  What follows is one cyclone put through one country's rulebook. Each stage says "
            "what it did")
    n.write("  and shows the artefact it produced. Nothing is narrated that is not on disk.")

    store = ClauseStore()
    try:
        narrate_kb(n, store)
        if not args.skip_retrieval:
            narrate_retrieval(n, store, QUESTIONS, args.k)
        pack = narrate_pack(n, pack_path, store)
        scenario = load_scenario(args.scenario)
        narrate_scenario(n, scenario)
        result = run(scenario, pack, seed=args.seed)
        counts = narrate_run(n, result, scenario, pack, store, args.full)
        narrate_properties(n, result, scenario)
        ok = narrate_ledger(n, result, counts)
    finally:
        store.close()

    n.banner("done", f"{result.run_id}  ·  head {result.ledger_head_hash[:32]}…")
    others = [p.stem for p in sorted(PACKS_DIR.glob("*.yaml")) if p.stem != args.pack]
    n.write("  Run it again with the same seed and the same pack and every line above is the "
            "same, byte for byte.")
    if others:
        n.write(f"  Run it with {n.good('--pack ' + others[0])} and the only thing that "
                f"changed is the law.")
    n.blank()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
