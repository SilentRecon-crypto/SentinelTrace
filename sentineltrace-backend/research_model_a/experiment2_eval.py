"""
Experiment 2 — baselines, ML/graph-ML approach, and evaluation metrics.

Unlike Experiment 1 (exactly one true location per query), here a complaint can
have 1-3 true positives among its candidates. Metrics are adapted accordingly:
  - P@1: is the #1 ranked candidate a true chain member?
  - P@5: (# true positives in top-5) / 5   [standard multi-label precision]
  - Recall@5: (# true positives in top-5) / (total true chain length)
  - MRR: 1 / rank of the FIRST true chain member found
  - Path recovery rate: fraction of complaints where ALL true chain members
    appear somewhere in the top-10 (operationally: "did we map the whole chain")
  - False positive rate: among candidates flagged (top-5 rule), fraction that
    are NOT true chain members
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from experiment2_features import FEATURE_COLS

def rank_metrics_multilabel(df, score_col, k5=5, k_path=10):
    p1, p5, r5, mrr, path_ok = [], [], [], [], []
    fp_top5, tp_top5 = 0, 0
    for cid, g in df.groupby("complaint_id"):
        g = g.sort_values(score_col, ascending=False).reset_index(drop=True)
        n_true = g.label.sum()
        if n_true == 0:
            continue
        top1 = g.iloc[0]
        p1.append(float(top1.label == 1))

        top5 = g.head(k5)
        tp = top5.label.sum()
        p5.append(tp / k5)
        r5.append(tp / n_true)
        tp_top5 += tp
        fp_top5 += (k5 - tp)

        true_ranks = g.index[g.label == 1].values + 1
        mrr.append(1.0 / true_ranks.min())

        topk_path = g.head(k_path)
        path_ok.append(float(topk_path.label.sum() == n_true))

    fpr = fp_top5 / (fp_top5 + (5 * len(p1) - fp_top5)) if p1 else float("nan")
    # simpler, standard FPR = FP / (FP + TN); TN = candidates outside top5 that are
    # correctly not-flagged AND negative -- compute at row level for precision:
    return dict(
        P_at_1=np.mean(p1), P_at_5=np.mean(p5), Recall_at_5=np.mean(r5),
        MRR=np.mean(mrr), Path_recovery_rate=np.mean(path_ok),
        n_complaints=len(p1),
    )


def row_level_fpr(df, score_col, k5=5):
    df = df.copy()
    df["pred_pos"] = 0
    for cid, g in df.groupby("complaint_id"):
        idx = g.sort_values(score_col, ascending=False).index[:k5]
        df.loc[idx, "pred_pos"] = 1
    fp = ((df.pred_pos == 1) & (df.label == 0)).sum()
    tn = ((df.pred_pos == 0) & (df.label == 0)).sum()
    return fp / (fp + tn) if (fp + tn) > 0 else float("nan")


def run_all_methods(feat, split_day, seed=0):
    train = feat[feat.day < split_day].copy()
    test = feat[feat.day >= split_day].copy()
    rng = np.random.default_rng(seed)
    out = {}

    # 1. Random
    t = test.copy(); t["score"] = rng.random(len(t))
    out["Random"] = {**rank_metrics_multilabel(t, "score"), "FPR": row_level_fpr(t, "score")}

    # 2. Simple transaction heuristic: nearest hop first
    t = test.copy(); t["score"] = -t["hop_distance"]
    out["Nearest-hop heuristic"] = {**rank_metrics_multilabel(t, "score"), "FPR": row_level_fpr(t, "score")}

    # 3. Rule-based suspicious-account scoring (fixed weights, NOT fit to data)
    t = test.copy()
    t["score"] = (
        1.6 * t["pass_through_ratio"]
        + 1.2 * (1.0 / (1.0 + t["account_age_days"] / 30.0))
        + 0.8 * t["amount_consistency"].clip(0, 2)
        - 0.5 * np.log1p(t["fan_in_recent_30d"])
    )
    out["Rule-based scoring"] = {**rank_metrics_multilabel(t, "score"), "FPR": row_level_fpr(t, "score")}

    # 4. Graph-based (non-ML): amount-flow decay propagation
    t = test.copy()
    t["score"] = t["amount_consistency"].clip(0, 2) * (0.6 ** (t["hop_distance"] - 1)) * (1 + t["pass_through_ratio"])
    out["Graph flow-decay (non-ML)"] = {**rank_metrics_multilabel(t, "score"), "FPR": row_level_fpr(t, "score")}

    # 5. ML / graph-ML (gradient boosting on engineered graph features)
    model = HistGradientBoostingClassifier(max_depth=6, random_state=seed)
    model.fit(train[FEATURE_COLS], train["label"])
    t = test.copy()
    t["score"] = model.predict_proba(t[FEATURE_COLS])[:, 1]
    out["ML (graph features)"] = {**rank_metrics_multilabel(t, "score"), "FPR": row_level_fpr(t, "score")}
    try:
        out["ML (graph features)"]["ROC_AUC"] = roc_auc_score(t["label"], t["score"])
    except ValueError:
        out["ML (graph features)"]["ROC_AUC"] = float("nan")

    return out, model, train, test
