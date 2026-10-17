"""
train_model_a.py — Stage 1 clean training entry point for SentinelTrace Model A
(mule-chain identification; called "Experiment 2" in the recovered research
files, per the confirmed terminology: Experiment 2 = Model A).

This script is a thin orchestration layer only. It does NOT reimplement,
redesign, or retune any Model A logic. It imports and calls the authoritative,
already-validated research functions verbatim from research_model_a/:

  - generate_graph_v1.generate_world          (synthetic world generator)
  - experiment2_features.build_candidate_table / FEATURE_COLS
  - experiment2_eval.run_all_methods          (trains the classifier, computes metrics)

CANONICAL CONFIGURATION
------------------------
seed = 42
config = final_validation_part1.py's own DEFAULT_KW dict, combined with
         noise_level="medium" exactly as that script passes it:

    generate_world(seed=42, noise_level="medium",
                    obscure_amounts=True, split_prob=0.35,
                    missing_hop_prob=0.15, adversarial_decoys=True,
                    n_complaints=500)

This is the exact "hardened realistic" configuration that produced the
headline 8-seed validated results in SentinelTrace_Experiment2_FINAL_Report.md
(seed 42 is the first/reference seed in that script's own SEEDS list). No
parameter here was invented, tuned, or adjusted for this stage.

Note: final_validation_part2.py uses a slightly different n_complaints (600)
for its own hop-stratification analysis. That variant is NOT used here —
this script uses part1's original multi-seed-validation config, since that is
the one the headline validated numbers are attributed to.
"""
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = ROOT / "research_model_a"
DATA_DIR = ROOT / "data" / "model_a"
ARTIFACT_DIR = ROOT / "artifacts" / "model_a"

sys.path.insert(0, str(RESEARCH_DIR))

from generate_graph_v1 import generate_world  # noqa: E402
from experiment2_features import build_candidate_table, FEATURE_COLS  # noqa: E402
from experiment2_eval import run_all_methods  # noqa: E402

MODEL_VERSION = "model_a_v1"
CANONICAL_SEED = 42
CANONICAL_KW = dict(
    noise_level="medium",
    obscure_amounts=True,
    split_prob=0.35,
    missing_hop_prob=0.15,
    adversarial_decoys=True,
    n_complaints=500,
)
CANONICAL_CONFIG_SOURCE = (
    "final_validation_part1.py :: DEFAULT_KW dict + noise_level='medium' "
    "(reused verbatim, not re-tuned). Seed 42 is the first/reference seed in "
    "that script's own SEEDS list."
)

# HistGradientBoostingClassifier hyperparameters exactly as used in
# experiment2_eval.run_all_methods() — copied here only for reporting in
# metadata; the actual training call below uses run_all_methods() itself,
# not a re-declared model, so these values cannot drift from the source.
REFERENCE_HYPERPARAMETERS = {"max_depth": 6, "random_state": CANONICAL_SEED}


def generate_and_persist_world():
    """Step 1: generate the canonical Model A world and persist it to CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    accounts, transactions, complaints, meta = generate_world(seed=CANONICAL_SEED, **CANONICAL_KW)

    accounts.to_csv(DATA_DIR / "accounts.csv", index=False)
    transactions.to_csv(DATA_DIR / "transactions.csv", index=False)

    # complaints.chain is a Python list per row (as returned by generate_world).
    # Stringify for CSV round-tripping using the same convention already used
    # elsewhere in this project (generate_data_v2.py serializes its own `chain`
    # column identically: ",".join(map(str, chain))).
    complaints_out = complaints.copy()
    complaints_out["chain"] = complaints_out["chain"].apply(lambda c: ",".join(map(str, c)))
    complaints_out.to_csv(DATA_DIR / "complaints.csv", index=False)

    with open(DATA_DIR / "generation_meta.json", "w") as f:
        json.dump({"shared_pool_account_ids": sorted(int(x) for x in meta["shared_pool"])}, f, indent=2)

    return accounts, transactions, complaints


def load_persisted_world():
    """Step 2: reload the world from the persisted CSVs (round-trip proof —
    this is what a real downstream consumer would actually read, not the
    in-memory objects generate_world() happened to also return)."""
    accounts = pd.read_csv(DATA_DIR / "accounts.csv")
    transactions = pd.read_csv(DATA_DIR / "transactions.csv")
    complaints = pd.read_csv(DATA_DIR / "complaints.csv")
    complaints["chain"] = complaints["chain"].apply(lambda s: [int(x) for x in str(s).split(",")])
    return accounts, transactions, complaints


def build_and_persist_candidates(accounts, transactions, complaints):
    """Step 3: build the candidate/feature table from the RELOADED (persisted)
    world, using the authoritative feature-engineering implementation unchanged."""
    feat = build_candidate_table(accounts, transactions, complaints)
    feat.to_csv(DATA_DIR / "candidates.csv", index=False)
    return feat


def train_and_save(feat):
    """Step 4: train using the authoritative training/eval function unchanged,
    then persist only the fitted estimator (no training data, no intermediate
    objects) via joblib."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    complaints = pd.read_csv(DATA_DIR / "complaints.csv")
    split_day = int(complaints["day"].quantile(0.70))

    out, model, train, test = run_all_methods(feat, split_day, seed=CANONICAL_SEED)

    artifact_path = ARTIFACT_DIR / f"{MODEL_VERSION}.pkl"
    joblib.dump(model, artifact_path)

    return model, out, train, test, split_day, artifact_path


