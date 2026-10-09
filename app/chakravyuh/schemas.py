"""ALL inter-module data models (spec §6). Y.3172 node: SRC (vocabulary shared by every node).

The models in spec §6 are implemented exactly. Two additive extensions are marked
EXTENSION below; both exist to keep unverified data honestly labelled rather than
silently presented as verified source text.
"""
from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel


def normalise_text(text: str) -> str:
    """Whitespace-normalise before hashing, so a reflow of the source does not break a hash."""
    return re.sub(r"\s+", " ", text).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalise_text(text).encode("utf-8")).hexdigest()


def canonical_json(payload: dict) -> str:
    """Stable serialisation: the ledger hash chain depends on this being byte-identical on replay."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


# --------------------------------------------------------------------------- KB

class Clause(BaseModel):
    clause_id: str            # e.g. "IN.TA2023.s20.2"
    instrument: str           # "Telecommunications Act 2023"
    jurisdiction: str         # "IN" | "BD" | "US" | "INTL"
    section: str
    text_verbatim: str
    source_url: str
    sha256: str               # of text_verbatim, normalised whitespace
    retrieved_at: str

    # ---- EXTENSIONS (not in §6). All exist to keep provenance attached to the text. ----
    #
    # verified                 text came from the instrument's own PDF and is clean
    # verified_with_artifacts  text came from the PDF but a marginal heading is interpolated
    #                          mid-sentence by a page break; see kb/real_sources.py
    # unverified_summary       model-written summary, NOT the words of the instrument
    verbatim_status: Literal["verified", "verified_with_artifacts", "unverified_summary"] = \
        "unverified_summary"

    # Chain of custody for gazette-derived text.
    page: Optional[int] = None                    # page of the source PDF
    source_pdf_sha256: Optional[str] = None       # hash of the PDF itself: pins the document
    text_raw: Optional[str] = None                # exactly what pdftotext produced
    sha256_raw: Optional[str] = None              # hash of text_raw, so cleaning is auditable
    pagebreak_artifact: bool = False
    marginal_note_candidate: Optional[str] = None  # suspected interpolated heading, NOT removed
    parent_clause_id: Optional[str] = None        # set on derived subsection records
    provenance: Literal["gazette_pdf", "gazette_pdf_subsection", "secondary_source",
                        "model_written"] = "model_written"

    @property
    def is_real_text(self) -> bool:
        """True when text_verbatim is the instrument's own words rather than a summary."""
        return self.verbatim_status in ("verified", "verified_with_artifacts")

    @property
    def quotable(self) -> bool:
        """Safe to quote verbatim: real text with no interpolated page-break debris."""
        return self.verbatim_status == "verified"

    def hash_matches(self) -> bool:
        return self.sha256 == sha256_text(self.text_verbatim)


# ----------------------------------------------------------------------- POLICY

class Rule(BaseModel):
    rule_id: str
    clause_ids: list[str] = []   # must exist in clause store; compiler checks hash
    actor_role: str
    action_type: str
    effect: Literal["permit", "oblige", "prohibit"]
    conditions: dict = {}        # simple DSL: {"event_seen": "LANDFALL", "area_in": "affected"}
    approval_delay_min: int = 0
    deadline_min: Optional[int] = None
    requires_authenticated_order: bool = False
    reversible: bool = True

    # EXTENSION: human-readable summary shown in agent prompts (§12 wants "rule_id: summary").
    summary: str = ""


class PolicyPack(BaseModel):
    pack_id: str
    jurisdiction: str
    version: str
    mode: Literal["advisory", "blocking"] = "blocking"
    rules: list[Rule]

    def rules_for(self, actor_role: str, action_type: str) -> list[Rule]:
        return [r for r in self.rules if r.actor_role == actor_role and r.action_type == action_type]

    def powers_of(self, actor_role: str) -> list[str]:
        """Action types this role may proposeat all: anything a permit/oblige rule names for it."""
        return sorted({r.action_type for r in self.rules
                       if r.actor_role == actor_role and r.effect in ("permit", "oblige")})


# ------------------------------------------------------------------------- SIM

