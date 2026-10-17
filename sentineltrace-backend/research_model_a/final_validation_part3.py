import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from generate_graph_v1 import generate_world
from experiment2_features import build_candidate_table, FEATURE_COLS
from experiment2_eval import run_all_methods, rank_metrics_multilabel

# ======================================================================
# 7. DISTRIBUTION-SHIFT TEST
# ======================================================================
print("="*70); print("7. DISTRIBUTION-SHIFT TEST (train env A, freeze, eval on env B)"); print("="*70)

# Environment A: the "hardened default" world used throughout this report
envA_kw = dict(obscure_amounts=True, split_prob=0.35, missing_hop_prob=0.15,
               adversarial_decoys=True, n_complaints=500, noise_level="medium",
               reuse_prob=0.35)
accounts_A, tx_A, complaints_A, _ = generate_world(seed=42, **envA_kw)
feat_A = build_candidate_table(accounts_A, tx_A, complaints_A)
split_day_A = int(complaints_A.day.quantile(0.70))
train_A = feat_A[feat_A.day < split_day_A]
model = HistGradientBoostingClassifier(max_depth=6, random_state=0)
model.fit(train_A[FEATURE_COLS], train_A["label"])

# Environment B: deliberately different on many axes at once --
# higher reuse, longer/shorter chains skew, different noise regime,
# different amount distribution (via very_high noise + different split/missing
# probabilities + different mule pool composition via a different seed AND
# structurally different generation call)
envB_kw = dict(obscure_amounts=True, split_prob=0.55, missing_hop_prob=0.30,
               adversarial_decoys=True, n_complaints=500, noise_level="high",
               reuse_prob=0.65, shared_pool_size=200)
accounts_B, tx_B, complaints_B, _ = generate_world(seed=9001, **envB_kw)
feat_B = build_candidate_table(accounts_B, tx_B, complaints_B)
# Evaluate the FROZEN model (trained only on env A) across ALL of env B
# (env B is entirely "the future/unknown" from the model's perspective)
feat_B_scored = feat_B.copy()
feat_B_scored["score"] = model.predict_proba(feat_B_scored[FEATURE_COLS])[:, 1]
m_shift = rank_metrics_multilabel(feat_B_scored, "score")

# For comparison: a model trained AND tested natively on env B (upper bound)
split_day_B = int(complaints_B.day.quantile(0.70))
out_B_native, model_B, train_B, test_B = run_all_methods(feat_B, split_day_B)

print(f"Env A (train) -> avg candidates/complaint: {len(feat_A)/feat_A.complaint_id.nunique():.1f}, "
      f"reuse_prob={envA_kw['reuse_prob']}, noise={envA_kw['noise_level']}")
print(f"Env B (shift) -> avg candidates/complaint: {len(feat_B)/feat_B.complaint_id.nunique():.1f}, "
      f"reuse_prob={envB_kw['reuse_prob']}, noise={envB_kw['noise_level']}")
print()
print(f"Model trained on A, frozen, evaluated on ALL of B:")
print(f"  P@1={m_shift['P_at_1']:.3f}  P@5={m_shift['P_at_5']:.3f}  Recall@5={m_shift['Recall_at_5']:.3f}  MRR={m_shift['MRR']:.3f}")
print()
print(f"Reference: model trained natively on B, tested on B's own held-out period:")
mb = out_B_native["ML (graph features)"]
print(f"  P@1={mb['P_at_1']:.3f}  P@5={mb['P_at_5']:.3f}  Recall@5={mb['Recall_at_5']:.3f}  MRR={mb['MRR']:.3f}")
print()
print(f"Performance drop from distribution shift (P@1): "
      f"{mb['P_at_1']:.3f} (native) -> {m_shift['P_at_1']:.3f} (shifted, frozen) "
      f"= {(mb['P_at_1']-m_shift['P_at_1'])/mb['P_at_1']*100:.1f}% relative drop")

pd.DataFrame([{
    "env": "A_native_holdout", **{k: out_B_native["ML (graph features)"][k] for k in ["P_at_1","P_at_5","Recall_at_5","MRR"]}
}]).to_csv("FINAL_distshift_reference.csv", index=False)
pd.DataFrame([m_shift]).to_csv("FINAL_distshift_result.csv", index=False)
print()

# ======================================================================
# 8. ABLATION STUDY
# ======================================================================
print("="*70); print("8. ABLATION STUDY (feature groups removed one at a time)"); print("="*70)
FEATURE_GROUPS = {
    "A: Transaction amount":       ["amount_consistency"],
    "B: Temporal":                 ["pass_through_ratio", "account_age_days"],
    "C: Graph structure":          ["hop_distance", "subgraph_degree_centrality"],
    "D: Account behavioural":      ["fan_in_recent_30d", "out_degree_recent_30d"],
    "E: Geographic":               [],  # not applicable -- Experiment 2 has no location features by design
    "F: Historical/reputation":    ["confirmed_history_count"],
}

accounts, transactions, complaints, meta = generate_world(seed=42, **envA_kw)
feat = build_candidate_table(accounts, transactions, complaints)
split_day = int(complaints.day.quantile(0.70))
train = feat[feat.day < split_day]
test = feat[feat.day >= split_day]

full_model = HistGradientBoostingClassifier(max_depth=6, random_state=0)
full_model.fit(train[FEATURE_COLS], train["label"])
test_full = test.copy()
test_full["score"] = full_model.predict_proba(test_full[FEATURE_COLS])[:, 1]
full_m = rank_metrics_multilabel(test_full, "score")
print(f"FULL MODEL (all features): P@1={full_m['P_at_1']:.3f}  P@5={full_m['P_at_5']:.3f}")
print()

ablation_rows = [["(none removed -- full model)", full_m["P_at_1"], full_m["P_at_5"], 0.0]]
for group_name, cols_to_remove in FEATURE_GROUPS.items():
    if not cols_to_remove:
        print(f"{group_name}: N/A (no such features exist in this experiment)")
        ablation_rows.append([group_name, float("nan"), float("nan"), float("nan")])
        continue
    remaining = [c for c in FEATURE_COLS if c not in cols_to_remove]
    m2 = HistGradientBoostingClassifier(max_depth=6, random_state=0)
    m2.fit(train[remaining], train["label"])
    t2 = test.copy()
    t2["score"] = m2.predict_proba(t2[remaining])[:, 1]
    m2_metrics = rank_metrics_multilabel(t2, "score")
    drop = full_m["P_at_1"] - m2_metrics["P_at_1"]
    ablation_rows.append([group_name, m2_metrics["P_at_1"], m2_metrics["P_at_5"], drop])
    print(f"{group_name} removed (cols: {cols_to_remove}): "
          f"P@1={m2_metrics['P_at_1']:.3f}  P@5={m2_metrics['P_at_5']:.3f}  "
          f"drop in P@1 = {drop:+.3f}")

ablation_df = pd.DataFrame(ablation_rows, columns=["Feature group removed", "P@1", "P@5", "P@1 drop"]).round(4)
ablation_df.to_csv("FINAL_ablation.csv", index=False)
print()
print(ablation_df.to_string(index=False))
