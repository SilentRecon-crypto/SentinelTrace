"""
Stage 7 structured case evidence configuration.

CONTRACT NOTE: `SentinelTrace_Technical_Contract.md` remains unavailable in
this repository (searched exhaustively again before Stage 7 began, same
result as every prior stage). Stage 7's scope was explicitly authorized by
the project owner as "Structured Case Evidence" — references to
already-existing backend outputs attached to a Case, NOT file/document
management. This is a reference/composition layer only: nothing here
computes, duplicates, or stores a second copy of any canonical dataset,
Model A output, graph/explanation, or risk output. Every evidence row
stores only a foreign key (plus, for risk drivers, an optional index into
an already-persisted array) to data that already exists elsewhere.
"""

# ============================================================
# EVIDENCE TYPES — closed set, per explicit authorization. Do not add
# additional types without explicit authorization (see module docstring).
# ============================================================
EVIDENCE_TYPE_TRANSACTION = "transaction_reference"
EVIDENCE_TYPE_GRAPH_EXPLANATION = "graph_explanation_reference"
EVIDENCE_TYPE_RISK_DRIVER = "risk_driver_reference"

EVIDENCE_VALID_TYPES = [
    EVIDENCE_TYPE_TRANSACTION,
    EVIDENCE_TYPE_GRAPH_EXPLANATION,
    EVIDENCE_TYPE_RISK_DRIVER,
]

# ============================================================
# RELEVANCE INVARIANT (deterministic, documented — a design decision made
# during Stage 7 implementation, not dictated by the authorization message,
# but a direct and minimal reading of "reference the existing complaint/
# case investigation context"):
#
# Every piece of evidence attached to a case must directly involve that
# case's OWN complaint_id/account_id (both denormalized onto the case at
# creation time in Stage 6). Concretely:
#   - transaction_reference:        the transaction's src or dst account
#                                    must equal the case's account_id.
#   - graph_explanation_reference:  the referenced prediction row's
#                                    complaint_id AND candidate_account_id
#                                    must equal the case's complaint_id and
#                                    account_id.
#   - risk_driver_reference:        the referenced risk score's
#                                    complaint_id AND account_id must equal
#                                    the case's complaint_id and account_id.
# A reference that exists in the database but fails this relevance check is
# rejected as an "invalid reference target" (422), distinct from a
# reference that doesn't exist at all (404). This prevents an investigator
# from accidentally (or maliciously) attaching an unrelated complaint's
# evidence to this case.
# ============================================================

# ============================================================
# FIELD LIMITS
# ============================================================
EVIDENCE_NOTE_MAX_LENGTH = 4000
EVIDENCE_ADDED_BY_MAX_LENGTH = 128
