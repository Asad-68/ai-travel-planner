"""
models/personalization.py
--------------------------
User segmentation via KMeans clustering.

Preprocessing:
  1. Drop NaN / duplicates
  2. Clamp binary flags to {0, 1}
  3. Clip numeric ranges (budget, trip_length, travel_frequency)
  4. Derive: budget_tier (cut), adventure_score
  5. StandardScaler

Optimal k selection:
  • Elbow method (inertia)
  • Silhouette score
  • Cap at min(KMEANS_MAX_K, n // KMEANS_MIN_ROWS_PER_K)

Model persistence via joblib + JSON for feature column list.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# ─── Feature Columns ─────────────────────────────────────────────────────────

# All possible extended feature columns (subset actually used depends on CSV)
CANDIDATE_FEATURE_COLS: List[str] = [
    "avg_budget_per_day",
    "preferred_trip_length",
    "interest_nature",
    "interest_heritage",
    "interest_nightlife",
    "interest_adventure",
    "interest_food",
    "interest_shopping",
    "travel_frequency",
    "solo_preference",
    # Derived (added during preprocessing)
    "budget_tier",
    "adventure_score",
]

# Human-readable cluster persona templates keyed by (budget_tier, dominant_interest)
_PERSONA_TEMPLATES = {
    "high_nature":    "Nature Explorer",
    "high_heritage":  "Heritage Seeker",
    "high_adventure": "Adventure Junkie",
    "high_nightlife": "Night Owl",
    "high_food":      "Foodie Traveller",
    "high_shopping":  "Shopping Enthusiast",
    "budget":         "Budget Traveller",
    "premium":        "Premium Explorer",
    "default":        "General Traveller",
}


# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_user_data(path: str | Path = "data/users.csv") -> pd.DataFrame:
    """Load user profile data from CSV."""
    df = pd.read_csv(path)
    logger.info("Loaded user data: %d rows, %d cols", *df.shape)
    return df


# ─── Preprocessing ────────────────────────────────────────────────────────────

def preprocess_user_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and enrich user DataFrame before clustering.

    Returns a new DataFrame with derived features appended.
    """
    df = df.copy()
    before = len(df)

    # 1. Drop NaN rows and perfect duplicates
    df = df.dropna().drop_duplicates().reset_index(drop=True)
    logger.info("Removed %d invalid/duplicate user rows. Remaining: %d", before - len(df), len(df))

    if df.empty:
        raise ValueError("User dataset is empty after cleaning — cannot cluster.")

    # 2. Clamp binary columns to [0, 1]
    binary_cols = [c for c in df.columns if c.startswith("interest_") or c == "solo_preference"]
    for col in binary_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(0, 1).astype(int)

    # 3. Clip numeric columns to sensible ranges
    if "avg_budget_per_day" in df.columns:
        df["avg_budget_per_day"] = pd.to_numeric(df["avg_budget_per_day"], errors="coerce").clip(lower=0)
    if "preferred_trip_length" in df.columns:
        df["preferred_trip_length"] = pd.to_numeric(df["preferred_trip_length"], errors="coerce").clip(1, 30)
    if "travel_frequency" in df.columns:
        df["travel_frequency"] = pd.to_numeric(df["travel_frequency"], errors="coerce").clip(0, 52)

    # 4. Derive budget_tier: 0=budget (<800/day), 1=mid, 2=premium (>2000/day)
    if "avg_budget_per_day" in df.columns:
        df["budget_tier"] = pd.cut(
            df["avg_budget_per_day"],
            bins=[0, 800, 2000, np.inf],
            labels=[0, 1, 2],
        ).astype(int)

    # 5. Derive adventure score (higher if adventurer + group traveller)
    if "interest_adventure" in df.columns and "solo_preference" in df.columns:
        df["adventure_score"] = df["interest_adventure"] + (1 - df["solo_preference"]) * 0.5

    return df


# ─── Optimal k Selection ──────────────────────────────────────────────────────

def find_optimal_k(X_scaled: np.ndarray, max_k: int = 8, n_init: int = 10) -> int:
    """
    Evaluate KMeans for k in [2, max_k] and return the k with the
    highest silhouette score (ties broken by lower inertia).

    Parameters
    ----------
    X_scaled : already-scaled feature matrix
    max_k    : upper bound on clusters to test
    n_init   : KMeans n_init for stable results
    """
    max_k = max(2, min(max_k, len(X_scaled) - 1))
    best_k, best_score = 2, -1.0

    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=n_init)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        logger.debug("[KMeans] k=%d  inertia=%.1f  silhouette=%.4f", k, km.inertia_, score)
        if score > best_score:
            best_score, best_k = score, k

    logger.info("[KMeans] Optimal k=%d (silhouette=%.4f)", best_k, best_score)
    return best_k


