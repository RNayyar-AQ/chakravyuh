/** Shapes written by app/scripts/export_web.py. Nothing here is computed in the browser. */

export type PackId = "india_current" | "bangladesh" | "fcc_mdri";

export interface Pack {
  pack_id: PackId;
  label: string;
  blurb: string;
  jurisdiction: string;
  version: string;
  mode: string;
  rule_count: number;
}

export interface Role {
  role_id: string;
  name: string;
  analogue: string;
  mandate: string;
  boundaries: string;
  inbox_types: string[];
  priority: number;
  channel_latency_min: number;
}

export interface PropertyResult {
  property_id: string;
  text: string;
  margins: Record<string, number>;
  passes_under: string[];
  fails_under: string[];
}

export interface FuzzCard {
  failure_id: string;
  pack_id: string;
  violated_property: string;
  gap_class: string;
  margin: number;
  seed: number;
  mutations: { op: string; family: string; args: Record<string, unknown>; created_event_id?: string }[];
  responsible_clause_ids: string[];
  passes_under_packs: string[];
  replay_cmd: string;
}

export interface FuzzRun {
  pack_id: string;
  asserted_properties: string[];
  excluded_at_baseline: string[];
  baseline: Record<string, boolean>;
  max_examples: number;
  /** The declared budget for campaigns that actually ran; 0 where the baseline already failed.
   *  The number of examples a randomised search *completes* is not reproducible, so it stays in
   *  outputs/fuzz_summary.json rather than in a bundle that must rebuild byte for byte. */
  examples_budgeted: number;
  unique_minimal_failures: number;
  found: boolean;
}

export interface LedgerRun {
  run_id: string;
  path: string;
  verified: boolean;
  message: string;
  entries: number;
  head_hash: string;
  kinds: Record<string, number>;
}

export interface Source {
  id: string;
  instrument: string;
  gazette: string;
  status: "held" | "partial" | "wanted";
  url: string;
  sha256: string;
  jurisdiction: string;
  official: boolean;
  pages: number | null;
  feeds: string[];
  reason: string | string[];
}

export interface Y3172Node {
  node: string;
  description: string;
  count: number;
  members: string[];
}

export interface RetrievalResult {
  mode: string;
  questions: number;
  recall_at_k: number;
  mrr: number;
  abstention_questions: number;
  abstention_separability: number;
  mean_top_score_answerable: number;
  mean_top_score_unanswerable: number;
}

/** Gap register rows are read straight from the CSV, so every value is a string. */
export type GapRow = Record<string, string>;

export interface ClauseRecord {
  clause_id: string;
  instrument: string;
  section: string;
  jurisdiction: string;
  text: string;
  source_url: string;
  sha256: string;
  page: number | null;
  provenance: string;
  verbatim_status: string;
  quotable: boolean;
}

/** One pipeline stage, carrying the number that stage actually produced. */
export interface FlowStage {
  node: string;
  title: string;
  module: string;
  command: string;
  measure: string;
  measure_sub: string;
  body: string;
}

/** A margin, recomputed from the operands the run recorded. */
export interface Derivation {
  pack_id: string;
  property_id: string;
  applicable: boolean;
  unit: string;
  formula: string;
  observed_label: string;
  observed: number | null;
  threshold: number | null;
  threshold_name: string;
  threshold_from?: number;
  arithmetic: string;
  margin: number;
  recomputed?: number;
  agrees: boolean;
  passed: boolean;
  note: string;
  terms: { label: string; value: number | null; note: string }[];
  seq: number;
}

export interface RrfPart {
  mode: string;
  rank: number;
  contribution: number;
}

export interface RetrievalExample {
  qid: string;
  question: string;
  gold_clause_ids: string[];
  k: number;
  formula: string;
  rankings: { mode: string; retrieved: string[]; top_score: number; first_gold_rank: number | null }[];
  fused: { clause_id: string; parts: RrfPart[]; score: number; tied_with_next: boolean }[];
  recorded_hybrid: string[];
  agrees_with_recorded: boolean;
  caveat: string;
}

export interface KbGraph {
  clauses: number;
  chunks: number;
  collections: Record<string, number>;
  chunk_metadata_fields: string[];
  instruments: {
    instrument: string;
    jurisdiction: string;
    clauses: number;
    real_text: number;
    quotable: number;
    with_page: number;
  }[];
  quotable: number;
  real_text: number;
  with_pdf_hash: number;
}

