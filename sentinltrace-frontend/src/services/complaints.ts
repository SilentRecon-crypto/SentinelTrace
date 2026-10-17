// ============================================================
// Real backend complaints service — GET /api/v1/complaints[/{id}]
//
// sanitizeComplaint() explicitly PICKS only the allowed fields off the raw
// JSON response rather than passing the fetched object through as-is. The
// backend's raw response also contains `chain`/`used_shared_pool`/`mode`/
// `missing_hop_idx` (see src/services/backendTypes.ts's file header for
// why those are excluded) — this function is the point where those extra
// keys are dropped from memory, not just from the TypeScript type, so a
// stray `console.log(complaint)` or JSON.stringify elsewhere can never
// accidentally surface them either.
// ============================================================
import type { BackendComplaint, BackendComplaintListResponse } from "@/services/backendTypes";
import { http } from "@/services/httpClient";

function sanitizeComplaint(raw: BackendComplaint): BackendComplaint {
  return {
    complaint_id: raw.complaint_id,
    victim: raw.victim,
    day: raw.day,
    fraud_amount: raw.fraud_amount,
    n_hops: raw.n_hops,
  };
}

export async function getComplaintsPage(limit = 50, offset = 0): Promise<BackendComplaintListResponse> {
  const res = await http.get<BackendComplaintListResponse>(`/api/v1/complaints?limit=${limit}&offset=${offset}`);
  return { ...res, items: res.items.map(sanitizeComplaint) };
}

export async function getComplaintById(complaintId: number): Promise<BackendComplaint> {
  const res = await http.get<BackendComplaint>(`/api/v1/complaints/${complaintId}`);
  return sanitizeComplaint(res);
}

/** Consistent with the existing mock "CMP-xxxxx" visual convention — pure display formatting, not fabricated data. */
export function formatComplaintId(complaintId: number): string {
  return `CMP-${String(complaintId).padStart(5, "0")}`;
}