def write_metadata(feat, out, train, test, split_day, artifact_path):
    now = datetime.now(timezone.utc).isoformat()

    # ---- feature_metadata.json ----
    feature_metadata = {
        "model_version": MODEL_VERSION,
        "feature_names_ordered": FEATURE_COLS,
        "feature_count": len(FEATURE_COLS),
        "source_implementation": "research_model_a/experiment2_features.py :: FEATURE_COLS (verbatim, unmodified)",
        "normalization_or_scaling": (
            "None. HistGradientBoostingClassifier is fit directly on raw feature "
            "values; the source implementation does not fit or apply any "
            "scaler/encoder anywhere in the training path."
        ),
        "naming_discrepancy_notice": (
            "The authoritative CODE names two features 'fan_in_recent_30d' and "
            "'out_degree_recent_30d' (30-day window explicit in the name). "
            "SentinelTrace_Technical_Contract.md section 8 lists the equivalent "
            "features as 'fan_in_recent' and 'out_degree_recent' (no suffix). "
            "This metadata and the persisted model follow the ACTUAL CODE, per "
            "Stage 1 instructions not to silently rename anything. This "
            "discrepancy must be resolved explicitly (either amend the Contract "
            "or rename in code) before any API layer is built around this model."
        ),
    }
    with open(ARTIFACT_DIR / "feature_metadata.json", "w") as f:
        json.dump(feature_metadata, f, indent=2)

    # ---- training_metadata.json ----
    training_metadata = {
        "model_version": MODEL_VERSION,
        "model_class": "sklearn.ensemble.HistGradientBoostingClassifier",
        "hyperparameters": REFERENCE_HYPERPARAMETERS,
        "hyperparameters_source": "research_model_a/experiment2_eval.py :: run_all_methods() (verbatim call, not re-declared)",
        "library_versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "generator_seed": CANONICAL_SEED,
        "generator_function": "research_model_a/generate_graph_v1.py :: generate_world",
        "generator_config": CANONICAL_KW,
        "generator_config_source": CANONICAL_CONFIG_SOURCE,
        "feature_builder": "research_model_a/experiment2_features.py :: build_candidate_table",
        "candidate_generation_defaults": {"max_depth": 4, "max_days": 14, "resolution_lag_days": 25,
                                           "note": "build_candidate_table()'s own defaults, not overridden."},
        "train_test_split": {
            "method": "temporal (day-based)",
            "split_day": split_day,
            "split_quantile": 0.70,
            "note": "train = day < split_day, test = day >= split_day — same discipline used throughout experiment2_eval.py and every final_validation_part*.py script.",
        },
        "dataset_size": {
            "n_candidate_rows_total": int(len(feat)),
            "n_complaints_total": int(feat.complaint_id.nunique()),
            "n_train_rows": int(len(train)),
            "n_test_rows": int(len(test)),
            "positive_rate_total": float(feat.label.mean()),
            "positive_rate_train": float(train.label.mean()),
            "positive_rate_test": float(test.label.mean()),
        },
        "training_timestamp_utc": now,
        "artifact_filename": artifact_path.name,
        "artifact_contents_note": "Fitted HistGradientBoostingClassifier only \u2014 no training data, no intermediate DataFrames, no other objects are pickled.",
        "provenance_scripts": [
            "generate_graph_v1.py",
            "experiment2_features.py",
            "experiment2_eval.py",
        ],
    }
    with open(ARTIFACT_DIR / "training_metadata.json", "w") as f:
        json.dump(training_metadata, f, indent=2)

    # ---- evaluation_metadata.json ----
    this_run = out["ML (graph features)"]
    this_run_clean = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in this_run.items()}

    evaluation_metadata = {
        "model_version": MODEL_VERSION,
        "dataset": "synthetic",
        "validation_type": "synthetic",
        "this_run_holdout_metrics": {
            "source": "recomputed_in_this_training_run",
            "seed": CANONICAL_SEED,
            "n_test_complaints": this_run_clean.get("n_complaints"),
            "metrics": this_run_clean,
        },
        "prior_validation_results": {
            "label": "PRIOR VALIDATION RESULTS \u2014 NOT NEWLY GENERATED IN THIS STAGE",
            "source": "prior_research_experiment_not_recomputed_on_demo_data",
            "reference_document": "SentinelTrace_Experiment2_FINAL_Report.md",
            "reference_data_files": [
                "FINAL_multiseed_summary.csv", "FINAL_noise_sweep.csv",
                "FINAL_hop_stratification.csv", "FINAL_distshift_reference.csv",
                "FINAL_distshift_result.csv", "FINAL_ablation.csv",
            ],
            "headline_8seed_ml_result_mean_std": {
                "P_at_1": [0.956, 0.017],
                "P_at_5": [0.352, 0.007],
                "Recall_at_5": [0.985, 0.004],
                "MRR": [0.976, 0.010],
                "FPR": [0.184, 0.012],
                "note": "Copied verbatim from SentinelTrace_Experiment2_FINAL_Report.md's final comparison table (8 seeds, hardened config). NOT computed in this training run \u2014 shown only as the prior research reference point.",
            },
        },
    }
    with open(ARTIFACT_DIR / "evaluation_metadata.json", "w") as f:
        json.dump(evaluation_metadata, f, indent=2)


