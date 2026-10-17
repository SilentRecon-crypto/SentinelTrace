"""
Stage 6 case-management configuration.

CONTRACT NOTE: `SentinelTrace_Technical_Contract.md` is unavailable in this
repository (verified by exhaustive search before Stage 6 work began, same
as Stages 5's own audit found). No contract requirement is invented here.
The status set/transition graph below is the smallest defensible design
consistent with what every prior stage's own scope document says belongs
to "Stage 6 or later": case status/assignment/notes, explicitly WITHOUT
evidence/file management (treated as a separate, later concern in those
same documents). If a real technical contract surfaces later, this file
should be reconciled against it.
"""

# ============================================================
# CASE STATUS LIFECYCLE
# ============================================================
CASE_STATUS_OPEN = "open"
CASE_STATUS_INVESTIGATING = "investigating"
CASE_STATUS_ESCALATED = "escalated"
CASE_STATUS_RESOLVED = "resolved"

CASE_VALID_STATUSES = [
    CASE_STATUS_OPEN,
    CASE_STATUS_INVESTIGATING,
    CASE_STATUS_ESCALATED,
    CASE_STATUS_RESOLVED,
]
CASE_STATUS_DEFAULT = CASE_STATUS_OPEN

# Explicit, centralized transition graph — a status change is legal iff
# new_status is in CASE_STATUS_TRANSITIONS[current_status]. No other Python
# module encodes transition rules. RESOLVED is terminal (no way out via
# this API) by design: reopening a resolved case is a distinct future
# workflow decision this repo has no contract basis to make.
CASE_STATUS_TRANSITIONS: dict[str, list[str]] = {
    CASE_STATUS_OPEN: [CASE_STATUS_INVESTIGATING, CASE_STATUS_ESCALATED, CASE_STATUS_RESOLVED],
    CASE_STATUS_INVESTIGATING: [CASE_STATUS_ESCALATED, CASE_STATUS_RESOLVED],
    CASE_STATUS_ESCALATED: [CASE_STATUS_RESOLVED],
    CASE_STATUS_RESOLVED: [],
}

# ============================================================
# QUEUE ORDERING (mirrors the deterministic-ordering pattern established by
# Stage 5's alert queue in app/services/alert_orchestration.py)
# ============================================================
# Open/investigating/escalated cases should surface before resolved ones in
# the default case queue. Lower number = shown first.
CASE_STATUS_QUEUE_RANK: dict[str, int] = {
    CASE_STATUS_ESCALATED: 0,
    CASE_STATUS_INVESTIGATING: 1,
    CASE_STATUS_OPEN: 2,
    CASE_STATUS_RESOLVED: 3,
}

# ============================================================
# FIELD LIMITS
# ============================================================
CASE_ASSIGNED_TO_MAX_LENGTH = 128   # free-text investigator identifier; no auth/user table exists yet
CASE_NOTE_MAX_LENGTH = 4000
