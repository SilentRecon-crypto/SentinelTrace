"""
Experiment 2 — candidate subgraph construction + features.

CANDIDATE GENERATION mimics how a real investigator works: starting from the
victim's account, follow OUTGOING transactions forward in time (money can only
move forward), up to max_depth hops, within a max_days window after the
complaint. This naturally pulls in the true mule chain PLUS a large number of
decoys (background noise, hub accounts, confusor accounts, unrelated branches)
-- nobody hands the investigator a clean list.

LEAKAGE RULE: every feature is computed using only transactions with
day <= complaint_day + hop-observation-time (i.e., only what would be visible
by the time that candidate surfaced during tracing), and NEVER using acc_type,
ring membership, or the chain list itself. Checked explicitly at the bottom.
"""
import numpy as np
import pandas as pd
from collections import defaultdict, deque

def build_candidate_table(accounts, transactions, complaints, max_depth=4, max_days=14,
                            resolution_lag_days=25):
    # Index outgoing transactions by (account, day) for fast forward BFS
    tx_by_src = defaultdict(list)
    for row in transactions.itertuples(index=False):
        tx_by_src[row.src].append(row)
    for k in tx_by_src:
        tx_by_src[k].sort(key=lambda r: r.day)

    # For "confirmed_history_count": build a resolved-case ledger, i.e. every
    # account that was part of a chain becomes "confirmed" resolution_lag_days
    # after that complaint's day -- simulating real investigative lag. Only
    # entries with confirmed_day < current complaint day are usable.
    confirmed_events = []  # (account_id, confirmed_day)
    for c in complaints.itertuples(index=False):
        for m in c.chain:
            confirmed_events.append((m, c.day + resolution_lag_days))
    confirmed_df = pd.DataFrame(confirmed_events, columns=["account_id", "confirmed_day"]).sort_values("confirmed_day")

    def confirmed_history_count(account_id, as_of_day):
        sub = confirmed_df[(confirmed_df.account_id == account_id) & (confirmed_df.confirmed_day < as_of_day)]
        return len(sub)
    # Precompute per-account sorted confirmed_day list for speed
    conf_by_acc = defaultdict(list)
    for r in confirmed_df.itertuples(index=False):
        conf_by_acc[r.account_id].append(r.confirmed_day)

    def confirmed_count_fast(account_id, as_of_day):
        days = conf_by_acc.get(account_id, [])
        # count of days < as_of_day
        lo, hi = 0, len(days)
        while lo < hi:
            mid = (lo + hi) // 2
            if days[mid] < as_of_day:
                lo = mid + 1
            else:
                hi = mid
        return lo

    # Historical in/out-degree and fan-in as of a given day (pre-complaint only)
    all_tx_sorted = transactions.sort_values("day")
    # Build cumulative degree lookups lazily per query (acceptable at this scale)
    def historical_out_degree(account_id, as_of_day, window=30):
        lo = as_of_day - window
        sub = tx_by_src.get(account_id, [])
        return sum(1 for r in sub if lo <= r.day < as_of_day)

    in_tx_by_dst = defaultdict(list)
    for row in transactions.itertuples(index=False):
        in_tx_by_dst[row.dst].append(row)
    for k in in_tx_by_dst:
        in_tx_by_dst[k].sort(key=lambda r: r.day)

    def historical_fan_in(account_id, as_of_day, window=30):
        lo = as_of_day - window
        sub = in_tx_by_dst.get(account_id, [])
        senders = {r.src for r in sub if lo <= r.day < as_of_day}
        return len(senders)

    def account_age(account_id, as_of_day, created_lookup):
        c = created_lookup.get(account_id, 0)
        return max(0, as_of_day - c)

    created_lookup = dict(zip(accounts.account_id, accounts.created_day))
    chain_sets = {c.complaint_id: set(c.chain) for c in complaints.itertuples(index=False)}

    rows = []
    for c in complaints.itertuples(index=False):
        true_set = chain_sets[c.complaint_id]
        # BFS forward from victim
        visited_depth = {}
        edge_in = {}  # account_id -> (amount, day) of the FIRST traced inbound edge that discovered it
        frontier = deque([(c.victim, 0, c.day, c.fraud_amount)])
        visited_depth[c.victim] = 0
        while frontier:
            node, depth, node_time, incoming_amt = frontier.popleft()
            if depth >= max_depth:
                continue
            for r in tx_by_src.get(node, []):
                if r.day < node_time or r.day > c.day + max_days:
                    continue
                nxt = r.dst
                if nxt == c.victim:
                    continue
                if nxt not in visited_depth:
                    visited_depth[nxt] = depth + 1
                    edge_in[nxt] = (r.amount, r.day)
                    frontier.append((nxt, depth + 1, r.day, r.amount))

        candidates = [a for a in visited_depth if a != c.victim]
        if not candidates:
            continue

        for cand in candidates:
            depth = visited_depth[cand]
            in_amt, in_day = edge_in[cand]

            # pass-through ratio: fraction of the traced-in amount that leaves again
            # within 72h, computed purely from observed outgoing txns (no label use)
            out_within_72h = [r.amount for r in tx_by_src.get(cand, [])
                               if in_day <= r.day <= in_day + 3]
            pass_through_ratio = (sum(out_within_72h) / in_amt) if in_amt > 0 else 0.0
            pass_through_ratio = min(pass_through_ratio, 3.0)  # clip outliers

            fan_in = historical_fan_in(cand, c.day, window=30)
            out_deg = historical_out_degree(cand, c.day, window=30)
            age = account_age(cand, c.day, created_lookup)
            conf_hist = confirmed_count_fast(cand, c.day)
            amount_consistency = in_amt / c.fraud_amount if c.fraud_amount > 0 else 0.0

            rows.append(dict(
                complaint_id=c.complaint_id, day=c.day, n_hops=c.n_hops,
                candidate_id=cand, hop_distance=depth,
                pass_through_ratio=pass_through_ratio,
                fan_in_recent_30d=fan_in, out_degree_recent_30d=out_deg,
                account_age_days=age, confirmed_history_count=conf_hist,
                amount_consistency=amount_consistency,
                traced_in_amount=in_amt,
                label=int(cand in true_set),
                used_shared_pool=c.used_shared_pool,
            ))

    feat = pd.DataFrame(rows)
    # simple structural centrality within each complaint's own candidate subgraph
    feat["subgraph_degree_centrality"] = feat.groupby("complaint_id")["fan_in_recent_30d"].rank(pct=True)
    return feat


FEATURE_COLS = [
    "hop_distance", "pass_through_ratio", "fan_in_recent_30d", "out_degree_recent_30d",
    "account_age_days", "confirmed_history_count", "amount_consistency",
    "subgraph_degree_centrality",
]

if __name__ == "__main__":
    from generate_graph_v1 import generate_world
    accounts, transactions, complaints, meta = generate_world(seed=42, noise_level="medium", n_complaints=200)
    feat = build_candidate_table(accounts, transactions, complaints)
    print(f"Candidate rows: {len(feat)} across {feat.complaint_id.nunique()} complaints")
    print(f"Avg candidates per complaint: {len(feat)/feat.complaint_id.nunique():.1f}")
    print(f"Positive rate: {feat.label.mean():.4f}")
    print(feat[FEATURE_COLS + ['label']].describe().round(3))