# ─── Model Building ──────────────────────────────────────────────────────────

def build_kmeans_model(
    df: pd.DataFrame,
    k: int | None = None,
    max_k: int = 8,
    min_rows_per_k: int = 3,
) -> Tuple[StandardScaler, KMeans, List[str], pd.DataFrame]:
    """
    Preprocess user data, auto-select k via silhouette, fit KMeans.

    Returns
    -------
    scaler       : fitted StandardScaler
    kmeans       : fitted KMeans
    feature_cols : list of column names used for clustering
    df           : DataFrame with 'cluster' column appended
    """
    df = preprocess_user_data(df)

    # Select available feature columns
    feature_cols = [c for c in CANDIDATE_FEATURE_COLS if c in df.columns]
    if not feature_cols:
        raise ValueError("No valid feature columns found for clustering.")

    X = df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Determine optimal k
    if k is None:
        auto_max_k = min(max_k, len(df) // min_rows_per_k)
        k = find_optimal_k(X_scaled, max_k=auto_max_k)

    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    df = df.copy()
    df["cluster"] = kmeans.labels_

    _log_cluster_profiles(df, feature_cols)
    return scaler, kmeans, feature_cols, df


# ─── Cluster Profiling ────────────────────────────────────────────────────────

def _log_cluster_profiles(df: pd.DataFrame, feature_cols: list) -> None:
    """Log mean feature values per cluster and cluster sizes."""
    profile = df.groupby("cluster")[feature_cols].mean().round(2)
    sizes   = df["cluster"].value_counts().sort_index()
    logger.info("[KMeans] Cluster profiles:\n%s", profile.to_string())
    logger.info("[KMeans] Cluster sizes:\n%s", sizes.to_string())


def get_cluster_label(
    cluster_id: int,
    kmeans: KMeans,
    scaler: StandardScaler,
    feature_cols: list,
) -> str:
    """
    Return a human-readable persona string for a given cluster ID
    by inspecting the cluster centroid.
    """
    try:
        centroid_scaled = kmeans.cluster_centers_[cluster_id]
        centroid        = scaler.inverse_transform([centroid_scaled])[0]
        centroid_dict   = dict(zip(feature_cols, centroid))

        budget = centroid_dict.get("avg_budget_per_day", 1000)
        if budget < 800:
            return _PERSONA_TEMPLATES["budget"]
        if budget > 2000:
            return _PERSONA_TEMPLATES["premium"]

        # Find the dominant interest
        interest_keys = [c for c in feature_cols if c.startswith("interest_")]
        if interest_keys:
            dominant = max(interest_keys, key=lambda c: centroid_dict.get(c, 0))
            key = f"high_{dominant.replace('interest_', '')}"
            if key in _PERSONA_TEMPLATES:
                return _PERSONA_TEMPLATES[key]

        return _PERSONA_TEMPLATES["default"]
    except Exception:
        return _PERSONA_TEMPLATES["default"]


# ─── Inference ────────────────────────────────────────────────────────────────

def assign_cluster(
    scaler: StandardScaler,
    kmeans: KMeans,
    user_features: dict,
    feature_cols: list,
) -> int:
    """
    Assign a new user to a cluster.

    Parameters
    ----------
    user_features : dict of feature_col → value (missing keys default to 0)
    feature_cols  : list returned by build_kmeans_model()
    """
    x = np.array([[user_features.get(c, 0) for c in feature_cols]])
    x_scaled = scaler.transform(x)
    return int(kmeans.predict(x_scaled)[0])


# ─── Model Persistence ────────────────────────────────────────────────────────

def save_kmeans(
    scaler: StandardScaler,
    kmeans: KMeans,
    feature_cols: list,
    scaler_path: str | Path,
    kmeans_path: str | Path,
    cols_path:   str | Path,
) -> None:
    """Persist KMeans scaler, model, and feature columns to disk."""
    joblib.dump(scaler, scaler_path)
    joblib.dump(kmeans, kmeans_path)
    with open(cols_path, "w", encoding="utf-8") as f:
        json.dump(feature_cols, f)
    logger.info("Saved KMeans artefacts -> %s, %s, %s", scaler_path, kmeans_path, cols_path)


def load_kmeans(
    scaler_path: str | Path,
    kmeans_path: str | Path,
    cols_path:   str | Path,
) -> Tuple[StandardScaler, KMeans, List[str]]:
    """Load KMeans artefacts from disk."""
    scaler       = joblib.load(scaler_path)
    kmeans       = joblib.load(kmeans_path)
    with open(cols_path, "r", encoding="utf-8") as f:
        feature_cols = json.load(f)
    logger.info("Loaded KMeans artefacts <- %s, %s", scaler_path, kmeans_path)
    return scaler, kmeans, feature_cols
