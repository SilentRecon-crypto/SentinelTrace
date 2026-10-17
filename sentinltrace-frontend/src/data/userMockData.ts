import type { ComplaintTimelineStep, UserComplaint, UserComplaintStatus, UserNotification, UserProfileInfo } from "@/types";

const NOW = new Date("2026-09-04T11:24:31+05:30");
function daysAgo(d: number): string {
  return new Date(NOW.getTime() - d * 86400000).toISOString();
}

export const USER_PROFILE: UserProfileInfo = {
  name: "Demo Citizen",
  email: "citizen.demo@example.com",
  phone: "+91 98XXXXXX10",
  memberSince: daysAgo(210),
};

// In-memory store so newly submitted complaints show up immediately in the
// session, without pretending to persist anything server-side.
export const USER_COMPLAINTS: UserComplaint[] = [
  {
    id: "UC-58213",
    dateSubmitted: daysAgo(21),
    complaintType: "UPI Fraud",
    amount: 48500,
    status: "investigation_in_progress",
    lastUpdated: daysAgo(2),
    description: "Unauthorized UPI transfer from my account after a phishing call impersonating my bank.",
    referenceInfo: "UPI Ref 402281XXXXXX",
    contactEmail: USER_PROFILE.email,
    contactPhone: USER_PROFILE.phone,
  },
  {
    id: "UC-58019",
    dateSubmitted: daysAgo(64),
    complaintType: "Fake Investment App",
    amount: 125000,
    status: "under_review",
    lastUpdated: daysAgo(30),
    description: "Invested through an app that stopped allowing withdrawals after an initial payout.",
    contactEmail: USER_PROFILE.email,
  },
  {
    id: "UC-57402",
    dateSubmitted: daysAgo(150),
    complaintType: "Card Skimming",
    amount: 15200,
    status: "resolved",
    lastUpdated: daysAgo(120),
    description: "Unrecognized card-present transactions at an ATM I did not use.",
    contactEmail: USER_PROFILE.email,
  },
  {
    id: "UC-56988",
    dateSubmitted: daysAgo(3),
    complaintType: "Job Scam",
    amount: 9000,
    status: "submitted",
    lastUpdated: daysAgo(3),
    description: "Paid a 'registration fee' for a work-from-home job offer that turned out to be fake.",
    contactEmail: USER_PROFILE.email,
  },
];

export const USER_NOTIFICATIONS: UserNotification[] = [
  { id: "UN-1", title: "Complaint status updated", detail: "UC-58213 moved to Investigation in Progress.", timestamp: daysAgo(2), read: false, relatedComplaintId: "UC-58213" },
  { id: "UN-2", title: "Complaint received", detail: "UC-56988 has been received and is queued for review.", timestamp: daysAgo(3), read: false, relatedComplaintId: "UC-56988" },
  { id: "UN-3", title: "Complaint resolved", detail: "UC-57402 has been marked resolved.", timestamp: daysAgo(120), read: true, relatedComplaintId: "UC-57402" },
  { id: "UN-4", title: "Welcome to SentinelTrace", detail: "You can track any complaint's status from My Complaints at any time.", timestamp: daysAgo(210), read: true },
];

const STATUS_STEPS: UserComplaintStatus[] = ["submitted", "under_review", "investigation_in_progress", "resolved"];
const STEP_LABELS: Record<UserComplaintStatus, string> = {
  submitted: "Complaint Submitted",
  under_review: "Complaint Received",
  investigation_in_progress: "Under Investigation",
  resolved: "Resolved",
};

export function buildTimeline(complaint: UserComplaint): ComplaintTimelineStep[] {
  const currentIdx = STATUS_STEPS.indexOf(complaint.status);
  const steps: ComplaintTimelineStep[] = STATUS_STEPS.map((status, i) => ({
    label: STEP_LABELS[status],
    timestamp: i === 0 ? complaint.dateSubmitted : i <= currentIdx ? complaint.lastUpdated : null,
    complete: i <= currentIdx,
  }));
  if (complaint.status === "investigation_in_progress") {
    steps.splice(3, 0, { label: "Investigation Update", timestamp: complaint.lastUpdated, complete: true, note: "An investigator has reviewed linked transaction activity." });
  }
  return steps;
}
