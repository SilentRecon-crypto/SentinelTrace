"""
Stage 4 risk engine + intervention window configuration.

Every weight, threshold, and bound used by app/services/risk_engine.py and
app/services/intervention_engine.py lives here — nothing is scattered inline
in those modules, per Stage 4 instructions.

CONTRACT ALIGNMENT: SentinelTrace_Technical_Contract.md §10 (Risk Engine
Contract) specifies exactly three named inputs to `priority.value`:
`ml_score`, `fraud_amount_tier`, `hours_since_complaint`. It does NOT specify
exact weights or thresholds — §10 explicitly says thresholds are "to be
tuned during demo rehearsal... and recorded in a config file, not
hard-coded inline." The values below are that config file: a documented,
smallest-deterministic-choice starting point, not a value derived from any
labeled outcome data (there is none — see §10's `priority.method` rule).

None of this touches Model A. `ml_score` is read verbatim from the existing
persisted Model A prediction; nothing here retrains, recalibrates, or
reinterprets it as anything other than the ranking score it already is.
"""

# ============================================================
# PRIORITY FORMULA (Contract §10: ml_score + fraud_amount_tier + hours_since_complaint)
# ============================================================
# priority.value = PRIORITY_WEIGHT_ML * ml_score
#                 + PRIORITY_WEIGHT_AMOUNT * fraud_amount_tier_normalized
#                 + PRIORITY_WEIGHT_URGENCY * hours_since_complaint_normalized
# Weights must sum to 1.0 (enforced by a test).
PRIORITY_WEIGHT_ML = 0.60          # Model A's own ranking score dominates — it is the
                                    # only component backed by an actual trained/validated model.
PRIORITY_WEIGHT_AMOUNT = 0.25      # Larger reported fraud amounts merit higher operational priority.
PRIORITY_WEIGHT_URGENCY = 0.15     # Complaints sitting longer without action get a small priority boost
                                    # (staleness risk), capped so it can never dominate the ML signal.

# fraud_amount_tier: complaint.fraud_amount is bucketed into 4 tiers, each
# mapped to a fixed normalized value in [0, 1]. Breakpoints are in the
# dataset's native currency unit (same unit as `complaints.fraud_amount`,
# i.e. INR in the synthetic generator). Chosen as round, defensible numbers
# spanning the canonical dataset's observed range, not fitted to any outcome.
FRAUD_AMOUNT_TIER_BREAKPOINTS = [10_000, 50_000, 200_000]  # <=10k, <=50k, <=200k, >200k
FRAUD_AMOUNT_TIER_VALUES = [0.25, 0.50, 0.75, 1.00]

# hours_since_complaint: normalized as min(hours / SATURATION_HOURS, 1.0).
# A complaint that has sat for >= 72 hours (3 days) without resolution is
# treated as maximally "stale" for prioritization purposes; this is a
# documented assumption, not derived from real case-aging data (none exists).
URGENCY_SATURATION_HOURS = 72.0

# Since the synthetic dataset's `day` integers have no real calendar
# anchor, we fix one arbitrary but consistent epoch so day N maps to a real
# datetime (EPOCH + N days). This affects only the *display* of timestamps
# and the *relative* hours_since_complaint computation — never which
# candidates are considered or how they're scored.
SYNTHETIC_DAY_ZERO_EPOCH = "2026-01-01T00:00:00+00:00"

# priority.level bands over priority.value in [0, 1]. Boundaries are
# inclusive on the lower bound. Must be non-overlapping and cover [0, 1].
RISK_BANDS = [
    (0.00, 0.40, "low"),
    (0.40, 0.65, "medium"),
    (0.65, 0.85, "high"),
    (0.85, 1.01, "critical"),  # upper bound 1.01 so priority.value == 1.0 lands in "critical"
]

