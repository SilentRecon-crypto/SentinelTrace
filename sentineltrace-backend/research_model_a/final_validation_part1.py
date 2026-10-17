import numpy as np
import pandas as pd
from generate_graph_v1 import generate_world
from experiment2_features import build_candidate_table, FEATURE_COLS
from experiment2_eval import run_all_methods, rank_metrics_multilabel, row_level_fpr
from sklearn.ensemble import HistGradientBoostingClassifier

METHOD_NAMES = ["Random", "Nearest-hop heuristic", "Rule-based scoring",
                "Graph flow-decay (non-ML)", "ML (graph features)"]

# Realistic "hardened" default config used throughout unless stated otherwise
DEFAULT_KW = dict(obscure_amounts=True, split_prob=0.35, missing_hop_prob=0.15,
                   adversarial_decoys=True, n_complaints=500)

# ======================================================================
# 1. MULTI-SEED VALIDATION (8 seeds)
# ======================================================================
print("="*70); print("1. MULTI-SEED VALIDATION (8 seeds, hardened default config)"); print("="*70)
SEEDS = [42, 123, 456, 789, 2026, 31415, 99991, 777]
METRIC_KEYS = ["P_at_1", "P_at_5", "Recall_at_5", "MRR", "Path_recovery_rate", "FPR"]
agg = {name: {k: [] for k in METRIC_KEYS} for name in METHOD_NAMES}
for seed in SEEDS:
    accounts, transactions, complaints, meta = generate_world(seed=seed, noise_level="medium", **DEFAULT_KW)
    feat = build_candidate_table(accounts, transactions, complaints)
    split_day = int(complaints.day.quantile(0.70))
    out, model, train, test = run_all_methods(feat, split_day, seed=seed)
    for name in METHOD_NAMES:
        for k in METRIC_KEYS:
            agg[name][k].append(out[name][k])
    print(f"seed {seed} done")

rows = []
for name in METHOD_NAMES:
    for k in METRIC_KEYS:
        vals = np.array(agg[name][k])
        rows.append([name, k, vals.mean(), vals.std(), vals.min(), vals.max()])
summary = pd.DataFrame(rows, columns=["Model", "Metric", "Mean", "Std", "Min", "Max"]).round(4)
summary.to_csv("FINAL_multiseed_summary.csv", index=False)
print()
for metric in METRIC_KEYS:
    print(f"--- {metric} ---")
    print(summary[summary.Metric == metric].drop(columns="Metric").to_string(index=False))
    print()

# ======================================================================
# 2. NOISE SWEEP (low/medium/high/very_high)
# ======================================================================
print("="*70); print("2. NOISE SWEEP"); print("="*70)
noise_rows = []
for nl in ["low", "medium", "high", "very_high"]:
    accounts, transactions, complaints, meta = generate_world(seed=42, noise_level=nl, **DEFAULT_KW)
    feat = build_candidate_table(accounts, transactions, complaints)
    split_day = int(complaints.day.quantile(0.70))
    out, model, train, test = run_all_methods(feat, split_day)
    avg_cand = len(feat) / feat.complaint_id.nunique()
    for name in METHOD_NAMES:
        m = out[name]
        noise_rows.append([nl, round(avg_cand, 1), name, m["P_at_1"], m["P_at_5"], m["Recall_at_5"], m["FPR"]])
    print(f"{nl}: avg candidates/complaint = {avg_cand:.1f}")
noise_df = pd.DataFrame(noise_rows, columns=["Noise", "AvgCandidates", "Model", "P@1", "P@5", "Recall@5", "FPR"]).round(4)
noise_df.to_csv("FINAL_noise_sweep.csv", index=False)
print()
print(noise_df.pivot(index="Model", columns="Noise", values="P@1")[["low", "medium", "high", "very_high"]].round(3))
print()
