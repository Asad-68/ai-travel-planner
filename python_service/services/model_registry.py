"""
services/model_registry.py
---------------------------
Singleton that owns all trained ML model objects.

Responsibilities:
  • Load models from disk (joblib) if artefacts exist and are not stale
  • Train models from scratch if artefacts are absent
  • Save newly-trained models to disk automatically
  • Expose a clean interface to the rest of the application

Usage:
    registry = ModelRegistry()
    registry.load_or_train()          # call once at startup
    reg_model   = registry.reg_model
    clf_model   = registry.clf_model
    cluster_id  = registry.assign_cluster(user_features)
    persona     = registry.cluster_label(cluster_id)
"""

from __future__ import annotations

import logging
from pathlib import Path

import config
from models.feasibility_ml import (
    build_classification_model,
    build_regression_model,
    load_models,
    load_trip_data,
    save_models,
)
from models.personalization import (
    assign_cluster,
    build_kmeans_model,
    get_cluster_label,
    load_kmeans,
    load_user_data,
    save_kmeans,
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central store for all ML model artefacts used by the travel planner.

    Attributes (available after load_or_train())
    -------------------------------------------
    reg_model     : fitted Ridge regression pipeline
    clf_model     : fitted Logistic Regression pipeline
    scaler        : StandardScaler used for KMeans features
    kmeans        : fitted KMeans model
    feature_cols  : list of feature column names for clustering
    """

    def __init__(self) -> None:
        self.reg_model    = None
        self.clf_model    = None
        self.scaler       = None
        self.kmeans       = None
        self.feature_cols = None
        self._ready       = False

    # ── Public Interface ────────────────────────────────────────────────────

    def load_or_train(self, force_retrain: bool = False) -> None:
        """
        Initialise all models.

        If saved artefacts exist on disk (and force_retrain is False),
        load them directly — no retraining overhead on restarts.
        Otherwise, train from CSV data and persist to disk.

        Parameters
        ----------
        force_retrain : always retrain even if artefacts exist
        """
        if self._artefacts_exist() and not force_retrain:
            logger.info("Saved model artefacts found — loading from disk.")
            self._load_from_disk()
        else:
            logger.info("Training models from scratch (artefacts missing or force_retrain=True).")
            self._train_and_save()

        self._ready = True
        logger.info("ModelRegistry ready.")

    def assign_cluster(self, user_features: dict) -> int:
        """
        Assign a new user to a cluster.

        Parameters
        ----------
        user_features : dict mapping feature name → value;
                        missing keys default to 0
        """
        self._check_ready()
        return assign_cluster(
            self.scaler, self.kmeans, user_features, self.feature_cols
        )

    def cluster_label(self, cluster_id: int) -> str:
        """Return a human-readable persona string for a cluster ID."""
        self._check_ready()
        return get_cluster_label(
            cluster_id, self.kmeans, self.scaler, self.feature_cols
        )

    # ── Private Helpers ─────────────────────────────────────────────────────

    def _check_ready(self) -> None:
        if not self._ready:
            raise RuntimeError(
                "ModelRegistry not initialised — call load_or_train() first."
            )

    def _artefacts_exist(self) -> bool:
        paths = [
            config.REG_MODEL_PATH,
            config.CLF_MODEL_PATH,
            config.KMEANS_SCALER_PATH,
            config.KMEANS_MODEL_PATH,
            config.CLUSTER_FEATURE_COLS_PATH,
        ]
        return all(Path(p).exists() for p in paths)

    def _load_from_disk(self) -> None:
        self.reg_model, self.clf_model = load_models(
            config.REG_MODEL_PATH, config.CLF_MODEL_PATH
        )
        self.scaler, self.kmeans, self.feature_cols = load_kmeans(
            config.KMEANS_SCALER_PATH,
            config.KMEANS_MODEL_PATH,
            config.CLUSTER_FEATURE_COLS_PATH,
        )

    def _train_and_save(self) -> None:
        # ── Feasibility models ───────────────────────────────────────────
        trip_df        = load_trip_data(config.TRIPS_CSV)
        self.reg_model = build_regression_model(
            trip_df, alpha=config.RIDGE_ALPHA, cv=config.CV_FOLDS
        )
        self.clf_model = build_classification_model(
            trip_df, C=config.LOGREG_C, max_iter=config.LOGREG_MAX_ITER, cv=config.CV_FOLDS
        )
        save_models(
            self.reg_model, self.clf_model,
            config.REG_MODEL_PATH, config.CLF_MODEL_PATH,
        )

        # ── Clustering model ─────────────────────────────────────────────
        user_df = load_user_data(config.USERS_CSV)
        self.scaler, self.kmeans, self.feature_cols, _ = build_kmeans_model(
            user_df,
            max_k=config.KMEANS_MAX_K,
            min_rows_per_k=config.KMEANS_MIN_ROWS_PER_K,
        )
        save_kmeans(
            self.scaler, self.kmeans, self.feature_cols,
            config.KMEANS_SCALER_PATH,
            config.KMEANS_MODEL_PATH,
            config.CLUSTER_FEATURE_COLS_PATH,
        )


# ── Module-level singleton ────────────────────────────────────────────────────

registry = ModelRegistry()
