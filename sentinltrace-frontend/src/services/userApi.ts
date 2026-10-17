// ============================================================
// SENTINELTRACE USER-PORTAL DATA-ACCESS LAYER
//
// Mirrors src/services/api.ts: every function returns a Promise and is the
// only place user-portal pages touch data. Swapping in the real backend
// later (e.g. GET /api/user/complaints, POST /api/user/complaints) means
// editing only this file.
// ============================================================

import { USER_COMPLAINTS, USER_NOTIFICATIONS, USER_PROFILE, buildTimeline } from "@/data/userMockData";
import type { ComplaintTimelineStep, NewComplaintInput, UserComplaint, UserNotification, UserProfileInfo } from "@/types";

const LATENCY_MS = 180;
function resolveAfter<T>(value: T, ms = LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export async function getUserComplaints(): Promise<UserComplaint[]> {
  return resolveAfter([...USER_COMPLAINTS].sort((a, b) => +new Date(b.dateSubmitted) - +new Date(a.dateSubmitted)));
}

export async function getUserComplaint(id: string): Promise<UserComplaint | null> {
  return resolveAfter(USER_COMPLAINTS.find((c) => c.id === id) ?? null);
}

export async function getComplaintTimeline(id: string): Promise<ComplaintTimelineStep[] | null> {
  const complaint = USER_COMPLAINTS.find((c) => c.id === id);
  return resolveAfter(complaint ? buildTimeline(complaint) : null);
}

export async function submitComplaint(input: NewComplaintInput): Promise<UserComplaint> {
  const now = new Date().toISOString();
  const complaint: UserComplaint = {
    id: `UC-${Math.floor(50000 + Math.random() * 9999)}`,
    dateSubmitted: now,
    complaintType: input.complaintType,
    amount: input.amount,
    status: "submitted",
    lastUpdated: now,
    description: input.description,
    referenceInfo: input.referenceInfo,
    contactEmail: input.contactEmail,
    contactPhone: input.contactPhone,
  };
  USER_COMPLAINTS.unshift(complaint);
  return resolveAfter(complaint, 260);
}

export async function getUserNotifications(): Promise<UserNotification[]> {
  return resolveAfter(USER_NOTIFICATIONS);
}

export async function getUserProfile(): Promise<UserProfileInfo> {
  return resolveAfter(USER_PROFILE);
}
