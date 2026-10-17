import { createRng, pick, randInt, randFloat } from "@/utils/seededRandom";
import { CITIES, MODEL_A_FEATURES } from "@/data/reference";
import type {
  Account,
  Alert,
  Complaint,
  KPISummary,
  Location,
  ModelMetricSet,
  NetworkGraph,
  RiskLevel,
  RiskTrendPoint,
  SystemComponentStatus,
} from "@/types";

const NOW = new Date("2026-09-04T11:24:31+05:30");
const rng = createRng(20260904);

function isoMinutesAgo(mins: number): string {
  return new Date(NOW.getTime() - mins * 60000).toISOString();
}
function isoDaysAgo(days: number): string {
  return new Date(NOW.getTime() - days * 86400000).toISOString();
}

function riskFromScore(score: number): RiskLevel {
  if (score >= 85) return "critical";
  if (score >= 65) return "high";
  if (score >= 40) return "medium";
  return "low";
}

// ---------------------------------------------------------------
// ACCOUNTS
// ---------------------------------------------------------------
const ACCOUNT_COUNT = 64;
export const ACCOUNTS: Account[] = [];

for (let i = 0; i < ACCOUNT_COUNT; i++) {
  const id = `ACC-${10001 + i}`;
  const riskScore = i === 0 ? 94.7 : Math.max(12, Math.min(98, randFloat(rng, 8, 97, 1)));
  const risk = riskFromScore(riskScore);
  const hopDistance = i === 0 ? 3 : randInt(rng, 1, 6);
  const passThroughRatio = i === 0 ? 0.92 : randFloat(rng, 0.05, 0.97, 2);
  const recentFanIn = i === 0 ? 14 : randInt(rng, 0, 22);
  const outDegree = i === 0 ? 8 : randInt(rng, 0, 15);
  const amountConsistency = i === 0 ? 0.88 : randFloat(rng, 0.1, 0.98, 2);
  const centrality = i === 0 ? 0.71 : randFloat(rng, 0.02, 0.9, 2);
  const accountAgeDays = i === 0 ? 42 : randInt(rng, 3, 1800);
  const transactionCount = randInt(rng, 4, 260);
  const incomingVolume = randInt(rng, 5000, 4200000);
  const outgoingVolume = Math.round(incomingVolume * amountConsistency * randFloat(rng, 0.85, 1.05, 2));

  ACCOUNTS.push({
    id,
    riskScore,
    risk,
    hopDistance,
    passThroughRatio,
    recentFanIn,
    outDegree,
    amountConsistency,
    centrality,
    accountAgeDays,
    status: risk,
    transactionCount,
    incomingVolume,
    outgoingVolume,
    fanIn: recentFanIn + randInt(rng, 0, 6),
    fanOut: outDegree + randInt(rng, 0, 4),
    lastActivity: isoMinutesAgo(randInt(rng, 4, 8000)),
    linkedComplaintIds: [],
    riskFactors: buildRiskFactors(risk, passThroughRatio, centrality, hopDistance),
    modelVersion: "Model A",
  });
}
ACCOUNTS.sort((a, b) => b.riskScore - a.riskScore);

function buildRiskFactors(risk: RiskLevel, ptr: number, cen: number, hop: number): string[] {
  const factors: string[] = [];
  if (ptr > 0.7) factors.push("High pass-through behavior");
  if (cen > 0.55) factors.push("Strong network centrality");
  if (hop <= 3) factors.push("Multi-hop transaction involvement");
  factors.push("Recent fan-in activity");
  if (risk === "critical" || risk === "high") factors.push("Amount consistency with suspicious flow");
  return factors;
}

const heroAccount = ACCOUNTS.find((a) => a.id === "ACC-10001")!;
heroAccount.id = "ACC-10482";

// give the hero a couple of named chain accomplices with plausible scores
const chainB = ACCOUNTS[1];
chainB.id = "ACC-11037";
chainB.riskScore = 81.3;
chainB.risk = "high";
chainB.hopDistance = 2;

const chainC = ACCOUNTS[2];
chainC.id = "ACC-11842";
chainC.riskScore = 68.9;
chainC.risk = "high";
chainC.hopDistance = 1;