class Event(BaseModel):
    event_id: str
    t_minutes: int
    type: str
    area: Optional[str] = None
    payload: dict = {}
    visible_to: list[str]
    delay_by_role: dict[str, int] = {}
    authentic: bool = True          # agents never see this field (see redact())
    claimed_issuer: Optional[str] = None
    # True when this event is our construction rather than something that happened. The real IMD
    # bulletins and the real landfall are `false`; the per-cell outages, the rumour and the forged
    # order are `true`. It is a first-class field, not a naming convention, so the UI can grey
    # them, the report can count them and nobody can mistake the adversarial test for history.
    synthetic: bool = False

    def redact(self) -> dict:
        """What an agent is allowed to perceive. `authentic` and `truth` stay with the Game Master."""
        payload = {k: v for k, v in self.payload.items() if k != "truth"}
        return {
            "event_id": self.event_id,
            "type": self.type,
            "area": self.area,
            "payload": payload,
            "claimed_issuer": self.claimed_issuer,
        }


class Proposal(BaseModel):
    proposal_id: str
    t_minutes: int
    actor_role: str
    action_type: str                 # or "ASK" / "NOOP"
    params: dict = {}
    cited_rule_ids: list[str] = []
    # Clause ids the cited rules rest on. Filled by the Game Master from the compiled pack, NOT
    # by the agent: an agent may claim a rule, but only the pack decides which law that rule
    # encodes, and the audit trail has to show law the agent could not have invented.
    cited_clause_ids: list[str] = []
    reasoning: str                   # stored as CoT trace
    triggered_by_event_ids: list[str] = []


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    NEEDS_HUMAN = "NEEDS_HUMAN"


class Verdict(BaseModel):
    proposal_id: str
    decision: Decision
    rule_ids: list[str] = []
    clause_ids: list[str] = []
    explanation: str
    mode: Literal["advisory", "blocking"]

    # EXTENSION: in advisory mode a BLOCK still executes (§5.4). The GM needs to know
    # whether to apply effects without re-deriving the mode rule.
    @property
    def executes(self) -> bool:
        if self.decision is Decision.ALLOW:
            return True
        if self.decision is Decision.BLOCK:
            return self.mode == "advisory"
        return False   # NEEDS_HUMAN executes only after the human-in-loop gate clears


# ----------------------------------------------------------------------- AUDIT

LedgerKind = Literal[
    "EVENT", "DELIVERY", "PROPOSAL", "VERDICT", "EFFECT",
    "LLM_TRACE", "ADVISER_QA", "PROPERTY",
]


class LedgerEntry(BaseModel):
    seq: int
    prev_hash: str
    hash: str
    t_minutes: int
    kind: LedgerKind
    payload: dict


# -------------------------------------------------------------------- ANALYSIS

class PropertyResult(BaseModel):
    """EXTENSION: §5.5 defines properties with a measured margin; this carries the measurement."""
    property_id: str          # P1..P4
    description: str
    passed: bool
    margin: float             # signed slack in the property's own illustrative unit
    unit: str
    detail: dict = {}


class GapFinding(BaseModel):
    """§5.6. Phrased domain-first, country as instance."""
    gap_id: str
    violated_property: str
    gap_class: Literal["policy", "coordination", "execution"]
    domain: str                              # "Emergency telecom"
    statement: str                           # domain-first phrasing
    instance: str                            # "India-Bangladesh"
    responsible_clause_ids: list[str] = []
    responsible_rule_ids: list[str] = []
    evidence_run_id: str = ""
    evidence: dict = {}


class FailureCard(BaseModel):
    failure_id: str
    pack_id: str
    seed: int
    mutations: list[dict]
    violated_property: str
    margin: float
    gap_class: Literal["policy", "coordination", "execution"]
    responsible_clause_ids: list[str]
    passes_under_packs: list[str]            # cross-pack comparison
    replay_cmd: str


class RunResult(BaseModel):
    """EXTENSION: return type of sim.runner.run (§4 names the function, not its type)."""
    run_id: str
    pack_id: str
    scenario_id: str
    seed: int
    agent_tier: str                          # "rule" | "llm" | "jev"
    ledger_path: str
    ledger_head_hash: str
    properties: list[PropertyResult] = []
    gaps: list[GapFinding] = []
    mutations: list[dict] = []
    tick_count: int = 0
    wall_seconds: float = 0.0
    llm_calls: int = 0

    @property
    def passed(self) -> bool:
        return all(p.passed for p in self.properties)

    def violated(self) -> list[PropertyResult]:
        return [p for p in self.properties if not p.passed]
