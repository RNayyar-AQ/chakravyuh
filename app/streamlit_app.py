"""CHAKRAVYUH demo UI: Timeline | Adviser | Failure Atlas | Why? | Ledger & Audit.

Y.3172 node: SINK. Runs fully offline: rule-based agent twins need no model, and the Adviser falls
back to extractive mode when no LLM is reachable. Nothing here decides anything -- it displays what
the simulator and the policy engine already decided.

    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chakravyuh.agents.adviser import Adviser
from chakravyuh.agents.base import ProposalIdFactory
from chakravyuh.agents.rule_agents import build_rule_agents
from chakravyuh.analysis.compare import divergences, gap_findings_across, run_across_packs
from chakravyuh.audit.ledger import read, verify
from chakravyuh.fuzz.properties import PROPERTY_TEXT
from chakravyuh.kb.clause_store import ClauseStore
from chakravyuh.policy.compiler import compile_all
from chakravyuh.sim.events import load_scenario
from chakravyuh.sim.runner import context_for

st.set_page_config(page_title="CHAKRAVYUH", page_icon="🌀", layout="wide")

SCENARIO = "data/scenarios/amphan_2020.yaml"
PASS_COLOUR = {"PASS": "#1b7f4f", "FAIL": "#b3261e"}


# --------------------------------------------------------------------- loading

@st.cache_resource(show_spinner=False)
def load_everything(scenario_path: str, seed: int):
    """One simulation sweep across every pack. Cached so tab switches do not re-run it."""
    scenario = load_scenario(scenario_path)
    packs = compile_all()
    results = run_across_packs(scenario, packs, seed=seed,
                               agent_factory=lambda: build_rule_agents(ProposalIdFactory()))
    findings = gap_findings_across(results, packs, scenario)
    return scenario, packs, results, findings


@st.cache_resource(show_spinner=False)
def load_adviser(retrieval_mode: str):
    return Adviser(retrieval_mode=retrieval_mode, use_llm=False)


@st.cache_resource(show_spinner=False)
def load_store():
    return ClauseStore()


def badge(passed: bool) -> str:
    label = "PASS" if passed else "FAIL"
    return (f"<span style='background:{PASS_COLOUR[label]};color:#fff;padding:2px 8px;"
            f"border-radius:10px;font-size:0.8em;font-weight:600'>{label}</span>")


# ----------------------------------------------------------------------- shell

st.title("🌀 CHAKRAVYUH")
st.caption("Policy fuzzing for emergency telecom governance — agents propose, a deterministic "
           "Game Master and policy engine decide, and every decision cites a clause.")

with st.sidebar:
    st.header("Run")
    seed = st.number_input("Seed", min_value=0, max_value=10_000, value=0, step=1)
    retrieval_mode = st.selectbox("Adviser retrieval", ["hybrid", "bm25", "vector", "tree"], index=0)
    st.divider()
    st.markdown(
        "**Limits.** Synthetic world. Illustrative thresholds. Policy packs are encodings of "
        "selected clauses **for simulation, not legal advice**. Clauses marked "
        "`unverified_summary` are accurate summaries with real source URLs, **not verbatim "
        "statute text**."
    )

try:
    scenario, packs, results, findings = load_everything(SCENARIO, int(seed))
except Exception as exc:
    st.error(f"Could not run the simulation: {exc}")
    st.info("Run `python scripts/build_kb.py --no-chroma` first: the policy packs will not compile "
            "until the clause store exists.")
    st.stop()

base_pack = "india_current" if "india_current" in results else sorted(results)[0]

tab_timeline, tab_adviser, tab_atlas, tab_why, tab_ledger = st.tabs(
    ["Timeline", "Ask the Adviser", "Failure Atlas", "Why?", "Ledger & Audit"])


# -------------------------------------------------------------------- timeline

with tab_timeline:
    st.subheader("Properties by policy pack")
    st.caption("Same scenario, same agents, same seed. Only the law changes.")

    cols = st.columns(len(results))
    for col, pack_id in zip(cols, sorted(results), strict=True):
        r = results[pack_id]
        with col:
            st.markdown(f"**`{pack_id}`** · {packs[pack_id].jurisdiction} · {packs[pack_id].mode}")
            for p in r.properties:
                st.markdown(f"{badge(p.passed)} **{p.property_id}** `{p.margin:+g}`",
                            unsafe_allow_html=True)
            ok, msg = verify(r.ledger_path)
            st.caption(f"ledger {'verifies' if ok else 'FAILS'} · {r.tick_count} ticks · "
                       f"{r.wall_seconds}s")

    with st.expander("What each property means, and in what unit"):
        for p in results[base_pack].properties:
            st.markdown(f"- **{p.property_id}** — {PROPERTY_TEXT[p.property_id]}  \n"
                        f"  _unit: {p.unit}; margin is signed slack, negative means violated_")

    divs = divergences(results)
    if divs:
        st.subheader("Where the packs disagree")
        st.dataframe([{"property": d["property_id"],
                       "fails under": ", ".join(d["fails_under"]),
                       "passes under": ", ".join(d["passes_under"]),
                       **{f"margin {k}": v for k, v in d["margins"].items()}} for d in divs],
                     width='stretch', hide_index=True)

    st.subheader("Event timeline — who learned what, and when")
    st.caption("The same fact reaches different agents at different times. That unevenness is the "
               "object of study, not a defect.")
    pack_choice = st.selectbox("Pack", sorted(results), index=sorted(results).index(base_pack),
                               key="timeline_pack")
    ctx = context_for(results[pack_choice])
    bus, gm, world = ctx["bus"], ctx["gm"], ctx["world"]

    rows = []
    for d in bus.delivered:
        rows.append({"released T+": d.released_t, "arrived T+": d.arrives_t,
                     "latency (min)": d.latency, "role": d.role,
                     "event": d.event.type, "area": d.event.area or "",
                     "source": "constructed" if d.event.synthetic else "IMD release",
                     "claimed issuer": d.event.claimed_issuer or ""})
    rows.sort(key=lambda r: (r["arrived T+"], r["role"]))

    n_syn = sum(1 for e in scenario.events if e.synthetic)
    st.caption(f"{len(scenario.events) - n_syn} of the {len(scenario.events)} events are messages "
               f"from the IMD release; **{n_syn} are constructed by us** and are greyed below — "
               f"the per-cell outages, the rumour and the forged order. No public dataset records "
               f"cell-site outage for an Indian cyclone, and the forged order never happened: it "
               f"is an adversarial test, not history.")

    def _grey_constructed(row):
        """Grey every row whose event we constructed, so it cannot read as a historical fact."""
        grey = row["source"] == "constructed"
        return ["color: #8a8a8a; font-style: italic" if grey else "" for _ in row]

    try:
        import pandas as pd
        st.dataframe(pd.DataFrame(rows).style.apply(_grey_constructed, axis=1),
                     width='stretch', hide_index=True, height=280)
    except ImportError:          # pandas absent: the column still says which is which
        st.dataframe(rows, width='stretch', hide_index=True, height=280)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Channel latency observed per role**")
        st.dataframe([{"role": k, **v} for k, v in bus.latency_report().items()],
                     width='stretch', hide_index=True)
    with c2:
        st.markdown("**Verdicts**")
        st.dataframe([{"decision": k, "count": v} for k, v in gm.verdict_counts().items()],
                     width='stretch', hide_index=True)
        st.markdown("**Blocks by reason**")
        st.dataframe([{"reason": k, "count": v} for k, v in gm.blocks_by_reason().items()],
                     width='stretch', hide_index=True)

    st.subheader("Actions that reached the world")
    st.dataframe([{"T+": e["t"], "role": e["actor_role"], "action": e["action_type"],
                   "area": e.get("area") or "", "rules": ", ".join(e.get("rule_ids") or []),
                   "trigger authentic": e.get("trigger_authentic", True)}
                  for e in gm.effects], width='stretch', hide_index=True, height=260)

    if gm.forged_executions:
        st.error(f"{len(gm.forged_executions)} irreversible action(s) executed on an "
                 f"unauthenticated order — property P2 violated.")
        st.json(gm.forged_executions)


# --------------------------------------------------------------------- adviser

with tab_adviser:
    st.subheader("Policy & Legal Adviser")
    st.caption("Holds no powers and proposes no actions. Every claim must cite a clause_id that was "
               "retrieved and exists in the clause store; a citation failing either test is "
               "rejected in code, not trusted.")

    adviser = load_adviser(retrieval_mode)
    store = load_store()
    st.info("**Extractive mode** — no model is configured, so the Adviser quotes the retrieved "
            "clauses and generates no prose. Quoting is not advising; set `CHAKRAVYUH_LLM_MODE` "
            "and a model, then record the cache, to get generated answers.")

    examples = [
        "Who can order temporary suspension of telecom services and for how long?",
        "Can our SDMA issue a CAP alert across the border into Bangladesh?",
        "Is there a standing trigger that switches on disaster roaming without a fresh order?",
        "Must we authenticate a suspension order before giving effect to it?",
        "Can we process subscriber data without consent during a disaster?",
    ]
    pick = st.selectbox("Example question", ["(type your own)"] + examples)
    question = st.text_input("Question", value="" if pick == "(type your own)" else pick)
    at_t = st.slider("Ask at simulated time (T+ minutes)", 0, scenario.horizon_min, 90, 15)

    if question:
        ans = adviser.ask(question, t=at_t)
        st.markdown(f"**Mode** `{ans.mode}` · **retrieval** `{ans.retrieval_mode}` · "
                    f"**confidence** `{ans.confidence}`")
        st.text_area("Answer", ans.answer, height=260)
        st.markdown("**Cited clauses**")
        st.markdown(ans.citations_markdown(store))
        if ans.gaps:
            st.warning("Gaps reported by the Adviser:\n\n" + "\n".join(f"- {g}" for g in ans.gaps))
        if ans.rejected_citations:
            st.error(f"Citations rejected by the gate (not retrieved or not in the store): "
                     f"{ans.rejected_citations}")
        with st.expander("Retrieved chunks (what the Adviser was allowed to see)"):
            st.json({"chunk_ids": ans.retrieved_chunk_ids, "clause_ids": ans.retrieved_clause_ids})

    st.divider()
    st.subheader("Clause store")
    st.caption("The structured layer. Legality checks come from here by exact ID, never from "
               "similarity search.")
    clauses = store.all_clauses()
    st.dataframe([{"clause_id": c.clause_id, "jurisdiction": c.jurisdiction,
                   "instrument": c.instrument, "section": c.section,
                   "verbatim status": c.verbatim_status, "sha256": c.sha256[:12] + "…"}
                  for c in clauses], width='stretch', hide_index=True, height=300)


# ----------------------------------------------------------------------- atlas

with tab_atlas:
    st.subheader("Gap register")
    st.caption("Domain-first, country as instance. Each row is produced by a run, with the "
               "cross-pack result from replaying the same seed under the other packs.")

    rows = []
    for f in findings.get(base_pack, []):
        rows.append({
            "property": f.violated_property, "class": f.gap_class, "domain": f.domain,
            "instance": f.instance, "statement": f.statement,
            "clauses": ", ".join(f.responsible_clause_ids),
            "passes under": ", ".join(f.evidence.get("passes_under_packs", [])) or "none",
        })
    if rows:
        st.dataframe(rows, width='stretch', hide_index=True)
        counts: dict[str, int] = {}
        for f in findings[base_pack]:
            counts[f.gap_class] = counts.get(f.gap_class, 0) + 1
        st.markdown("**By class:** " + ", ".join(f"`{k}` {v}" for k, v in sorted(counts.items())))
        for f in findings[base_pack]:
            with st.expander(f"{f.violated_property} · {f.gap_class} · {f.instance}"):
                st.markdown(f"**{f.domain}:** {f.statement}")
                st.markdown(f"Responsible clauses: "
                            f"{', '.join(f'`{c}`' for c in f.responsible_clause_ids) or 'n/a'}")
                st.markdown(f"Evidence run: `{f.evidence_run_id}`")
                st.json(f.evidence)
    else:
        st.success(f"No gap found under `{base_pack}` for this seed.")

    st.divider()
    st.subheader("Failure cards from fuzzing")
    index = Path("outputs/failures/index.json")
    if index.exists():
        cards = json.loads(index.read_text(encoding="utf-8"))
        if cards:
            st.dataframe([{"failure": c["failure_id"], "pack": c["pack_id"],
                           "property": c["violated_property"], "margin": c["margin"],
                           "class": c["gap_class"], "mutations": len(c["mutations"]),
                           "passes under": ", ".join(c["passes_under_packs"]) or "none"}
                          for c in cards], width='stretch', hide_index=True)
            for c in cards:
                with st.expander(f"{c['failure_id']} — {c['violated_property']} under "
                                 f"`{c['pack_id']}`"):
                    st.markdown("**Minimal mutation sequence** (Hypothesis-shrunk):")
                    for i, m in enumerate(c["mutations"], 1):
                        args = ", ".join(f"{k}={v}" for k, v in sorted((m.get("args") or {}).items()))
                        st.code(f"{i}. {m['op']}({args})", language="text")
                    st.markdown(f"**Replay:** `{c['replay_cmd']}`")
        else:
            st.info("No failure cards: the fuzzer found no new failure within its budget.")
    else:
        st.info("No fuzz results yet. Run `python scripts/run_fuzz.py` to populate the atlas.")


# ---------------------------------------------------------------------- ledger

with tab_why:
    st.subheader("Why did this happen?")
    st.caption("Pick any action a run took. This is the whole chain behind it: what the agent "
               "could see, what it proposed and why, which rule decided it, the verbatim clause "
               "that rule rests on, that clause's SHA-256, and the official URL to check it "
               "against. Nothing here is regenerated -- every field is read back out of the "
               "hash-chained ledger.")

    why_pack = st.selectbox("Pack", sorted(results), key="why_pack",
                            index=sorted(results).index(base_pack))
    why_ledger = Path(results[why_pack].ledger_path)
    if not why_ledger.exists():
        st.info("No ledger for that pack yet.")
    else:
        entries = list(read(why_ledger))
        proposals = {e.payload["proposal_id"]: e for e in entries if e.kind == "PROPOSAL"}
        verdicts = {e.payload["proposal_id"]: e for e in entries if e.kind == "VERDICT"}
        effects = {e.payload.get("proposal_id"): e for e in entries if e.kind == "EFFECT"}

        decisions = sorted({v.payload["decision"] for v in verdicts.values()})
        want = st.multiselect("Show decisions", decisions, default=decisions, key="why_dec")
        actions = sorted({p.payload["action_type"] for p in proposals.values()})
        want_actions = st.multiselect("Show actions", actions, default=actions, key="why_act")

        candidates = [pid for pid, p in proposals.items()
                      if p.payload["action_type"] in want_actions
                      and pid in verdicts and verdicts[pid].payload["decision"] in want]
        if not candidates:
            st.info("No action matches those filters.")
        else:
            labels = {}
            for pid in candidates:
                p, v = proposals[pid].payload, verdicts[pid].payload
                labels[pid] = (f"T+{proposals[pid].t_minutes:>5} | {p['actor_role']:<21} | "
                               f"{p['action_type']:<26} | {v['decision']}")
            pick = st.selectbox("Action", candidates, key="why_pick",
                                format_func=lambda pid: labels[pid])

            p_entry, v_entry = proposals[pick], verdicts[pick]
            p, v = p_entry.payload, v_entry.payload
            e_entry = effects.get(pick)

            c1, c2, c3 = st.columns(3)
            c1.metric("Decision", v["decision"])
            c2.metric("At", f"T+{p_entry.t_minutes} min")
            c3.metric("Ledger seq", f"{p_entry.seq} → {v_entry.seq}")

            st.markdown("**1 — What the agent could see.** The events that triggered this "
                        "proposal, at the time they reached *this* role.")
            trigger_ids = set(p.get("triggered_by_event_ids") or [])
            deliveries = [e for e in entries if e.kind == "DELIVERY"
                          and e.payload.get("event_id") in trigger_ids
                          and e.payload.get("role") == p["actor_role"]]
            if deliveries:
                st.dataframe([{"event": d.payload.get("event_id"),
                               "type": d.payload.get("event_type", ""),
                               "arrived at role": f"T+{d.t_minutes}",
                               "channel delay": d.payload.get("delay_min", "")}
                              for d in deliveries], width='stretch', hide_index=True)
            else:
                st.caption(f"Triggered by {sorted(trigger_ids) or 'standing duty, no event'} "
                           f"— no DELIVERY entry, so this action rests on a standing obligation "
                           f"rather than on news arriving.")

            st.markdown("**2 — What it proposed, and its reasoning.**")
            st.code(p["reasoning"] or "(no reasoning recorded)", language=None)
            st.json({"action_type": p["action_type"], "params": p.get("params", {}),
                     "cited_rule_ids": p.get("cited_rule_ids", []),
                     "cited_clause_ids": p.get("cited_clause_ids", [])})

            st.markdown("**3 — What the policy engine decided, and on which rule.**")
            st.code(f"{v['decision']}  —  {v['explanation']}", language=None)
            st.caption(f"deciding rule(s): {', '.join(v.get('rule_ids') or []) or 'none'} · "
                       f"mode: {v.get('mode', '-')}")

            st.markdown("**4 — The law behind it.** Verbatim text, hash and official source.")
            store = load_store()
            cited = v.get("clause_ids") or p.get("cited_clause_ids") or []
            if not cited:
                st.caption("No clause cited — this verdict rests on the absence of a rule, "
                           "which is itself a gap-register finding.")
            for cid in cited:
                clause = store.try_get(cid)
                if clause is None:
                    st.warning(f"{cid}: not in the clause store")
                    continue
                badge = {"verified": "verbatim gazette text",
                         "verified_with_artifacts": "verbatim gazette text, carries page-break "
                                                    "artefacts — not quotable",
                         "unverified_summary": "SUMMARY, not the instrument's words"}
                with st.expander(f"{cid} — {clause.instrument} "
                                 f"[{badge.get(clause.verbatim_status, clause.verbatim_status)}]"):
                    st.write(clause.text_verbatim)
                    st.caption(f"provenance `{clause.provenance}` · "
                               f"page {clause.page if clause.page is not None else '—'} · "
                               f"sha256 `{clause.sha256[:24]}…`")
                    if clause.source_pdf_sha256:
                        st.caption(f"source PDF sha256 `{clause.source_pdf_sha256[:24]}…` — "
                                   f"pins the document even if the link rots")
                    if clause.marginal_note_candidate:
                        st.caption(f"suspected interpolated marginal heading: "
                                   f"`{clause.marginal_note_candidate}` (flagged, NOT removed)")
                    st.markdown(f"[Open the official source]({clause.source_url})")

            st.markdown("**5 — What actually changed in the world.**")
            if e_entry is None:
                st.caption("No EFFECT entry: the action did not execute (blocked, or still held "
                           "at the human gate).")
            else:
                st.json(e_entry.payload)
                cap = e_entry.payload.get("cap_identifier")
                if cap:
                    st.caption(f"CAP 1.2 / ITU-T X.1303 envelope `{cap}` sent "
                               f"{e_entry.payload.get('cap_sent')} in "
                               f"`{e_entry.payload.get('cap_language')}`")

with tab_ledger:
    st.subheader("Hash-chained audit ledger")
    st.caption("hash = sha256(prev_hash | seq | t | kind | canonical_json(payload)). Editing, "
               "reordering, inserting or deleting any line breaks the chain.")

    ledgers = sorted(Path("runs").rglob("*.jsonl")) if Path("runs").exists() else []
    if not ledgers:
        st.info("No ledgers yet. Run `python scripts/run_demo.py`.")
    else:
        choice = st.selectbox("Ledger", [str(p) for p in ledgers],
                              index=next((i for i, p in enumerate(ledgers)
                                          if base_pack in str(p)), 0))
        ok, msg = verify(choice)
        (st.success if ok else st.error)(f"verify_ledger: {msg}")

        entries = list(read(choice))
        kinds = sorted({e.kind for e in entries})
        chosen = st.multiselect("Entry kinds", kinds, default=kinds)
        shown = [e for e in entries if e.kind in chosen]
        st.caption(f"{len(shown)} of {len(entries)} entries")
        st.dataframe([{"seq": e.seq, "T+": e.t_minutes, "kind": e.kind,
                       "hash": e.hash[:12] + "…", "prev": e.prev_hash[:12] + "…",
                       "payload": json.dumps(e.payload, default=str)[:160]}
                      for e in shown], width='stretch', hide_index=True, height=380)

        seqs = [e.seq for e in shown]
        if seqs:
            pick_seq = st.number_input("Inspect entry (seq)", min_value=min(seqs),
                                       max_value=max(seqs), value=min(seqs), step=1)
            entry = next((e for e in entries if e.seq == int(pick_seq)), None)
            if entry:
                st.json(entry.model_dump())

        st.markdown("**Chain-of-thought traces.** Every proposal carries the agent's reasoning; "
                    "every LLM call additionally stores its prompt hash, retrieved chunk ids and "
                    "raw output.")
        proposals = [e for e in entries if e.kind == "PROPOSAL"]
        st.dataframe([{"T+": e.t_minutes, "role": e.payload.get("actor_role"),
                       "action": e.payload.get("action_type"),
                       "cited rules": ", ".join(e.payload.get("cited_rule_ids") or []),
                       "reasoning": (e.payload.get("reasoning") or "")[:200]}
                      for e in proposals], width='stretch', hide_index=True, height=300)
