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
  runs_completed: number;
  max_examples: number;
  unique_minimal_failures: number;
  found: boolean;
  wall_seconds: number;
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
  adviser: Record<string, number | string>;
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
