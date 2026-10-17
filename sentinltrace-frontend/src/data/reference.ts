export const CITIES: { city: string; state: string; lat: number; lng: number }[] = [
  { city: "New Delhi", state: "Delhi", lat: 28.6139, lng: 77.209 },
  { city: "Noida", state: "Uttar Pradesh", lat: 28.5355, lng: 77.391 },
  { city: "Lucknow", state: "Uttar Pradesh", lat: 26.8467, lng: 80.9462 },
  { city: "Mumbai", state: "Maharashtra", lat: 19.076, lng: 72.8777 },
  { city: "Bengaluru", state: "Karnataka", lat: 12.9716, lng: 77.5946 },
  { city: "Hyderabad", state: "Telangana", lat: 17.385, lng: 78.4867 },
  { city: "Jaipur", state: "Rajasthan", lat: 26.9124, lng: 75.7873 },
  { city: "Kolkata", state: "West Bengal", lat: 22.5726, lng: 88.3639 },
  { city: "Pune", state: "Maharashtra", lat: 18.5204, lng: 73.8567 },
  { city: "Ahmedabad", state: "Gujarat", lat: 23.0225, lng: 72.5714 },
  { city: "Chandigarh", state: "Chandigarh", lat: 30.7333, lng: 76.7794 },
  { city: "Patna", state: "Bihar", lat: 25.5941, lng: 85.1376 },
];

export const LOCATION_TYPE_LABEL: Record<string, string> = {
  atm: "ATM",
  branch: "Branch",
  agent: "Agent",
};

export const MODEL_A_FEATURES = [
  {
    key: "hopDistance",
    label: "Hop Distance",
    description: "Number of transaction hops between the originating complaint and this account in the transaction graph.",
  },
  {
    key: "passThroughRatio",
    label: "Pass-Through Ratio",
    description: "Measures how strongly an account exhibits pass-through behavior — funds arriving and leaving in similar amounts, within a short window.",
  },
  {
    key: "recentFanIn",
    label: "Recent Fan-In",
    description: "Number of distinct accounts that have recently sent funds into this account.",
  },
  {
    key: "outDegree",
    label: "Recent Out-Degree",
    description: "Number of distinct accounts this account has recently sent funds to.",
  },
  {
    key: "amountConsistency",
    label: "Amount Consistency",
    description: "How closely outgoing transaction amounts track incoming amounts, adjusted for typical service fees.",
  },
  {
    key: "centrality",
    label: "Subgraph Degree Centrality",
    description: "The account's structural importance within its local transaction subgraph, relative to connected accounts.",
  },
  {
    key: "accountAgeDays",
    label: "Account Age",
    description: "Number of days since the account was opened. Newer accounts carry elevated risk weighting.",
  },
];

export const MODEL_B_FEATURES = [
  { key: "minDistanceTopK", label: "Minimum Distance to Top-K Account" },
  { key: "historicalFraudCount", label: "Historical Fraud Count" },
  { key: "recentActivity", label: "Recent Activity" },
  { key: "locationType", label: "Location Type" },
  { key: "aggregatedTopKScore", label: "Aggregated Top-K Score" },
];
