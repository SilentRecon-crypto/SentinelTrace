// ============================================================
// SENTINELTRACE DATA-ACCESS LAYER
//
// Every function here returns a Promise, matching the shape an
// eventual fetch() call against the SentinelTrace FastAPI backend
// would have. Pages and components should only ever import from
// this file (or the hooks in src/hooks that wrap it) — never from
// src/data directly — so that swapping mock data for real API
// calls later requires editing only this file.
//
// Planned backend contract (see spec):
//   GET /api/complaints           -> getComplaints()
//   GET /api/complaints/{id}      -> getComplaint(id)
//   GET /api/accounts             -> getAccounts()
//   GET /api/accounts/{id}        -> getAccount(id)
//   GET /api/networks/{complaint_id} -> getNetwork(complaintId)
//   GET /api/locations            -> getLocations()
//   GET /api/locations/{id}       -> getLocation(id)
//   GET /api/predictions/{complaint_id} -> getPredictions(complaintId)
//   GET /api/model/metrics        -> getModelMetrics()
// ============================================================

import {
  ACCOUNTS,
  ALERTS,
  COMPLAINTS,
  KPI_SUMMARY,
  LAST_ANALYSIS_ISO,
  LOCATIONS,
  MODEL_METRICS,
  SYSTEM_STATUS,
  buildNetworkGraph,
  buildRiskTrend,
} from "@/data/mockData";
import type {
  Account,
  Alert,
  Complaint,
  KPISummary,
  Location,
  ModelMetricSet,
  NetworkGraph,
  PredictionResult,
  RiskTrendPoint,
  SearchResultItem,
  SystemComponentStatus,
} from "@/types";

// Simulated network latency — small and constant so the demo stays snappy,
// but present so loading states are exercised honestly.
const LATENCY_MS = 180;
function resolveAfter<T>(value: T, ms = LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// ---------------------------------------------------------------
// Complaints
// ---------------------------------------------------------------
export async function getComplaints(): Promise<Complaint[]> {
  return resolveAfter(COMPLAINTS);
}
export async function getComplaint(id: string): Promise<Complaint | null> {
  return resolveAfter(COMPLAINTS.find((c) => c.id === id) ?? null);
}

// ---------------------------------------------------------------
// Accounts
// ---------------------------------------------------------------
export async function getAccounts(): Promise<Account[]> {
  return resolveAfter(ACCOUNTS);
}
export async function getAccount(id: string): Promise<Account | null> {
  return resolveAfter(ACCOUNTS.find((a) => a.id === id) ?? null);
}

// ---------------------------------------------------------------
// Locations
// ---------------------------------------------------------------
export async function getLocations(): Promise<Location[]> {
  return resolveAfter(LOCATIONS);
}
export async function getLocation(id: string): Promise<Location | null> {
  return resolveAfter(LOCATIONS.find((l) => l.id === id) ?? null);
}

// ---------------------------------------------------------------
// Network graph
// ---------------------------------------------------------------
export async function getNetwork(complaintId: string): Promise<NetworkGraph> {
  return resolveAfter(buildNetworkGraph(complaintId));
}

// ---------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------
export async function getPredictions(complaintId: string): Promise<PredictionResult> {
  const linked = LOCATIONS.filter((l) => l.linkedComplaintIds.includes(complaintId));
  const pool = linked.length > 0 ? linked : LOCATIONS.slice(0, 8);
  const locations = pool
    .slice()
    .sort((a, b) => b.predictionScore - a.predictionScore)
    .map((l, idx) => ({ rank: idx + 1, locationId: l.id, score: l.predictionScore }));
  const result: PredictionResult = {
    complaintId,
    generatedAt: LAST_ANALYSIS_ISO,
    topLocationId: locations[0]?.locationId ?? "",
    top5ConfidenceAvg: locations.slice(0, 5).reduce((s, l) => s + l.score, 0) / Math.max(1, Math.min(5, locations.length)) / 100,
    candidateCount: pool.length,
    locations,
  };
  return resolveAfter(result);
}

// ---------------------------------------------------------------
// Model performance
// ---------------------------------------------------------------
export async function getModelMetrics(): Promise<ModelMetricSet> {
  return resolveAfter(MODEL_METRICS);
}

// ---------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------
export async function getAlerts(): Promise<Alert[]> {
  return resolveAfter(ALERTS);
}

// ---------------------------------------------------------------
// Dashboard aggregates
// ---------------------------------------------------------------
export async function getKpiSummary(): Promise<KPISummary> {
  return resolveAfter(KPI_SUMMARY);
}
export async function getRiskTrend(range: "24H" | "7D" | "30D" | "90D"): Promise<RiskTrendPoint[]> {
  const config = { "24H": [24, 1], "7D": [28, 6], "30D": [30, 24], "90D": [30, 72] } as const;
  const [points, stepHours] = config[range];
  return resolveAfter(buildRiskTrend(points, stepHours));
}

// ---------------------------------------------------------------
// System status
// ---------------------------------------------------------------
export async function getSystemStatus(): Promise<SystemComponentStatus[]> {
  return resolveAfter(SYSTEM_STATUS);
}

// ---------------------------------------------------------------
// Global search
// ---------------------------------------------------------------
export async function searchAll(query: string): Promise<SearchResultItem[]> {
  const q = query.trim().toLowerCase();
  if (!q) return resolveAfter([], 0);
  const results: SearchResultItem[] = [];

  COMPLAINTS.filter((c) => c.id.toLowerCase().includes(q)).slice(0, 5).forEach((c) =>
    results.push({ id: c.id, type: "complaint", title: c.id, subtitle: `Filed ${new Date(c.filedAt).toLocaleDateString("en-IN")}`, risk: c.risk })
  );
  ACCOUNTS.filter((a) => a.id.toLowerCase().includes(q)).slice(0, 5).forEach((a) =>
    results.push({ id: a.id, type: "account", title: a.id, subtitle: `Risk score ${a.riskScore.toFixed(1)}%`, risk: a.risk })
  );
  LOCATIONS.filter((l) => l.id.toLowerCase().includes(q) || l.city.toLowerCase().includes(q)).slice(0, 5).forEach((l) =>
    results.push({ id: l.id, type: "location", title: l.id, subtitle: `${l.city}, ${l.state}`, risk: l.risk })
  );

  return resolveAfter(results, 90);
}
