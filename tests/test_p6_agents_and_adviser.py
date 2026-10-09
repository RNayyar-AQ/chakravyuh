"""P6 gate (spec §10): the Adviser answers a known question citing the gold clause."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from chakravyuh.agents.adviser import Adviser
from chakravyuh.agents.base import Agent, ProposalIdFactory
from chakravyuh.agents.llm_agent import LLMAgent, build_llm_agents
from chakravyuh.agents.roles import ROLES, Inbox
from chakravyuh.agents.rule_agents import build_rule_agents
from chakravyuh.llm.client import CacheMiss, LLMClient
from chakravyuh.schemas import Event

ROOT = Path(__file__).resolve().parents[1]


def test_adviser_cites_the_gold_clause(built_kb):
    adviser = Adviser(retrieval_mode="hybrid", use_llm=False)
    ans = adviser.ask("Who is the competent authority that may order a telecom suspension?")
    assert "IN.SUSP2024.r2.1" in ans.cited_clause_ids


@pytest.mark.parametrize("qid,question,gold", [
    ("Q02", "For how long can a telecom suspension direction remain in force at a time?",
     "IN.SUSP2024.r2.4"),
    ("Q11", "Within how many hours must a cyber incident be reported to CERT-In?",
     "IN.CERTIN2022.p2"),
    ("Q27", "What triggers the FCC Mandatory Disaster Response Initiative obligations?",
     "US.CFR47.4.17.trigger"),
    ("Q30", "What must states parties do about regulatory barriers to cross-border telecom use?",
     "INTL.TAMPERE1998.art9"),
    # Against the REAL gazette text now in the store.
    ("Q36", "What may the Central Government take temporary possession of on the occurrence of a "
            "public emergency?", "IN.TA2023.s20.1"),
    ("Q38", "What is the Digital Bharat Nidhi and what fund does it replace?", "IN.TA2023.s24"),
    ("Q39", "What power does the Central Government have to create regulatory sandboxes for "
            "telecom innovation?", "IN.TA2023.s27"),
])
def test_adviser_retrieves_gold_clauses(built_kb, qid, question, gold):
    adviser = Adviser(retrieval_mode="hybrid", use_llm=False)
    assert gold in adviser.ask(question).cited_clause_ids, qid


def test_adviser_never_cites_a_clause_outside_the_retrieved_set(built_kb):
    adviser = Adviser(retrieval_mode="hybrid", use_llm=False)
    ans = adviser.ask("Who can order a suspension?")
    assert set(ans.cited_clause_ids) <= set(ans.retrieved_clause_ids)
    for cid in ans.cited_clause_ids:
        assert adviser.store.exists(cid)


def test_adviser_citation_gate_rejects_an_invented_clause(built_kb, tmp_path):
    """A model that invents a clause id must not have it stand: answer becomes insufficient."""
    client = LLMClient(mode="replay", cache_dir=tmp_path)
    adviser = Adviser(retrieval_mode="bm25", client=client, use_llm=True)
    question = "Who can order a suspension?"
    hits = adviser.retrieve(question)
    context = adviser._context(hits)

    from chakravyuh.agents.adviser import REJECTION_NOTE, SYSTEM, USER
    fabricated = json.dumps({"answer": "The Director of Telecom may do so.",
                             "cited_clause_ids": ["IN.MADE.UP.s1"], "gaps": [],
                             "confidence": "high"})
    first = USER.format(question=question, situation="", context=context)
    client.seed_cache(f"{SYSTEM}\n\n---\n\n{first}", fabricated, "AdviserAnswer")
    client.seed_cache(f"{SYSTEM}\n\n---\n\n{first}\n\n{REJECTION_NOTE}", fabricated, "AdviserAnswer")

    ans = adviser.ask(question)
    assert ans.cited_clause_ids == []
    assert "Insufficient evidence" in ans.answer
    assert "IN.MADE.UP.s1" in ans.rejected_citations
    assert ans.attempts == 2


def test_adviser_falls_back_to_extractive_on_cache_miss(built_kb, tmp_path):
    client = LLMClient(mode="replay", cache_dir=tmp_path)
    adviser = Adviser(retrieval_mode="bm25", client=client, use_llm=True)
    ans = adviser.ask("Who can order a suspension?")
    assert ans.mode == "extractive"
    assert any("extractive" in g for g in ans.gaps)


# -------------------------------------------------------------------- agents

def test_all_six_roles_exist_and_satisfy_the_protocol():
    agents = build_rule_agents()
    assert set(agents) == set(ROLES) == {
        "competent_authority", "sdma_alerts", "tsp_network", "cert_in",
        "neighbour_authority", "adviser"}
    for agent in agents.values():
        assert isinstance(agent, Agent)


def test_adviser_role_proposes_nothing(india_pack):
    agent = build_rule_agents()["adviser"]
    out = agent.observe(Inbox("adviser"), 0, india_pack)
    assert all(p.action_type == "NOOP" for p in out)
    assert india_pack.powers_of("adviser") == []


def test_llm_agent_prompt_carries_objective_schema_actions_and_boundaries(india_pack, tmp_path):
    agent = LLMAgent("tsp_network", client=LLMClient(mode="replay", cache_dir=tmp_path))
    prompt = agent.system_prompt(india_pack)
    assert "Mandate:" in prompt
    assert "You may ONLY propose these actions:" in prompt
    assert "SUSPEND_SERVICE" in prompt and "ASK" in prompt and "NOOP" in prompt
    assert "cannot verify" in prompt          # the role's boundary
    assert "cited_rule_ids" in prompt          # the output schema


def test_llm_agent_raises_on_cache_miss_when_strict(india_pack, tmp_path):
    agent = LLMAgent("tsp_network", client=LLMClient(mode="replay", cache_dir=tmp_path),
                     strict=True)
    inbox = Inbox("tsp_network")

    class _D:
        arrives_t = 0
        event = Event(event_id="e1", t_minutes=0, type="ORDER", area="A",
                      payload={"area": "A"}, visible_to=["tsp_network"])
    inbox.add(_D())
    with pytest.raises(CacheMiss):
        agent.observe(inbox, 0, india_pack)


def test_llm_agent_parses_a_recorded_proposal(india_pack, tmp_path):
    client = LLMClient(mode="replay", cache_dir=tmp_path)
    agent = LLMAgent("tsp_network", client=client, ids=ProposalIdFactory())
    inbox = Inbox("tsp_network")

    class _D:
        arrives_t = 0
        event = Event(event_id="e1", t_minutes=0, type="ORDER", area="A",
                      payload={"area": "A"}, visible_to=["tsp_network"])
    inbox.add(_D())

    recorded = json.dumps({"action_type": "PRIORITISE_RELIEF_SLICE", "params": {"area": "A"},
                           "cited_rule_ids": ["IN.R.PRIORITISE_RELIEF_SLICE"],
                           "reasoning": "relief traffic must survive the suspension"})
    full = f"{agent.system_prompt(india_pack)}\n\n---\n\n{agent.user_prompt(inbox, 0)}"
    client.seed_cache(full, recorded, "Proposal")

    out = agent.observe(inbox, 0, india_pack)
    assert len(out) == 1
    assert out[0].action_type == "PRIORITISE_RELIEF_SLICE"
    assert out[0].cited_rule_ids == ["IN.R.PRIORITISE_RELIEF_SLICE"]
    assert out[0].triggered_by_event_ids == ["e1"]
    assert out[0].reasoning


def test_build_llm_agents_keeps_the_adviser_rule_based(tmp_path):
    agents = build_llm_agents(client=LLMClient(mode="replay", cache_dir=tmp_path))
    assert agents["adviser"].tier == "rule"
    assert agents["tsp_network"].tier == "llm"


def test_every_proposal_carries_reasoning_and_may_cite_rules(scenario, india_pack, tmp_path):
    from chakravyuh.sim.runner import run
    r = run(scenario, india_pack, seed=0, ledger_path=tmp_path / "l.jsonl")
    from chakravyuh.audit.ledger import read
    proposals = [e for e in read(r.ledger_path) if e.kind == "PROPOSAL"]
    assert proposals
    for e in proposals:
        assert e.payload["reasoning"], e.payload["proposal_id"]
        assert isinstance(e.payload["cited_rule_ids"], list)
