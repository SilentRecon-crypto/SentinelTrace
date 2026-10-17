// ============================================================
// Real backend connectivity check — GET /api/v1/health
// ============================================================
import type { BackendHealth } from "@/services/backendTypes";
import { http } from "@/services/httpClient";

export async function getHealth(): Promise<BackendHealth> {
  return http.get<BackendHealth>("/api/v1/health");
}
