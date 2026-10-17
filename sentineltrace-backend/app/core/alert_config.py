"""
Stage 5 alert generation + prioritization configuration.

Every threshold, weight, category name, and status value used by
app/services/alert_engine.py and app/services/alert_orchestration.py lives
here — nothing is scattered inline in those modules, matching the pattern
established for the risk engine in app/core/risk_config.py.

CONTRACT NOTE: no `SentinelTrace_Technical_Contract.md` file was found
anywhere in this repository or the surrounding filesystem when Stage 5 was
started (searched exhaustively before writing any code). Per the Stage 5
brief's own fallback rule ("if the contract leaves details unspecified,
create the smallest defensible alert model/policy"), the values below are
an explicit, documented, smallest-defensible starting point — not derived
from any labeled outcome data (there is none) and not copied from a
contract section that does not exist in this repo. If a real technical
contract surfaces later, these values should be reconciled against it
before Stage 5 is considered final.

Stage 5 does NOT re-score anything. It consumes the existing, frozen
Stage 4 outputs (RiskScore.priority_value/priority_level,
InterventionWindowRecord.estimated_window_minutes) and the existing frozen
Stage 3A rank — it never recomputes ml_score, heuristic_score, or
priority.value.
"""

# ============================================================
# TRIGGER POLICY (§7)
# ============================================================
# An alert is generated for a candidate account IFF its persisted Stage 4
# RiskScore.priority_level is one of these bands. Low/medium priority
# candidates never generate an alert — they are visible via the existing
# GET /complaints/{id}/risk endpoint, which is sufficient for them.
ALERT_TRIGGERING_PRIORITY_LEVELS = ["high", "critical"]

# ============================================================
# ALERT TYPES (§9) — each corresponds to an actual signal already present
# in the Stage 3A/3B/4 pipeline. No arbitrary categories.
# ============================================================
# Default type: priority_level alone crossed the trigger threshold.
ALERT_TYPE_MULE_CHAIN = "high_risk_mule_chain_detection"

# Upgraded type: this account is ALSO the top-ranked candidate (rank == 1,
# the only candidate for which Stage 4's intervention engine computes a
# window at all) AND that window's urgency band (per
# app.services.intervention_engine.urgency_band, itself driven by
# app.core.risk_config.INTERVENTION_URGENCY_BANDS) is one of the bands
# listed below.
ALERT_TYPE_INTERVENTION_URGENCY = "critical_intervention_urgency"
ALERT_INTERVENTION_URGENCY_TRIGGER_BANDS = ["critical", "high"]

# ============================================================
# ALERT PRIORITY (§8) — Stage 5's OWN score. Distinct from:
#   - Model A's ml_score (a ranking score from a trained classifier)
#   - Stage 4's priority.value (a heuristic combination of
#     ml_score + fraud_amount_tier + hours_since_complaint)
# NEITHER of the above is modified, replaced, or recomputed here.
# Stage 5's priority_score is a SEPARATE, transparent combination of the
# existing Stage 4 priority.value (primary input, per §8) with the
# existing intervention urgency signal (only available for rank==1
# candidates — see above), so that an account with both high operational
# risk AND a short remaining intervention window naturally sorts above an
# equally-risky account with no urgency signal at all.
#
# priority_score = ALERT_PRIORITY_WEIGHT_RISK * stage4_priority_value
#                 + ALERT_PRIORITY_WEIGHT_URGENCY * urgency_component
#
# urgency_component = 1 - min(estimated_window_minutes / INTERVENTION_MAX_MINUTES, 1)
#   (shorter remaining window -> value closer to 1; longer window -> closer to 0)
#   = 0.0 when no intervention window exists for this account (i.e. every
#     candidate except the top-ranked one), which is an honest "no urgency
#     evidence available" default, not a penalty.
#
# Weights must sum to 1.0 (enforced by a test). This is NOT a probability
# and must never be described as one.
ALERT_PRIORITY_WEIGHT_RISK = 0.70
ALERT_PRIORITY_WEIGHT_URGENCY = 0.30

# ============================================================
# ALERT LIFECYCLE (§10) — minimal, deterministic. No investigator notes,
# assignment, evidence, or closure workflow (deferred to a later stage).
# Stage 5 does not implement a status-mutation endpoint: every generated
# alert starts (and, on regeneration, restarts) at ALERT_STATUS_DEFAULT.
# ============================================================
ALERT_STATUS_OPEN = "open"
ALERT_STATUS_ACKNOWLEDGED = "acknowledged"
ALERT_STATUS_RESOLVED = "resolved"
ALERT_VALID_STATUSES = [ALERT_STATUS_OPEN, ALERT_STATUS_ACKNOWLEDGED, ALERT_STATUS_RESOLVED]
ALERT_STATUS_DEFAULT = ALERT_STATUS_OPEN

# ============================================================
# TITLE / EXPLANATION TEMPLATES (§14) — observational language only. Reuses
# Stage 4's own drivers/rationale rather than inventing a second
# explanation system. {value} placeholders are filled by alert_engine.py.
# ============================================================
ALERT_TITLE_TEMPLATE_MULE_CHAIN = "High-risk mule-chain candidate: account {account_id} ({severity} priority)"
ALERT_TITLE_TEMPLATE_INTERVENTION = "Critical intervention window: account {account_id} ({estimated_window_minutes} min estimated)"

ALERT_EXPLANATION_MAX_DRIVERS = 2  # how many Stage 4 drivers to fold into the alert explanation text
