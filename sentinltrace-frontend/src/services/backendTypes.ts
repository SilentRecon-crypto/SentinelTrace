// ============================================================
// SENTINELTRACE — REAL BACKEND RESPONSE TYPES
//
// These mirror the ACTUAL FastAPI/Pydantic schemas in the SentinelTrace
// backend (sentineltrace-backend, Stage 9), field-for-field, as opposed to
// src/types/index.ts's UI-facing mock types. Nothing here is invented —
// every field name/type was read directly from the backend's app/schemas/
// files. New sections get added here only as each stage is wired in.
//
// LEAKAGE / SCOPE NOTE (per explicit integration decision): the backend's
// legacy Stage 2 `GET /complaints/{id}` and `GET /accounts/{id}` endpoints
// still return `chain: number[]` (the synthetic ground-truth mule-chain)
// and `acc_type: string` (a synthetic role label) respectively — this is
// frozen backend behavior we do not touch. This file deliberately OMITS
// both fields from the TypeScript types below, so that no frontend code
// can reference `.chain` or `.acc_type` without a compile error (short of
// an explicit `as any` cast, which no code in this codebase performs).
// The raw JSON these endpoints return may still technically contain these
// keys at runtime; they are intentionally never read.
//
// Also omitted from BackendComplaint for the same reason, even though not
// explicitly named in the leakage rules: `used_shared_pool`, `mode`, and
// `missing_hop_idx`. Per the backend's own app/models/complaint.py
// docstring, these are synthetic-dataset-GENERATION parameters (how the
// complaint's chain was constructed for the research dataset), not real
// investigative data — the same "evaluation-only field" category the
// leakage rules describe in spirit, even if not by name. See the frontend
// integration audit for the full reasoning.
// ============================================================

export interface BackendHealth {
  api_status: string;
  database_connected: boolean;
  model_a_loaded: boolean;
  model_a_version: string | null;
  environment: string;
}

/**
 * GET /api/v1/complaints/{id} and list items within
 * GET /api/v1/complaints — deliberately excludes `chain`, `used_shared_pool`,
 * `mode`, `missing_hop_idx` (see file header).
 */
export interface BackendComplaint {
  complaint_id: number;
  victim: number; // victim account_id
  day: number; // synthetic-dataset day index — NOT a real calendar date, never format as one
  fraud_amount: number;
  n_hops: number;
}