// ---------------------------------------------------------------
// LOCATIONS
// ---------------------------------------------------------------
const LOCATION_TYPES = ["atm", "branch", "agent"] as const;
const LOCATION_COUNT = 34;
export const LOCATIONS: Location[] = [];

const CITY_BY_NAME = Object.fromEntries(CITIES.map((c) => [c.city, c]));
const usedLocationNumbers = new Set<number>([84, 31, 67]);
function nextLocationNumber(): number {
  let n = randInt(rng, 100, 999);
  while (usedLocationNumbers.has(n)) n = randInt(rng, 100, 999);
  usedLocationNumbers.add(n);
  return n;
}

for (let i = 0; i < LOCATION_COUNT; i++) {
  const isHeroLoc = i < 3;
  // Hero locations (top 3, used throughout the demo walkthrough) get fixed,
  // named cities so their coordinates always match their displayed city.
  const cityInfo = i === 0 ? CITY_BY_NAME["New Delhi"] : i === 1 ? CITY_BY_NAME["Noida"] : i === 2 ? CITY_BY_NAME["Lucknow"] : pick(rng, CITIES);
  const type = pick(rng, LOCATION_TYPES);
  const predictionScore = i === 0 ? 92.4 : i === 1 ? 88.7 : i === 2 ? 84.2 : randFloat(rng, 8, 80, 1);
  const risk = riskFromScore(predictionScore);
  // Hero markers use precise city-center coordinates; the rest get a small
  // realistic jitter (~1-2km) so multiple locations in one city don't overlap exactly.
  const jitter = isHeroLoc ? 0 : randFloat(rng, -0.018, 0.018, 4);
  const jitter2 = isHeroLoc ? 0 : randFloat(rng, -0.018, 0.018, 4);
  LOCATIONS.push({
    id: `LOC-${String(i === 0 ? 84 : i === 1 ? 31 : i === 2 ? 67 : nextLocationNumber()).padStart(3, "0")}`,
    type,
    name:
      type === "atm"
        ? `${cityInfo.city} ${pick(rng, ["Sector", "MG Road", "Central", "Station Road", "Ring Road"])} ATM`
        : type === "branch"
        ? `${cityInfo.city} ${pick(rng, ["Main Branch", "City Branch", "Central Branch"])}`
        : `${cityInfo.city} Banking Correspondent`,
    city: cityInfo.city,
    state: cityInfo.state,
    predictionScore,
    rank: i + 1,
    distanceKm: i === 0 ? 1.8 : randFloat(rng, 0.4, 42, 1),
    historicalFraudCount: randInt(rng, 0, 19),
    recentActivityCount: randInt(rng, 0, 40),
    aggregatedTopKScore: randFloat(rng, 0.1, 0.97, 2),
    risk,
    lat: cityInfo.lat + jitter,
    lng: cityInfo.lng + jitter2,
    linkedComplaintIds: [],
  });
}
LOCATIONS.sort((a, b) => b.predictionScore - a.predictionScore);
LOCATIONS.forEach((l, i) => (l.rank = i + 1));

// ---------------------------------------------------------------
// COMPLAINTS
// ---------------------------------------------------------------
const COMPLAINT_COUNT = 42;
const STATUSES = ["new", "under_investigation", "escalated", "monitoring", "resolved"] as const;
export const COMPLAINTS: Complaint[] = [];

for (let i = 0; i < COMPLAINT_COUNT; i++) {
  const isHero = i === 0;
  const id = isHero ? "CMP-10482" : `CMP-${10001 + i}`;
  const chainDepth = isHero ? 3 : randInt(rng, 1, 5);
  const amount = isHero ? 48500 : randInt(rng, 2500, 620000);
  const risk: RiskLevel = isHero ? "high" : riskFromScore(randFloat(rng, 5, 99, 1));
  const status = isHero ? "under_investigation" : pick(rng, STATUSES);
  const topAccountId = isHero ? "ACC-10482" : pick(rng, ACCOUNTS).id;
  const chain = isHero
    ? ["ACC-10482", "ACC-11037", "ACC-11842"]
    : Array.from({ length: chainDepth }, () => pick(rng, ACCOUNTS).id);

  COMPLAINTS.push({
    id,
    filedAt: isHero ? "2026-09-04T09:41:00+05:30" : isoDaysAgo(randInt(rng, 0, 60)),
    amount,
    risk,
    suspiciousAccountCount: chain.length,
    chainDepth,
    predictedLocationCount: isHero ? 5 : randInt(rng, 1, 8),
    status,
    victimRef: `VIC-${randInt(rng, 100000, 999999)}`,
    summary: isHero
      ? "The transaction graph indicates a multi-hop flow through 3 intermediary accounts. Account ACC-10482 currently has the highest model score. Three locations show elevated predicted cash-out risk."
      : `Transaction graph indicates a ${chainDepth}-hop flow through intermediary accounts. Account ${topAccountId} currently holds the highest model score for this complaint.`,
    accountChain: chain,
    topAccountId,
  });
}

