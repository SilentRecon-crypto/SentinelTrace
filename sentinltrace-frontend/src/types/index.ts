// ============================================================
// SENTINELTRACE — DOMAIN TYPES
// These types define the contract between the frontend and the
// eventual SentinelTrace Python/FastAPI backend. Mock data in
// src/data conforms to these shapes; services in src/services
// return these shapes so the data layer can later be swapped
// for real API calls without touching UI components.
// ============================================================

export type RiskLevel = "critical" | "high" | "medium" | "low";

export type ComplaintStatus =
  | "new"
  | "under_investigation"
  | "escalated"
  | "monitoring"
  | "resolved";

export type LocationType = "atm" | "branch" | "agent";

export interface Complaint {
  id: string; // CMP-xxxxx
  filedAt: string; // ISO timestamp
  amount: number; // INR
  risk: RiskLevel;
  suspiciousAccountCount: number;
  chainDepth: number;
  predictedLocationCount: number;
  status: ComplaintStatus;
  victimRef: string; // synthetic, non-identifying
  summary: string;
  accountChain: string[]; // ordered account IDs, complaint -> ... -> final hop
  topAccountId: string;
}

export interface Account {
  id: string; // ACC-xxxxx
  riskScore: number; // 0-100
  risk: RiskLevel;
  hopDistance: number;
  passThroughRatio: number; // 0-1
  recentFanIn: number;
  outDegree: number;
  amountConsistency: number; // 0-1
  centrality: number; // 0-1
  accountAgeDays: number;
  status: RiskLevel | "cleared";
  transactionCount: number;
  incomingVolume: number;
  outgoingVolume: number;
  fanIn: number;
  fanOut: number;
  lastActivity: string; // ISO timestamp
  linkedComplaintIds: string[];
  riskFactors: string[];
  modelVersion: "Model A";
}

export interface Transaction {
  id: string; // TXN-xxxxx
  fromAccountId: string;
  toAccountId: string;
  amount: number;
  timestamp: string;
  channel: "IMPS" | "NEFT" | "UPI" | "RTGS";
}

export interface Location {
  id: string; // LOC-xxx
  type: LocationType;
  name: string;
  city: string;
  state: string;
  predictionScore: number; // 0-100
  rank: number;
  distanceKm: number;
  historicalFraudCount: number;
  recentActivityCount: number;
  aggregatedTopKScore: number; // 0-1
  risk: RiskLevel;
  lat: number;
  lng: number;
  linkedComplaintIds: string[];
}

export interface PredictionResult {
  complaintId: string;
  generatedAt: string;
  topLocationId: string;
  top5ConfidenceAvg: number; // 0-1
  candidateCount: number;
  locations: {
    rank: number;
    locationId: string;
    score: number; // 0-100
  }[];
}

export type NetworkNodeType = "victim" | "account" | "complaint" | "location";
export type NetworkEdgeType = "reports" | "initiates" | "transaction" | "cashout";

export interface NetworkNode {
  id: string;
  type: NetworkNodeType;
  label: string;
  risk?: RiskLevel;
  x?: number;
  y?: number;
  meta?: Record<string, string | number>;
}

export interface NetworkEdge {
  id: string;
  source: string;
  target: string;
  type: NetworkEdgeType;
  amount?: number;
  onTracePath?: boolean;
}

export interface NetworkGraph {
  complaintId: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  tracePathNodeIds: string[]; // highlighted suspicious chain
}

export type AlertSeverity = "critical" | "high" | "medium" | "info";

export interface Alert {
  id: string;
  severity: AlertSeverity;
  title: string;
  detail: string;
  timestamp: string;
  entityType: "account" | "location" | "complaint" | "network";
  entityId: string;
  read: boolean;
}

export interface ModelMetricSet {
  modelVersion: "Model A";
  precisionAt1: number;
  precisionAt5: number;
  recallAt5: number;
  mrr: number;
  baseline: {
    precisionAt1: number;
    precisionAt5: number;
    recallAt5: number;
    mrr: number;
  };
  evaluation: {
    complaintCount: number;
    candidateAccountCount: number;
    positiveTargetCount: number;
  };
  features: {
    key: string;
    label: string;
    description: string;
  }[];
}

export interface RiskTrendPoint {
  timestamp: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface SystemComponentStatus {
  name: string;
  status: "operational" | "standby" | "degraded" | "offline";
  detail: string;
}

export interface InvestigationPin {
  id: string;
  entityType: "account" | "complaint" | "location";
  entityId: string;
  label: string;
  risk?: RiskLevel;
  pinnedAt: string;
  note?: string;
}

export interface Analyst {
  id: string;
  name: string;
  handle: string;
  unit: string;
}

export interface KPISummary {
  activeComplaints: number;
  activeComplaintsChangePct: number;
  highRiskAccounts: number;
  highRiskAccountsChangePct: number;
  predictedCashOutLocations: number;
  highConfidencePredictions: number;
  investigationsRequiringAction: number;
}

export interface SearchResultItem {
  id: string;
  type: "complaint" | "account" | "transaction" | "location";
  title: string;
  subtitle: string;
  risk?: RiskLevel;
}

// ============================================================
// USER PORTAL TYPES
//
// Deliberately separate from the analyst Complaint type above: citizen
// users only ever see their own submission and its public status, never
// internal fields like risk score, suspicious-account chain, or predicted
// cash-out locations.
// ============================================================

export type UserComplaintStatus = "submitted" | "under_review" | "investigation_in_progress" | "resolved";

export interface UserComplaint {
  id: string;
  dateSubmitted: string;
  complaintType: string;
  amount: number;
  status: UserComplaintStatus;
  lastUpdated: string;
  description: string;
  referenceInfo?: string;
  contactEmail: string;
  contactPhone?: string;
}

export interface ComplaintTimelineStep {
  label: string;
  timestamp: string | null;
  complete: boolean;
  note?: string;
}

export interface UserNotification {
  id: string;
  title: string;
  detail: string;
  timestamp: string;
  read: boolean;
  relatedComplaintId?: string;
}

export interface UserProfileInfo {
  name: string;
  email: string;
  phone: string;
  memberSince: string;
}

export interface NewComplaintInput {
  complaintType: string;
  incidentDate: string;
  amount: number;
  description: string;
  referenceInfo?: string;
  contactEmail: string;
  contactPhone?: string;
}