export interface BackendComplaintListResponse {
  items: BackendComplaint[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * GET /api/v1/complaints/{id}/mule-chain — Model A's ranked mule-chain
 * candidates for a complaint. Field-for-field match of the backend's
 * RankedCandidateOut/PredictionRunResponse (app/schemas/prediction.py).
 * `model_score` is Model A's raw P(is_mule_account) output — NOT a risk
 * score, confidence, or cash-out probability (same caveat the backend
 * itself documents on this field). No fields are excluded here; this
 * endpoint was already leakage-audited by the backend across Stages 3-5
 * and contains no ground-truth/role information.
 */
export interface BackendRankedCandidate {
  rank: number;
  candidate_account_id: number;
  model_score: number;
  hop_distance: number;
  features: Record<string, number>;
  explanation: string[];
}

export interface BackendPredictionRunResponse {
  complaint_id: number;
  model_version: string;
  generated_at: string;
  prediction_run_id: string;
  candidate_count: number;
  results: BackendRankedCandidate[];
}

/**
 * GET /api/v1/complaints/{id}/graph — field-for-field match of the
 * backend's ComplaintGraphResponse/GraphNodeOut/GraphEdgeOut/
 * GraphEdgeTransactionOut (app/schemas/graph.py). No fields excluded —
 * this endpoint contains no acc_type/chain/role/ground-truth information
 * at all (verified by reading the schema directly); it is a transaction
 * network, not a labeled classification.
 */
export interface BackendGraphNode {
  account_id: number;
  created_day: number;
  depth: number;
  is_root: boolean;
  is_candidate: boolean;
  prediction_rank: number | null;
  model_score: number | null;
}

export interface BackendGraphEdgeTransaction {
  transaction_id: number;
  day: number;
  hour: number;
  amount: number;
}

export interface BackendGraphEdge {
  src_account_id: number;
  dst_account_id: number;
  transaction_count: number;
  total_amount: number;
  first_day: number;
  last_day: number;
  transactions: BackendGraphEdgeTransaction[];
}

export interface BackendComplaintGraph {
  complaint_id: number;
  root_account_id: number;
  max_depth: number;
  node_count: number;
  edge_count: number;
  truncated: boolean;
  nodes: BackendGraphNode[];
  edges: BackendGraphEdge[];
}

/**
 * GET/POST /api/v1/complaints/{id}/risk — field-for-field match of
 * RiskScoreOut/PriorityOut/DriverOut (app/schemas/risk.py). One row PER
 * CANDIDATE ACCOUNT, not one per complaint — there is no single
 * complaint-level risk value in the backend. `priority.value`/
 * `priority.level` (the operational risk score/band) are explicitly
 * DISTINCT from `ml_score` (Model A's raw prediction, see
 * BackendRankedCandidate above) — never merge them into one number.
 */
export interface BackendRiskDriver {
  factor: string;
  contribution: number;
  description: string;
}

export interface BackendRiskPriority {
  level: string;
  value: number;
  method: string;
  formula_inputs: string[];
}

export interface BackendRiskScore {
  complaint_id: number;
  account_id: number;
  ml_score: number;
  heuristic_score: number;
  priority: BackendRiskPriority;
  drivers: BackendRiskDriver[];
  generated_at: string;
}

export interface BackendRiskListResponse {
  complaint_id: number;
  results: BackendRiskScore[];
}

/**
 * GET /api/v1/complaints/{id}/intervention-window — field-for-field match
 * of InterventionWindowOut (app/schemas/intervention.py). Only ever exists
 * for the complaint's single top-ranked (rank==1) candidate account —
 * `account_id` here identifies which one. `urgency` is one of
 * "critical"/"high"/"medium"/"low" (app/core/risk_config.py's
 * INTERVENTION_URGENCY_BANDS), the same four-value vocabulary as
 * src/types RiskLevel — safe to reuse RiskBadge for it (see
 * ComplaintDetail.tsx). `validation_status` (e.g. "synthetic_demo_only")
 * is shown verbatim, never hidden or reworded.
 */
export interface BackendInterventionWindow {
  complaint_id: number;
  account_id: number;
  current_time: string;
  predicted_cashout_time: string;
  estimated_window_minutes: number;
  urgency: string;
  method: string;
  validation_status: string;
  rationale: string;
}

/**
 * Case / Notes / Evidence / Resolution / Dossier (Stages 6-9) — field-for-
 * field match of CaseOut/CaseNoteOut/CaseEvidenceOut/CaseResolutionOut/
 * DossierOut (app/schemas/case.py, evidence.py, resolution.py, dossier.py).
 * No fields excluded — none of these contain acc_type/chain/role/
 * ground-truth information (verified by reading the schemas directly).
 * `status` is one of exactly "open"|"investigating"|"escalated"|"resolved"
 * (app/core/case_config.py); `evidence_type` one of exactly
 * "transaction_reference"|"graph_explanation_reference"|"risk_driver_reference"
 * (app/core/evidence_config.py); `outcome_type` one of exactly
 * "confirmed_mule"|"false_positive"|"insufficient_evidence"|"referred_external"
 * (app/core/resolution_config.py) — kept as `string` here rather than a
 * union to match the backend's own (intentionally simple) response typing,
 * with the literal allowed values enforced in the UI form controls.
 */
export interface BackendCase {
  case_id: string;
  alert_id: string;
  complaint_id: number;
  account_id: number;
  status: string;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface BackendCaseListResponse {
  results: BackendCase[];
}

export interface BackendCaseNote {
  note_id: string;
  case_id: string;
  author: string;
  note_text: string;
  created_at: string;
}

export interface BackendCaseNoteListResponse {
  case_id: string;
  results: BackendCaseNote[];
}

export interface BackendCaseEvidence {
  evidence_id: string;
  case_id: string;
  evidence_type: string;
  transaction_id: number | null;
  prediction_id: number | null;
  risk_score_id: string | null;
  driver_index: number | null;
  note: string | null;
  added_by: string;
  created_at: string;
}

export interface BackendCaseEvidenceListResponse {
  case_id: string;
  results: BackendCaseEvidence[];
}

export interface BackendCaseResolution {
  resolution_id: string;
  case_id: string;
  outcome_type: string;
  resolution_note: string | null;
  recorded_by: string;
  created_at: string;
}

/**
 * GET /api/v1/cases/{id}/dossier — reuses the same section types above
 * (the backend's own DossierOut does the same, reusing CaseOut/
 * CaseNoteOut/CaseEvidenceOut/CaseResolutionOut/AlertOut/RiskScoreOut/
 * InterventionWindowOut/RankedCandidateOut rather than redefining them —
 * mirrored here for the same reason).
 */
export interface BackendDossier {
  case: BackendCase;
  notes: BackendCaseNote[];
  evidence: BackendCaseEvidence[];
  resolution: BackendCaseResolution | null;
  alert: BackendAlert | null;
  risk: BackendRiskScore | null;
  intervention: BackendInterventionWindow | null;
  prediction: BackendRankedCandidate | null;
  limitations: string[];
}

/** GET /complaints/{id}/alerts, POST /complaints/{id}/alerts/generate,
 * GET /alerts/queue — field-for-field match of AlertOut/AlertListResponse/
 * AlertQueueResponse (app/schemas/alert.py). `priority_score` is Stage 5's
 * OWN derived value — explicitly distinct from Model A's `model_score`
 * (BackendRankedCandidate) and Stage 4's `risk_priority_value` (also
 * present here, copied verbatim by the backend for transparency) — never
 * merge or relabel these three. `status` is one of exactly
 * "open"|"acknowledged"|"resolved" (app/core/alert_config.py) with no
 * backend mutation endpoint — display only, no status-change UI. */
export interface BackendAlert {
  alert_id: string;
  complaint_id: number;
  account_id: number;
  risk_score_id: string;
  rank: number;
  alert_type: string;
  severity: string;
  status: string;
  priority_score: number;
  risk_priority_value: number;
  title: string;
  explanation: string;
  model_version: string;
  created_at: string;
  updated_at: string;
}

export interface BackendAlertListResponse {
  complaint_id: number;
  results: BackendAlert[];
}

export interface BackendAlertQueueResponse {
  results: BackendAlert[];
}
