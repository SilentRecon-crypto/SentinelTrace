// ============================================================
// Real backend risk + intervention window —
//   GET/POST /api/v1/complaints/{id}/risk
//   GET      /api/v1/complaints/{id}/intervention-window
//
// Both GET endpoints 404 when nothing has been computed yet for a
// complaint that itself exists — resolved to `null` here (a legitimate,
// expected state — "not generated yet" — not an error), exactly the same
// pattern src/services/predictions.ts already established in Slice 2.
// ============================================================
import type { BackendInterventionWindow, BackendRiskListResponse } from "@/services/backendTypes";
import { ApiError, http } from "@/services/httpClient";

export async function getComplaintRisk(complaintId: number): Promise<BackendRiskListResponse | null> {
  try {
    return await http.get<BackendRiskListResponse>(`/api/v1/complaints/${complaintId}/risk`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

/** Triggers the backend's risk + intervention computation (POST). Only
 * called from an explicit user action (a button) in ComplaintDetail.tsx —
 * never automatically on page load — per the integration instructions. */
export async function generateComplaintRisk(complaintId: number): Promise<BackendRiskListResponse> {
  return http.post<BackendRiskListResponse>(`/api/v1/complaints/${complaintId}/risk`);
}

export async function getComplaintInterventionWindow(complaintId: number): Promise<BackendInterventionWindow | null> {
  try {
    return await http.get<BackendInterventionWindow>(`/api/v1/complaints/${complaintId}/intervention-window`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}
