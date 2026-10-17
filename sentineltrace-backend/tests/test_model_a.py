import sys
from pathlib import Path

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services import model_a  # noqa: E402


def test_model_a_loaded_at_startup(client):
    # `client` fixture triggers the app lifespan, which loads Model A.
    assert model_a.is_loaded() is True


def test_model_a_feature_contract():
    registry = model_a.get_model_a()
    assert registry.feature_count == 8
    assert registry.feature_names_ordered == [
        "hop_distance", "pass_through_ratio", "fan_in_recent_30d", "out_degree_recent_30d",
        "account_age_days", "confirmed_history_count", "amount_consistency",
        "subgraph_degree_centrality",
    ]


def test_model_a_genuine_inference_on_real_candidate(client):
    registry = model_a.get_model_a()
    candidates = pd.read_csv(BACKEND_ROOT / "data" / "model_a" / "candidates.csv")
    real_row = candidates[candidates.label == 1].iloc[0]
    feature_row = {f: float(real_row[f]) for f in registry.feature_names_ordered}
    proba = registry.predict_proba(feature_row)
    assert 0.0 <= proba <= 1.0
    # This specific known-mule candidate should score high — real behavior,
    # not an arbitrary assertion (matches Stage 1's verify_model_a.py result).
    assert proba > 0.9
