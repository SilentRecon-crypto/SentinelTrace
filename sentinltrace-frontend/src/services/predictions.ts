// ============================================================
// Real backend Model A predictions — GET /api/v1/complaints/{id}/mule-chain
//
// This endpoint returns 404 for two distinct, legitimate reasons: (a) the
// complaint doesn't exist, or (b) the complaint exists but no Model A
// prediction has been generated for it yet (the backend requires
// POST /predictions/run first — a mutating call this integration slice
// does not perform, per scope). Callers of getMuleChainPrediction() are
// expected to have already confirmed the complaint exists via
// getComplaintById() (see ComplaintDetail.tsx), so a 404 here is treated
// unambiguously as "no prediction yet" and resolved to `null` rather than
// thrown — the page shows a neutral empty state, not an error state.
// ============================================================
import type { BackendPredictionRunResponse } from "@/services/backendTypes";
import { ApiError, http } from "@/services/httpClient";

export async function getMuleChainPrediction(complaintId: number): Promise<BackendPredictionRunResponse | null> {
  try {
    return await http.get<BackendPredictionRunResponse>(`/api/v1/complaints/${complaintId}/mule-chain`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}
