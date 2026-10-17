// ============================================================
// Real backend Case + Notes + Evidence + Resolution + Dossier —
// Stages 6-9. Consolidated into one file rather than five: every function
// here hangs off the same case_id and is used together from one page
// (InvestigationWorkspace.tsx), so one file is cleaner than five thin
// ones per the existing service-layer pattern's own judgment call
// ("if the existing architecture makes fewer files cleaner, use fewer
// files").
//
//   POST /alerts/{alert_id}/cases        openCaseForAlert
//   GET  /cases/{case_id}                getCase
//   PATCH /cases/{case_id}               updateCase
//   POST /cases/{case_id}/notes          addCaseNote
//   GET  /cases/{case_id}/notes          getCaseNotes
//   POST /cases/{case_id}/evidence       addCaseEvidence
//   GET  /cases/{case_id}/evidence       getCaseEvidence
//   POST /cases/{case_id}/resolution     submitCaseResolution
//   GET  /cases/{case_id}/resolution     getCaseResolution
//   GET  /cases/{case_id}/dossier        getCaseDossier
// ============================================================
import type {
  BackendCase,
  BackendCaseEvidence,
  BackendCaseEvidenceListResponse,
  BackendCaseNote,
  BackendCaseNoteListResponse,
  BackendCaseResolution,
  BackendDossier,
} from "@/services/backendTypes";
import { ApiError, http } from "@/services/httpClient";

export async function openCaseForAlert(alertId: string): Promise<BackendCase> {
  // Throws ApiError(404) if the alert doesn't exist, or ApiError(409) if a
  // case already exists for it — the 409's message includes the existing
  // case_id (the backend's own error text), handled by the caller.
  return http.post<BackendCase>(`/api/v1/alerts/${alertId}/cases`);
}

/**
 * Extracts a UUID from the backend's own 409 "case already exists" message
 * (e.g. "...already exists for this alert: <uuid>. Use GET ... to
 * retrieve it.") — parsing a real identifier the backend already returned
 * in its own text, not fabricating one. Shared by every page that calls
 * openCaseForAlert() (InvestigationWorkspace.tsx since Slice 4,
 * ComplaintDetail.tsx since Slice 5) so the parsing logic exists in one
 * place rather than being duplicated per page.
 */
export function extractCaseIdFromDuplicateMessage(message: string): string | null {
  const m = message.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  return m ? m[0] : null;
}

export async function getCase(caseId: string): Promise<BackendCase | null> {
  try {
    return await http.get<BackendCase>(`/api/v1/cases/${caseId}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

/**
 * `assignedTo` distinguishes "omit the key" (leave unchanged) from
 * "explicitly clear" (`null`) exactly as the backend's CaseUpdateRequest
 * requires — achieved by only adding the `assigned_to` key to the request
 * body when the caller's `updates` object actually contains that key at
 * all (checked with `in`, not `!== undefined`, so passing `assignedTo: null`
 * is preserved while omitting the property entirely is not).
 */
export async function updateCase(caseId: string, updates: { status?: string; assignedTo?: string | null }): Promise<BackendCase> {
  const body: Record<string, unknown> = {};
  if (updates.status !== undefined) body.status = updates.status;
  if ("assignedTo" in updates) body.assigned_to = updates.assignedTo;
  return http.patch<BackendCase>(`/api/v1/cases/${caseId}`, body);
}

export async function getCaseNotes(caseId: string): Promise<BackendCaseNote[]> {
  const res = await http.get<BackendCaseNoteListResponse>(`/api/v1/cases/${caseId}/notes`);
  return res.results;
}

export async function addCaseNote(caseId: string, author: string, noteText: string): Promise<BackendCaseNote> {
  return http.post<BackendCaseNote>(`/api/v1/cases/${caseId}/notes`, { author, note_text: noteText });
}

export async function getCaseEvidence(caseId: string): Promise<BackendCaseEvidence[]> {
  const res = await http.get<BackendCaseEvidenceListResponse>(`/api/v1/cases/${caseId}/evidence`);
  return res.results;
}

/** Reference-based evidence only — matches the backend's exact three
 * supported types. Never file upload, never arbitrary JSON. */
export interface CaseEvidenceCreatePayload {
  evidence_type: "transaction_reference" | "graph_explanation_reference" | "risk_driver_reference";
  transaction_id?: number;
  prediction_id?: number;
  risk_score_id?: string;
  driver_index?: number;
  note?: string;
  added_by: string;
}

export async function addCaseEvidence(caseId: string, payload: CaseEvidenceCreatePayload): Promise<BackendCaseEvidence> {
  return http.post<BackendCaseEvidence>(`/api/v1/cases/${caseId}/evidence`, payload);
}

/** Returns null when no resolution has been recorded yet for this case —
 * the same "known-to-exist parent, 404 means legitimately absent child"
 * pattern used throughout this service layer since Slice 2. */
export async function getCaseResolution(caseId: string): Promise<BackendCaseResolution | null> {
  try {
    return await http.get<BackendCaseResolution>(`/api/v1/cases/${caseId}/resolution`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

/** Explicit user action only — never called automatically. The backend
 * itself enforces "case must currently be status=resolved" (409 if not)
 * and "one resolution per case" (409 if one exists) — this function does
 * not duplicate that validation client-side, it just surfaces whatever
 * the backend says. */
export async function submitCaseResolution(
  caseId: string,
  payload: { outcome_type: string; resolution_note?: string; recorded_by: string }
): Promise<BackendCaseResolution> {
  return http.post<BackendCaseResolution>(`/api/v1/cases/${caseId}/resolution`, payload);
}

export async function getCaseDossier(caseId: string): Promise<BackendDossier> {
  return http.get<BackendDossier>(`/api/v1/cases/${caseId}/dossier`);
}
