import numpy as np
import pandas as pd
from generate_graph_v1 import generate_world
from experiment2_features import build_candidate_table, FEATURE_COLS
from experiment2_eval import run_all_methods, rank_metrics_multilabel

DEFAULT_KW = dict(obscure_amounts=True, split_prob=0.35, missing_hop_prob=0.15,
                   adversarial_decoys=True, n_complaints=600)

accounts, transactions, complaints, meta = generate_world(seed=42, noise_level="medium", **DEFAULT_KW)
feat = build_candidate_table(accounts, transactions, complaints)
split_day = int(complaints.day.quantile(0.70))
out, model, train, test = run_all_methods(feat, split_day)
test_scored = test.copy()
test_scored["score"] = model.predict_proba(test_scored[FEATURE_COLS])[:, 1]

# ======================================================================
# 3. HOP STRATIFICATION + path disambiguation
# ======================================================================
print("="*70); print("3. HOP STRATIFICATION"); print("="*70)
hop_rows = []
for h in [1, 2, 3]:
    cids = complaints[complaints.n_hops == h].complaint_id
    sub = test_scored[test_scored.complaint_id.isin(cids)]
    if sub.complaint_id.nunique() == 0:
        continue
    m = rank_metrics_multilabel(sub, "score")
    hop_rows.append([h, m["n_complaints"], m["P_at_1"], m["Recall_at_5"], m["MRR"], m["Path_recovery_rate"]])
hop_df = pd.DataFrame(hop_rows, columns=["n_hops", "n_complaints", "P@1", "Recall@5", "MRR", "PathRecovery"]).round(4)
print(hop_df.to_string(index=False))
hop_df.to_csv("FINAL_hop_stratification.csv", index=False)
print()

# Path disambiguation: at split-transaction complaints, is the TRUE hop-1
# candidate ranked above the DECOY split-branch candidate at the same hop?
print("--- Path disambiguation at split-transaction hops (hop_distance==1) ---")
h1 = test_scored[test_scored.hop_distance == 1]
disambig_hits, disambig_total = 0, 0
for cid, g in h1.groupby("complaint_id"):
    if g.label.sum() == 0 or g.label.sum() == len(g):
        continue  # need both a true and a decoy candidate at hop 1 to test disambiguation
    disambig_total += 1
    true_score = g[g.label == 1].score.max()
    decoy_score_max = g[g.label == 0].score.max()
    if true_score > decoy_score_max:
        disambig_hits += 1
print(f"Complaints with competing hop-1 paths (true + decoy present): {disambig_total}")
if disambig_total > 0:
    print(f"ML correctly ranks true path above decoy: {disambig_hits}/{disambig_total} = {disambig_hits/disambig_total:.3f}")
print()

# ======================================================================
# 4. NOVEL-MULE TEST (rigorous: based on actual chain membership history,
#    not the confirmed_history_count feature -- independent verification)
# ======================================================================
print("="*70); print("4. NOVEL-MULE TEST (rigorous, feature-independent verification)"); print("="*70)
train_complaints = complaints[complaints.day < split_day]
test_complaints = complaints[complaints.day >= split_day]
accounts_used_in_training = set()
for chain in train_complaints.chain:
    accounts_used_in_training.update(chain)

def is_fully_novel(chain):
    return len(set(chain) & accounts_used_in_training) == 0

test_complaints = test_complaints.copy()
test_complaints["fully_novel"] = test_complaints.chain.apply(is_fully_novel)
novel_ids = test_complaints[test_complaints.fully_novel].complaint_id
reused_ids = test_complaints[~test_complaints.fully_novel].complaint_id
print(f"Test complaints: {len(test_complaints)}")
print(f"  -> fully novel mule chain (zero overlap with training chains): {len(novel_ids)}")
print(f"  -> chain reuses at least one account seen in training:          {len(reused_ids)}")
print()
for label, ids in [("Fully novel mule accounts", novel_ids), ("Reused mule accounts", reused_ids)]:
    sub = test_scored[test_scored.complaint_id.isin(ids)]
    if sub.complaint_id.nunique() == 0:
        print(f"{label}: no complaints"); continue
    m = rank_metrics_multilabel(sub, "score")
    print(f"{label}: n={m['n_complaints']}  P@1={m['P_at_1']:.3f}  P@5={m['P_at_5']:.3f}  "
          f"Recall@5={m['Recall_at_5']:.3f}  MRR={m['MRR']:.3f}")
    # sanity check: confirm confirmed_history_count IS actually zero for novel-chain candidates
    sub_true = sub[sub.label == 1]
    if len(sub_true) > 0:
        print(f"    sanity check -- confirmed_history_count for true mules in this group: "
              f"mean={sub_true.confirmed_history_count.mean():.3f}, max={sub_true.confirmed_history_count.max()}")
print()

# ======================================================================
# 6. MULTIPLE SIMULTANEOUS FRAUD NETWORKS (shared-pool complaints)
# ======================================================================
print("="*70); print("6. SIMULTANEOUS/OVERLAPPING FRAUD NETWORKS (shared mule pool)"); print("="*70)
shared_ids = complaints[complaints.used_shared_pool].complaint_id
nonshared_ids = complaints[~complaints.used_shared_pool].complaint_id
for label, ids in [("Shared/overlapping mule pool", shared_ids), ("Independent (non-shared) mules", nonshared_ids)]:
    sub = test_scored[test_scored.complaint_id.isin(ids)]
    if sub.complaint_id.nunique() == 0:
        print(f"{label}: no test complaints"); continue
    m = rank_metrics_multilabel(sub, "score")
    print(f"{label}: n={m['n_complaints']}  P@1={m['P_at_1']:.3f}  Recall@5={m['Recall_at_5']:.3f}  MRR={m['MRR']:.3f}")
print()
