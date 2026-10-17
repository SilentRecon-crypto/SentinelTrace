"""
Model A loading service.

Loads artifacts/model_a/model_a_v1.pkl exactly once, at application startup
(via the FastAPI lifespan handler in app.main), and holds it in memory for
the life of the process. Nothing here retrains, retunes, or modifies the
model — it only loads the existing artifact and validates it against its
own recorded feature metadata.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from app.config import settings


class ModelALoadError(RuntimeError):
    """Raised when model_a_v1.pkl or its metadata cannot be loaded/validated."""


@dataclass
class ModelARegistry:
    model: Any
    version: str
    feature_names_ordered: list[str]
    feature_count: int
    training_metadata: dict
    feature_metadata: dict

    def predict_proba(self, feature_row: dict[str, float]) -> float:
        """Score a single candidate given a dict of {feature_name: value}.
        Feature ordering is taken from feature_names_ordered (the authoritative
        FEATURE_COLS order recorded in feature_metadata.json), not from
        dict insertion order, so callers cannot accidentally scramble it.
        """
        import pandas as pd

        missing = [f for f in self.feature_names_ordered if f not in feature_row]
        if missing:
            raise ModelALoadError(f"Missing required Model A features: {missing}")
        ordered = {f: [feature_row[f]] for f in self.feature_names_ordered}
        x = pd.DataFrame(ordered)
        return float(self.model.predict_proba(x)[0, 1])

    def predict_proba_batch(self, feature_df):
        """Score many candidates at once. `feature_df` must contain at least
        the columns in feature_names_ordered; extra columns (e.g. candidate_id,
        complaint_id) are ignored. Returns a 1-D numpy array of P(is_mule)
        in the same row order as feature_df. Feature columns are explicitly
        reordered to feature_names_ordered before calling the model, so the
        caller's column order never matters.
        """
        missing = [f for f in self.feature_names_ordered if f not in feature_df.columns]
        if missing:
            raise ModelALoadError(f"Missing required Model A features: {missing}")
        x = feature_df[self.feature_names_ordered]
        return self.model.predict_proba(x)[:, 1]


_registry: ModelARegistry | None = None


def load_model_a() -> ModelARegistry:
    """Load the model + metadata from disk and validate consistency. Called
    once from the FastAPI lifespan startup handler."""
    global _registry

    model_path = Path(settings.model_a_path)
    feature_meta_path = Path(settings.model_a_feature_metadata_path)
    training_meta_path = Path(settings.model_a_training_metadata_path)

    if not model_path.exists():
        raise ModelALoadError(f"Model A artifact not found at {model_path}. Run train_model_a.py (Stage 1) first.")
    if not feature_meta_path.exists():
        raise ModelALoadError(f"Model A feature metadata not found at {feature_meta_path}.")
    if not training_meta_path.exists():
        raise ModelALoadError(f"Model A training metadata not found at {training_meta_path}.")

    model = joblib.load(model_path)

    with open(feature_meta_path) as f:
        feature_metadata = json.load(f)
    with open(training_meta_path) as f:
        training_metadata = json.load(f)

    feature_names_ordered = feature_metadata["feature_names_ordered"]
    feature_count = feature_metadata["feature_count"]

    if len(feature_names_ordered) != feature_count:
        raise ModelALoadError(
            f"feature_metadata.json is internally inconsistent: "
            f"feature_count={feature_count} but feature_names_ordered has {len(feature_names_ordered)} entries."
        )

    # Sanity-check the loaded estimator actually expects this many features,
    # where the fitted estimator exposes that information.
    n_features_in = getattr(model, "n_features_in_", None)
    if n_features_in is not None and n_features_in != feature_count:
        raise ModelALoadError(
            f"Model/feature-metadata mismatch: model.n_features_in_={n_features_in} "
            f"but feature_metadata.json declares {feature_count} features."
        )

    _registry = ModelARegistry(
        model=model,
        version=feature_metadata.get("model_version", settings.model_a_version),
        feature_names_ordered=feature_names_ordered,
        feature_count=feature_count,
        training_metadata=training_metadata,
        feature_metadata=feature_metadata,
    )
    return _registry


def get_model_a() -> ModelARegistry:
    """FastAPI dependency: returns the already-loaded registry. Raises if
    load_model_a() was never called (i.e. startup failed) — callers must not
    silently proceed without a model."""
    if _registry is None:
        raise ModelALoadError("Model A has not been loaded. This should only happen if application startup failed.")
    return _registry


def is_loaded() -> bool:
    return _registry is not None
