"""
verify_model_a.py — Stage 1 independent verification.

Run this as its own `python3 verify_model_a.py` process (separate from
train_model_a.py) to prove the persisted artifact is genuinely reloadable
and usable for inference outside the training process/session.

Does NOT retrain anything. Only reads already-persisted files:
  - artifacts/model_a/model_a_v1.pkl
  - data/model_a/candidates.csv
"""
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESEARCH_DIR = ROOT / "research_model_a"
DATA_DIR = ROOT / "data" / "model_a"
ARTIFACT_DIR = ROOT / "artifacts" / "model_a"

sys.path.insert(0, str(RESEARCH_DIR))
from experiment2_features import FEATURE_COLS  # noqa: E402 — feature order, not re-derived by hand

print("=" * 70)
print("Model A — independent load + inference verification")
print(f"Running in process PID {__import__('os').getpid()} (separate from training)")
print("=" * 70)

# 1. Load the persisted artifact
artifact_path = ARTIFACT_DIR / "model_a_v1.pkl"
model = joblib.load(artifact_path)
print(f"\n[1] Loaded {artifact_path}")
print(f"    type: {type(model)}")
print(f"    sklearn params: {model.get_params()}")

# 2. Load real persisted candidates (not fabricated)
candidates = pd.read_csv(DATA_DIR / "candidates.csv")
print(f"\n[2] Loaded {len(candidates)} real persisted candidates from candidates.csv")

# Confirm the feature columns the model expects are all present
missing = [c for c in FEATURE_COLS if c not in candidates.columns]
assert not missing, f"Persisted candidates missing expected feature columns: {missing}"
print(f"    Confirmed all {len(FEATURE_COLS)} expected feature columns are present: {FEATURE_COLS}")

# 3. Pick two genuine real candidates: one true positive (label=1) and one
#    true negative (label=0), by ID — not synthesized.
pos_row = candidates[candidates.label == 1].iloc[0]
neg_row = candidates[candidates.label == 0].iloc[0]

print("\n[3] Genuine inference on real persisted candidates:")
for name, row in [("TRUE POSITIVE example (label=1 in data)", pos_row), ("TRUE NEGATIVE example (label=0 in data)", neg_row)]:
    x = row[FEATURE_COLS].to_frame().T.astype(float)
    proba = model.predict_proba(x)[0, 1]
    pred_class = int(model.predict(x)[0])
    print(f"\n  {name}")
    print(f"    complaint_id={int(row.complaint_id)}  candidate_account_id={int(row.candidate_id)}")
    print(f"    feature_vector = {dict(zip(FEATURE_COLS, [round(float(v), 4) for v in row[FEATURE_COLS]]))}")
    print(f"    model_score (P[is_mule_account]) = {proba:.6f}")
    print(f"    predicted_class = {pred_class}")

print("\n[4] Result: model loads independently and produces real inference output on real data.")
print("=" * 70)