export interface TraceDelivery {
  seq: number;
  role: string;
  released_t: number;
  arrives_t: number;
  latency_min: number;
  visible_payload: Record<string, unknown>;
}

export interface TraceProposal {
  seq: number;
  t: number;
  proposal_id: string;
  role: string;
  action: string;
  params: Record<string, unknown>;
  reasoning: string;
  cited_rule_ids: string[];
  cited_clause_ids: string[];
  verdict: {
    seq: number;
    decision: Decision;
    mode: string;
    explanation: string;
    rule_ids: string[];
    clause_ids: string[];
  } | null;
}

export interface Trace {
  event_id: string;
  event: {
    seq: number;
    t: number;
    event_id: string;
    type: string;
    area: string | null;
    authentic: boolean;
    synthetic: boolean;
    claimed_issuer: string | null;
    visible_to: string[];
    delay_by_role: Record<string, number>;
    payload: Record<string, unknown>;
  } | null;
  hidden_from_agents: string[];
  deliveries: TraceDelivery[];
  proposals: TraceProposal[];
  effects: { seq: number; t: number; action: string; area: string; detail: Record<string, unknown> }[];
  moves: {
    property_id: string;
    margin: number;
    passed: boolean;
    via: { kind: "id" | "moment"; what: string[] }[];
  }[];
}

export interface RubricCheck {
  id: string;
  criterion: string;
  question: string;
  status: "PASS" | "FAIL" | "WAIVED";
  detail: string;
  waiver: string;
}

export interface Rubric {
  source: string;
  command: string;
  totals: { pass: number; waived: number; fail: number; checks: number };
  checks: RubricCheck[];
}

export interface Bundle {
  fingerprint: string;
  scenario: {
    scenario_id: string;
    title: string;
    description: string;
    horizon_min: number;
    tick_min: number;
    areas: string[];
  };
  packs: Pack[];
  roles: Role[];
  properties: Record<string, string>;
  scorecard: { properties: PropertyResult[] };
  gaps: GapRow[];
  fuzz: { runs: FuzzRun[]; cards: FuzzCard[] };
  ledger: { runs: LedgerRun[]; tamper: { run_id: string; verified: boolean; message: string }[] };
  y3172: Y3172Node[];
  kb: {
    total: number;
    provenance: Record<string, number>;
    verbatim_status: Record<string, number>;
    jurisdiction: Record<string, number>;
  };
  sources: Source[];
  retrieval: RetrievalResult[];
  retrieval_example: RetrievalExample;
  adviser: Record<string, number | string>;
  clauses: Record<string, ClauseRecord>;
  flow: FlowStage[];
  derivations: Derivation[];
  traces: Trace[];
  kb_graph: KbGraph;
  rubric: Rubric;
}

export type Decision = "ALLOW" | "BLOCK" | "NEEDS_HUMAN";

export interface TimelineItem {
  seq: number;
  t: number;
  kind: "EVENT" | "PROPOSAL" | "EFFECT" | "PROPERTY";
  // PROPOSAL
  proposal_id?: string;
  role?: string;
  action?: string;
  params?: Record<string, unknown>;
  reasoning?: string;
  rule_ids?: string[];
  clause_ids?: string[];
  decision?: Decision | null;
  explanation?: string;
  verdict_rule_ids?: string[];
  verdict_clause_ids?: string[];
  // EVENT
  event_type?: string;
  area?: string;
  payload?: Record<string, unknown>;
  synthetic?: boolean;
  authentic?: boolean;
  event_id?: string;
  claimed_issuer?: string;
  delay_by_role?: Record<string, number>;
  // EFFECT
  cap_identifier?: string;
  cap_language?: string;
  cap_shape_ok?: boolean;
  detail?: Record<string, unknown>;
  // PROPERTY
  property_id?: string;
  holds?: boolean;
  margin?: number;
  description?: string;
}

export interface RunFooter {
  verdicts?: Record<string, number>;
  blocks_by_reason?: Record<string, number>;
  forged_executions?: number;
  undelivered_at_horizon?: number;
  human_gate?: {
    mode: string;
    decisions: { proposal_id: string; approved: boolean; approver: string; at: number }[];
    still_pending: unknown[];
  };
  latency_by_role?: Record<string, Record<string, number>>;
}

export interface Timeline {
  run_id: string;
  header: Record<string, unknown>;
  footer: RunFooter;
  counts: Record<string, number>;
  decisions: Record<string, number>;
  items: TimelineItem[];
}
