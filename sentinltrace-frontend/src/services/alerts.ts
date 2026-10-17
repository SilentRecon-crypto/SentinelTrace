// ============================================================
// Real backend Alert workflow — Stage 5.
//
//   POST /complaints/{id}/alerts/generate   generateComplaintAlerts
//   GET  /complaints/{id}/alerts            getComplaintAlerts
//   GET  /alerts/queue                      getAlertQueue
//
// Alert generation is idempotent/"replace current" on the backend — this
// service does not call it automatically anywhere; every call site must be
// an explicit analyst action (see ComplaintDetail.tsx). The backend
// returns 409 if no Stage 4 risk score exists yet for the complaint — that
// is a legitimate, expected state (risk must be generated first), not
// swallowed to null here; callers show the real backend message.
// ============================================================
import type { BackendAlertListResponse, BackendAlertQueueResponse } from "@/services/backendTypes";
import { http } from "@/services/httpClient";

export async function generateComplaintAlerts(complaintId: number): Promise<BackendAlertListResponse> {
  return http.post<BackendAlertListResponse>(`/api/v1/complaints/${complaintId}/alerts/generate`);
}

export async function getComplaintAlerts(complaintId: number): Promise<BackendAlertListResponse> {
  return http.get<BackendAlertListResponse>(`/api/v1/complaints/${complaintId}/alerts`);
}

/** Not wired into any page this slice — no existing page has a natural
 * home for a cross-complaint queue view yet (Dashboard remains a future
 * integration slice). Exported so it's available without duplicating
 * HTTP logic once that slice happens. */
export async function getAlertQueue(limit = 100): Promise<BackendAlertQueueResponse> {
  return http.get<BackendAlertQueueResponse>(`/api/v1/alerts/queue?limit=${limit}`);
}
