"""
scripts/check_model_a_compatibility.py

Verifies that:
  model_a_v1.pkl  <->  feature_metadata.json  <->  actual candidate feature columns

agree with each other. Does NOT retrain or modify anything — pure
verification, using a real candidate row from data/model_a/candidates.csv.
"""
import json
import sys
from pathlib import Path

import joblib
import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))


class CompatibilityError(RuntimeError):
    pass


def main():
    artifact_path = BACKEND_ROOT / "artifacts" / "model_a" / "model_a_v1.pkl"
    feature_meta_path = BACKEND_ROOT / "artifacts" / "model_a" / "feature_metadata.json"
    candidates_path = BACKEND_ROOT / "data" / "model_a" / "candidates.csv"

    print("=" * 70)
    print("Model A compatibility check")
    print("=" * 70)

    model = joblib.load(artifact_path)
    print(f"\n[1] Loaded model: {type(model).__name__}")

    with open(feature_meta_path) as f:
        feature_metadata = json.load(f)
    feature_names = feature_metadata["feature_names_ordered"]
    feature_count = feature_metadata["feature_count"]
    print(f"[2] feature_metadata.json declares {feature_count} features: {feature_names}")

    if len(feature_names) != feature_count:
        raise CompatibilityError(f"feature_count ({feature_count}) != len(feature_names_ordered) ({len(feature_names)})")

    n_features_in = getattr(model, "n_features_in_", None)
    if n_features_in is not None:
        print(f"[3] Model reports n_features_in_ = {n_features_in}")
        if n_features_in != feature_count:
            raise CompatibilityError(f"Model expects {n_features_in} features but metadata declares {feature_count}")
    else:
        print("[3] Model does not expose n_features_in_ (older sklearn) — skipping that check")

    candidates = pd.read_csv(candidates_path)
    missing_cols = [c for c in feature_names if c not in candidates.columns]
    if missing_cols:
        raise CompatibilityError(f"candidates.csv is missing expected feature columns: {missing_cols}")
    print(f"[4] candidates.csv has all {len(feature_names)} expected feature columns")

    real_row = candidates[candidates.label == 1].iloc[0]
    x = real_row[feature_names].to_frame().T.astype(float)
    proba = model.predict_proba(x)[0, 1]
    print(f"[5] Real inference on candidate_id={int(real_row.candidate_id)} (complaint {int(real_row.complaint_id)}): "
          f"P[mule]={proba:.6f}")

    print("\nRESULT: model_a_v1.pkl, feature_metadata.json, and candidates.csv are mutually compatible.")


if __name__ == "__main__":
    try:
        main()
    except CompatibilityError as exc:
        print(f"\nCOMPATIBILITY CHECK FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