def main():
    print("=" * 70)
    print("SentinelTrace Model A (mule-chain identification) — Stage 1 training")
    print("=" * 70)

    print("\n[1/5] Generating canonical Model A synthetic world...")
    generate_and_persist_world()
    print(f"    wrote accounts.csv, transactions.csv, complaints.csv, generation_meta.json to {DATA_DIR}")

    print("\n[2/5] Reloading world from persisted CSVs (round-trip check)...")
    accounts, transactions, complaints = load_persisted_world()
    print(f"    accounts={len(accounts)}  transactions={len(transactions)}  complaints={len(complaints)}")

    print("\n[3/5] Building candidate table (BFS + feature engineering) from the RELOADED data...")
    feat = build_and_persist_candidates(accounts, transactions, complaints)
    print(f"    candidate rows={len(feat)}  complaints_with_candidates={feat.complaint_id.nunique()}  positive_rate={feat.label.mean():.4f}")
    print(f"    wrote candidates.csv to {DATA_DIR}")

    print("\n[4/5] Training model_a_v1 (HistGradientBoostingClassifier, unmodified)...")
    model, out, train, test, split_day, artifact_path = train_and_save(feat)
    m = out["ML (graph features)"]
    print(f"    split_day={split_day}  train_rows={len(train)}  test_rows={len(test)}")
    print(f"    this-run holdout: P@1={m['P_at_1']:.4f}  P@5={m['P_at_5']:.4f}  Recall@5={m['Recall_at_5']:.4f}  MRR={m['MRR']:.4f}  FPR={m['FPR']:.4f}")
    print(f"    saved {artifact_path}")

    print("\n[5/5] Writing metadata...")
    write_metadata(feat, out, train, test, split_day, artifact_path)
    print(f"    wrote feature_metadata.json, training_metadata.json, evaluation_metadata.json to {ARTIFACT_DIR}")

    print("\nDone.")


if __name__ == "__main__":
    main()