// link accounts back to complaints
COMPLAINTS.forEach((c) => {
  c.accountChain.forEach((accId) => {
    const acc = ACCOUNTS.find((a) => a.id === accId);
    if (acc && !acc.linkedComplaintIds.includes(c.id)) acc.linkedComplaintIds.push(c.id);
  });
});
LOCATIONS.slice(0, 5).forEach((l) => l.linkedComplaintIds.push("CMP-10482"));

// ---------------------------------------------------------------
// NETWORK GRAPH (hero + generated per complaint)
// ---------------------------------------------------------------
export function buildNetworkGraph(complaintId: string): NetworkGraph {
  const complaint = COMPLAINTS.find((c) => c.id === complaintId);
  if (!complaint) {
    return { complaintId, nodes: [], edges: [], tracePathNodeIds: [] };
  }
  const nodes: NetworkGraph["nodes"] = [];
  const edges: NetworkGraph["edges"] = [];

  nodes.push({ id: complaint.victimRef, type: "victim", label: complaint.victimRef });
  nodes.push({ id: complaint.id, type: "complaint", label: complaint.id });
  edges.push({ id: `e-${complaint.victimRef}-${complaint.id}`, source: complaint.victimRef, target: complaint.id, type: "reports" });

  let prev = complaint.id;
  complaint.accountChain.forEach((accId, idx) => {
    const acc = ACCOUNTS.find((a) => a.id === accId);
    nodes.push({
      id: accId,
      type: "account",
      label: accId,
      risk: acc?.risk,
      meta: acc
        ? { "Risk Score": `${acc.riskScore.toFixed(1)}%`, Connections: acc.fanIn + acc.fanOut, Incoming: acc.fanIn, Outgoing: acc.fanOut, Centrality: acc.centrality }
        : undefined,
    });
    edges.push({
      id: `e-${prev}-${accId}`,
      source: prev,
      target: accId,
      type: idx === 0 ? "initiates" : "transaction",
      amount: Math.round(complaint.amount * randFloat(rng, 0.7, 1, 2)),
      onTracePath: true,
    });
    prev = accId;
  });

  const linkedLocations = LOCATIONS.filter((l) => l.linkedComplaintIds.includes(complaintId));
  const finalLocations = linkedLocations.length > 0 ? linkedLocations : LOCATIONS.slice(0, 3);
  finalLocations.forEach((loc) => {
    nodes.push({
      id: loc.id,
      type: "location",
      label: `${loc.id} · ${loc.city}`,
      risk: loc.risk,
      meta: { "Prediction Score": `${loc.predictionScore.toFixed(1)}%`, Type: loc.type },
    });
    edges.push({
      id: `e-${prev}-${loc.id}`,
      source: prev,
      target: loc.id,
      type: "cashout",
      onTracePath: loc.id === finalLocations[0].id,
    });
  });

  return {
    complaintId,
    nodes,
    edges,
    tracePathNodeIds: [complaint.victimRef, complaint.id, ...complaint.accountChain, finalLocations[0]?.id].filter(Boolean),
  };
}