# ============================================================
# HEURISTIC SCORE ("graph flow-decay formula" per Contract §5's risk_scores
# table description). This is DELIBERATELY separate from and NOT an input
# to priority.value (Contract §10's example lists only ml_score,
# fraud_amount_tier, hours_since_complaint as priority.formula_inputs) — it
# is reported alongside ml_score as an independent, ML-free, pure
# graph-topology view for an analyst to sanity-check the ML score against.
# ============================================================
# heuristic_score = clip(
#     HEUR_WEIGHT_HOP     * exp(-HEUR_HOP_DECAY_RATE * hop_distance)
#   + HEUR_WEIGHT_PASSTHROUGH * pass_through_ratio
#   + HEUR_WEIGHT_FANIN   * min(fan_in_recent_30d / HEUR_FANIN_CAP, 1.0)
#   + HEUR_WEIGHT_CENTRALITY * subgraph_degree_centrality
# , 0, 1)
# Weights must sum to 1.0 (enforced by a test).
HEUR_WEIGHT_HOP = 0.35
HEUR_WEIGHT_PASSTHROUGH = 0.30
HEUR_WEIGHT_FANIN = 0.15
HEUR_WEIGHT_CENTRALITY = 0.20
HEUR_HOP_DECAY_RATE = 0.5   # at hop_distance=1 -> exp(-0.5)=0.61; at hop=4 -> exp(-2)=0.14
HEUR_FANIN_CAP = 10.0       # fan-in counts are capped/normalized at 10 distinct senders

# ============================================================
# DRIVERS (Contract §10: "generated from §8's explanation.top_drivers" —
# top-3 features by permutation importance, combined with this candidate's
# actual feature value, rendered via a fixed plain-language template.)
# ============================================================
DRIVER_TOP_N = 3

# One template per Model A feature, matching the phrasing style of the
# three worked examples in Contract §10 exactly ("Rapid pass-through: funds
# forwarded within 4 hours", "High fan-in: 9 distinct senders in 30 days",
# "2 hops from victim account"). {value} is substituted with the
# candidate's actual feature value.
DRIVER_TEMPLATES = {
    "hop_distance": "{value_int} hop(s) from the victim account",
    "pass_through_ratio": "Rapid pass-through: {value_pct} of traced funds forwarded onward within 72h",
    "fan_in_recent_30d": "High fan-in: {value_int} distinct senders in the last 30 days",
    "out_degree_recent_30d": "Elevated recent activity: {value_int} outgoing transfers in the last 30 days",
    "account_age_days": "Very new account: opened {value_int} day(s) before the complaint",
    "confirmed_history_count": "Prior confirmed history: appeared in {value_int} previously resolved case(s)",
    "amount_consistency": "Traced-in amount is {value_pct} of the reported fraud amount",
    "subgraph_degree_centrality": "High structural centrality ({value_pct} percentile) within this complaint's candidate network",
}

# ============================================================
# INTERVENTION WINDOW (Contract §11, method="synthetic_historical_hop_timing")
# ============================================================
# For the top-ranked candidate, estimated_window_minutes is derived from
# that SPECIFIC account's own historical in->out transaction timing where
# available (real persisted transactions, day < complaint.day only — no
# future leakage), falling back to a dataset-wide median when the account
# has no prior track record. Result is clipped to a sane range so a
# pathological single data point can't produce an absurd estimate.
INTERVENTION_METHOD = "synthetic_historical_hop_timing"
INTERVENTION_VALIDATION_STATUS = "synthetic_demo_only"  # Contract §11: fixed literal, never changes
INTERVENTION_MIN_MINUTES = 5
INTERVENTION_MAX_MINUTES = 1440  # 24 hours

# Intervention urgency bands, over estimated_window_minutes (shorter window
# = more urgent). Computed at API-response time only — NOT persisted, since
# the Contract §5 intervention_windows schema has no urgency column.
INTERVENTION_URGENCY_BANDS = [
    (0, 30, "critical"),
    (30, 120, "high"),
    (120, 360, "medium"),
    (360, float("inf"), "low"),
]
