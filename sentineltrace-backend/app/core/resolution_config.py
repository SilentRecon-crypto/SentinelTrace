"""
Stage 8 case-resolution configuration.

CONTRACT NOTE: `SentinelTrace_Technical_Contract.md` remains unavailable
(searched exhaustively again before Stage 8 began, same result as every
prior stage). Unlike Stage 7's "smallest defensible design" situation,
Stage 8's scope, outcome-type set, and exact business rules were EXPLICITLY
authorized by the project owner in full detail — nothing below is inferred
or guessed; it is a direct transcription of that authorization into code.

LEAKAGE DISTINCTION (critical, stated explicitly per the authorization):
The outcome types below are INVESTIGATOR-RECORDED real-world judgments made
after Stage 6 case work. They are NOT, and must never be confused with,
this project's synthetic dataset's hidden ground-truth role labels (`mule`,
`legit_low`, `legit_high`, `hub`, `confusor`, `adversarial_bait`) or
Model A's training/evaluation `label`/`chain` fields. `confirmed_mule`
sounds similar to the synthetic `mule` role by design — that is the whole
point of building a REAL resolved-case ledger as a future alternative data
source to the synthetic labels, not a leak of them. Nothing in this module
or app/services/resolution_engine.py reads `label`/`chain`/`acc_type`.
"""

# ============================================================
# OUTCOME TYPES — exact closed set, authorized. Do not add without explicit
# authorization.
# ============================================================
OUTCOME_TYPE_CONFIRMED_MULE = "confirmed_mule"
OUTCOME_TYPE_FALSE_POSITIVE = "false_positive"
OUTCOME_TYPE_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
OUTCOME_TYPE_REFERRED_EXTERNAL = "referred_external"

RESOLUTION_VALID_OUTCOME_TYPES = [
    OUTCOME_TYPE_CONFIRMED_MULE,
    OUTCOME_TYPE_FALSE_POSITIVE,
    OUTCOME_TYPE_INSUFFICIENT_EVIDENCE,
    OUTCOME_TYPE_REFERRED_EXTERNAL,
]

# ============================================================
# BUSINESS RULE: a resolution may only be created for a case whose current
# status is exactly this value. Sourced directly from
# app.core.case_config.CASE_STATUS_RESOLVED (a READ-ONLY import — this
# module does not modify case_config.py, which remains frozen) rather than
# duplicated as an independent string literal, so the two can never drift.
# ============================================================
from app.core.case_config import CASE_STATUS_RESOLVED as REQUIRED_CASE_STATUS  # noqa: E402

# ============================================================
# FIELD LIMITS
# ============================================================
RESOLUTION_NOTE_MAX_LENGTH = 4000
RESOLUTION_RECORDED_BY_MAX_LENGTH = 128

# ============================================================
# EXPLICITLY DEFERRED (documented here so the boundary is visible from the
# config module itself, not just the README): this ledger is NOT wired into
# candidate_generation.py's or risk_engine.py's `confirmed_history_count`,
# Model A scoring, Model A features, prediction generation, graph
# generation, or risk calculation. Consuming this ledger from any of those
# is a separately-authorized future stage requiring Model A parity
# re-verification. Stage 8 only builds and populates the ledger.
# ============================================================
