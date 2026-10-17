"""
Production candidate generation for Model A inference.

CRITICAL DESIGN: this module does NOT reimplement BFS, feature engineering,
or candidate discovery. It loads real data from PostgreSQL into the same
pandas shapes the authoritative research function expects, then calls
research_model_a.experiment2_features.build_candidate_table() UNCHANGED.
This is the only way candidate generation happens in production.

GROUND-TRUTH ISOLATION (see module docstring in experiment2_features.py and
Stage 3A task section 18): build_candidate_table() takes a `complaints`
DataFrame and reads `c.chain` in three places — to compute the leakage-free
`label` column (evaluation-only), to build cross-complaint "confirmed_history"
events, and nowhere else (never for candidate discovery/BFS itself, which is
driven purely by victim/day/fraud_amount and the transaction graph).

To use this authoritative function honestly in production, we build a
SINGLE-ROW complaints DataFrame containing the real complaint we're scoring,
with chain=[] (empty). This has two deliberate, honest consequences:

  1. `label` is always 0 for every candidate (correct — production does not
     know the ground truth, and this column is stripped before it ever
     reaches the API response or persistence layer; see mule_chain_prediction.py).
  2. `confirmed_history_count` is always 0 for every candidate, because the
     function's "resolved-case ledger" is built ONLY from the chains of the
     complaints DataFrame passed in (see experiment2_features.py lines 33-36),
     and we pass exactly one complaint with chain=[]. This is not a hack —
     it is the honest answer: PostgreSQL currently has no independently
     verified resolved-case ledger (a real table of accounts previously
     confirmed as mules by human investigators) separate from this synthetic
     dataset's ground truth. See KNOWN LIMITATION in mule_chain_prediction.py.

No other behavior differs from the research implementation: BFS depth bound,
time window, transaction direction, pass-through/fan-in/out-degree/account-age/
amount-consistency/subgraph-centrality calculations are 100% the research code,
unmodified, run against real database rows.
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

RESEARCH_DIR = Path(__file__).resolve().parent.parent.parent / "research_model_a"
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from experiment2_features import build_candidate_table, FEATURE_COLS  # noqa: E402

from app.models.account import Account
from app.models.complaint import Complaint
from app.models.transaction import Transaction

# Must match research_model_a/experiment2_features.py::build_candidate_table's
# own defaults exactly — not re-tuned for production.
MAX_DEPTH = 4
MAX_DAYS = 14
RESOLUTION_LAG_DAYS = 25
HISTORICAL_WINDOW_DAYS = 30  # matches historical_fan_in/historical_out_degree's `window=30` default


class NoCandidatesError(RuntimeError):
    """Raised when BFS from the victim account discovers zero reachable accounts."""


def _load_accounts_df(db: Session) -> pd.DataFrame:
    rows = db.execute(select(Account.account_id, Account.acc_type, Account.created_day)).all()
    return pd.DataFrame(rows, columns=["account_id", "acc_type", "created_day"])


def _load_transactions_df(db: Session, complaint_day: int) -> pd.DataFrame:
    """Load only the transactions that could possibly matter for this
    complaint's BFS/feature window, per the same bounds build_candidate_table
    itself enforces (day <= complaint_day + MAX_DAYS for forward tracing;
    day >= complaint_day - HISTORICAL_WINDOW_DAYS for the 30-day trailing
    fan-in/out-degree windows, both evaluated relative to complaint_day).
    This is a query-time optimization only — it does not change which rows
    build_candidate_table would have used, since anything outside this range
    is provably unusable by the unmodified research logic.
    """
    lo = complaint_day - HISTORICAL_WINDOW_DAYS
    hi = complaint_day + MAX_DAYS
    rows = db.execute(
        select(Transaction.src_account_id, Transaction.dst_account_id, Transaction.day, Transaction.hour, Transaction.amount)
        .where(Transaction.day >= lo, Transaction.day <= hi)
    ).all()
    return pd.DataFrame(rows, columns=["src", "dst", "day", "hour", "amount"])


def build_candidates_for_complaint(db: Session, complaint: Complaint) -> pd.DataFrame:
    """Returns the candidate/feature table for ONE real complaint, built from
    real PostgreSQL data via the unmodified authoritative research function.
    The returned DataFrame includes a `label` column (always 0, per the
    ground-truth isolation design above) — callers must never expose or
    persist this column; it exists only because build_candidate_table()
    always produces it.
    """
    accounts_df = _load_accounts_df(db)
    transactions_df = _load_transactions_df(db, complaint.day)

    # Single-row complaints DataFrame for the authoritative function.
    # chain=[] is the deliberate ground-truth-isolation mechanism described
    # in this module's docstring — NOT a placeholder for missing data.
    complaint_row = pd.DataFrame([{
        "complaint_id": complaint.complaint_id,
        "victim": complaint.victim,
        "day": complaint.day,
        "fraud_amount": complaint.fraud_amount,
        "n_hops": complaint.n_hops,
        "chain": [],
        "used_shared_pool": False,
        "mode": complaint.mode,
        "missing_hop_idx": complaint.missing_hop_idx,
    }])

    feat = build_candidate_table(
        accounts_df, transactions_df, complaint_row,
        max_depth=MAX_DEPTH, max_days=MAX_DAYS, resolution_lag_days=RESOLUTION_LAG_DAYS,
    )

    if feat.empty:
        raise NoCandidatesError(
            f"BFS from victim account {complaint.victim} (complaint {complaint.complaint_id}) "
            f"discovered zero reachable accounts within {MAX_DEPTH} hops / {MAX_DAYS} days."
        )

    missing_cols = [c for c in FEATURE_COLS if c not in feat.columns]
    if missing_cols:
        raise RuntimeError(f"build_candidate_table() output is missing expected feature columns: {missing_cols}")

    return feat