// ---------------------------------------------------------------
// ALERTS
// ---------------------------------------------------------------
export const ALERTS: Alert[] = [
  {
    id: "ALT-0001",
    severity: "critical",
    title: "Account crossed risk threshold",
    detail: "Account ACC-10482 crossed the high-risk threshold with a model score of 94.7%.",
    timestamp: isoMinutesAgo(6),
    entityType: "account",
    entityId: "ACC-10482",
    read: false,
  },
  {
    id: "ALT-0002",
    severity: "high",
    title: "Location entered top-5 predictions",
    detail: "LOC-084 (New Delhi) entered the top-5 predicted cash-out locations for CMP-10482.",
    timestamp: isoMinutesAgo(11),
    entityType: "location",
    entityId: "LOC-084",
    read: false,
  },
  {
    id: "ALT-0003",
    severity: "medium",
    title: "Complaint requires review",
    detail: "Complaint CMP-10481 has remained in New status for 48 hours and requires review.",
    timestamp: isoMinutesAgo(38),
    entityType: "complaint",
    entityId: "CMP-10001",
    read: false,
  },
  {
    id: "ALT-0004",
    severity: "high",
    title: "New multi-hop transaction chain detected",
    detail: "A new 3-hop transaction chain was detected originating from complaint CMP-10482.",
    timestamp: isoMinutesAgo(63),
    entityType: "network",
    entityId: "CMP-10482",
    read: true,
  },
  {
    id: "ALT-0005",
    severity: "info",
    title: "Suspicious-account ranking updated",
    detail: "Complaint CMP-10482 generated a new suspicious-account ranking.",
    timestamp: isoMinutesAgo(94),
    entityType: "complaint",
    entityId: "CMP-10482",
    read: true,
  },
  {
    id: "ALT-0006",
    severity: "medium",
    title: "Account age flag",
    detail: "Account ACC-11037 opened 9 days ago and has already exceeded typical transaction volume.",
    timestamp: isoMinutesAgo(140),
    entityType: "account",
    entityId: "ACC-11037",
    read: true,
  },
];

// ---------------------------------------------------------------
// KPI SUMMARY
// ---------------------------------------------------------------
export const KPI_SUMMARY: KPISummary = {
  activeComplaints: 8421,
  activeComplaintsChangePct: 12.4,
  highRiskAccounts: 1153,
  highRiskAccountsChangePct: 8.2,
  predictedCashOutLocations: 87,
  highConfidencePredictions: 64,
  investigationsRequiringAction: 27,
};

// ---------------------------------------------------------------
// RISK TREND (for dashboard chart)
// ---------------------------------------------------------------
export function buildRiskTrend(points: number, stepHours: number): RiskTrendPoint[] {
  const out: RiskTrendPoint[] = [];
  for (let i = points - 1; i >= 0; i--) {
    const t = new Date(NOW.getTime() - i * stepHours * 3600000);
    const base = 40 + Math.sin(i / 4) * 10;
    out.push({
      timestamp: t.toISOString(),
      critical: Math.max(2, Math.round(base * 0.18 + randFloat(rng, -3, 3, 0))),
      high: Math.max(4, Math.round(base * 0.32 + randFloat(rng, -4, 4, 0))),
      medium: Math.max(6, Math.round(base * 0.34 + randFloat(rng, -5, 5, 0))),
      low: Math.max(3, Math.round(base * 0.16 + randFloat(rng, -3, 3, 0))),
    });
  }
  return out;
}

// ---------------------------------------------------------------
// MODEL METRICS
// ---------------------------------------------------------------
export const MODEL_METRICS: ModelMetricSet = {
  modelVersion: "Model A",
  precisionAt1: 60.0,
  precisionAt5: 24.0,
  recallAt5: 93.9,
  mrr: 87.9,
  baseline: {
    precisionAt1: 40.0,
    precisionAt5: 21.3,
    recallAt5: 84.8,
    mrr: 75.8,
  },
  evaluation: {
    complaintCount: 15,
    candidateAccountCount: 1153,
    positiveTargetCount: 20,
  },
  features: MODEL_A_FEATURES,
};

// ---------------------------------------------------------------
// SYSTEM STATUS
// ---------------------------------------------------------------
export const SYSTEM_STATUS: SystemComponentStatus[] = [
  { name: "Graph Engine", status: "operational", detail: "Transaction graph construction and traversal" },
  { name: "Model A", status: "operational", detail: "Suspicious-account ranking model" },
  { name: "Data Pipeline", status: "operational", detail: "Synthetic complaint and transaction ingestion" },
  { name: "Database", status: "operational", detail: "Entity and evaluation storage" },
  { name: "API", status: "standby", detail: "Backend not yet connected — frontend running on mock data" },
];

export const LAST_ANALYSIS_ISO = "2026-09-04T11:18:00+05:30";
