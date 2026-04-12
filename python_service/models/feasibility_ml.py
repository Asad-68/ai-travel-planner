"""
models/feasibility_ml.py
------------------------
ML pipeline for:
  • Trip cost prediction   -> Ridge Regression
  • Affordability check    -> Logistic Regression (balanced)

Preprocessing (inside sklearn Pipeline):
  1. SimpleImputer  — median for numerics, most_frequent for categoricals
  2. IQR clipping   — applied via FunctionTransformer before scaling
  3. Feature engineering:
       cost_per_day        = total_cost / num_days
       budget_utilization  = total_cost / budget  (clipped 0-2)
       distance_per_day    = distance_km / num_days
       hotel_food_ratio    = avg_hotel_per_night / (avg_food_per_day + 1)
       budget_per_day      = budget / num_days
       spend_intensity     = (hotel + food) / budget * 100
  4. StandardScaler for numerics
  5. OneHotEncoder  for categoricals

Model persistence via joblib.
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

NUMERIC_BASE_FEATURES = [
    "budget",
    "num_days",
    "distance_km",
    "avg_hotel_per_night",
    "avg_food_per_day",
    "num_cities",
    # Engineered
    "budget_per_day",
    "hotel_food_ratio",
    "spend_intensity",
    "distance_per_day",
    "budget_utilization",
]

CATEGORICAL_FEATURES = ["season", "trip_type"]

VALID_SEASONS   = {"winter", "summer", "monsoon", "spring", "autumn"}
VALID_TRIP_TYPES = {"solo", "friends", "family", "couple", "business"}


# ─── IQR Clipping (stateless, applied per-column) ───────────────────────────

def _iqr_clip(X: np.ndarray) -> np.ndarray:
    """Clip each column to [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    X = X.copy().astype(float)
    for col_idx in range(X.shape[1]):
        col = X[:, col_idx]
        q1, q3 = np.percentile(col[~np.isnan(col)], [25, 75])
        iqr = q3 - q1
        X[:, col_idx] = np.clip(col, q1 - 1.5 * iqr, q3 + 1.5 * iqr)
    return X


# ─── Data Loading ────────────────────────────────────────────────────────────

def load_trip_data(path: str | Path = "data/trips.csv") -> pd.DataFrame:
    """Load trip data from CSV with basic type enforcement."""
    df = pd.read_csv(path)
    logger.info("Loaded trip data: %d rows, %d cols", *df.shape)
    return df


# ─── Preprocessing ───────────────────────────────────────────────────────────

def preprocess_trip_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full data-cleaning + feature-engineering pass on raw trip DataFrame.

    Steps:
      1. Remove duplicate rows
      2. Sanitise categorical fields
      3. Clamp binary interest flags to {0, 1}
      4. Engineer derived numeric features
      5. Recompute 'affordable' label for consistency

    Returns a cleaned DataFrame ready for model training.
    """
    df = df.copy()
    before = len(df)

    # 1. Drop perfect duplicates
    df = df.drop_duplicates().reset_index(drop=True)
    logger.info("Removed %d duplicate rows.", before - len(df))

    # 2. Sanitise categoricals (lowercase + fallback)
    df["season"] = (
        df["season"].astype(str).str.lower()
        .where(df["season"].astype(str).str.lower().isin(VALID_SEASONS), "summer")
    )
    df["trip_type"] = (
        df["trip_type"].astype(str).str.lower()
        .where(df["trip_type"].astype(str).str.lower().isin(VALID_TRIP_TYPES), "solo")
    )

    # 3. Clamp all interest_* columns to {0, 1}
    interest_cols = [c for c in df.columns if c.startswith("interest_")]
    for col in interest_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(0, 1).astype(int)

    # 4. Ensure core numerics are numeric (coerce bad values to NaN for imputer)
    numeric_cols = [
        "budget", "num_days", "distance_km",
        "avg_hotel_per_night", "avg_food_per_day",
        "num_cities", "total_cost",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 5. Feature engineering (use .clip to guard division by zero)
    nd  = df["num_days"].clip(lower=1)
    bud = df["budget"].clip(lower=1)
    fd  = df["avg_food_per_day"].fillna(0)

    df["budget_per_day"]    = bud / nd
    df["hotel_food_ratio"]  = df["avg_hotel_per_night"] / (fd + 1)
    df["spend_intensity"]   = (df["avg_hotel_per_night"] + fd) / bud * 100
    df["distance_per_day"]  = df["distance_km"] / nd
    df["budget_utilization"] = (df["total_cost"] / bud).clip(0, 2)

    # 6. Recompute affordability label to stay consistent
    df["affordable"] = (df["total_cost"] <= df["budget"]).astype(int)

    logger.info(
        "Preprocessing complete. Shape: %s | Affordable dist: %s",
        df.shape,
        df["affordable"].value_counts().to_dict(),
    )
    return df


# ─── Feature Column Helpers ──────────────────────────────────────────────────

def _get_feature_columns(df: pd.DataFrame) -> Tuple[list, list]:
    """Return (numeric_features, categorical_features) based on DataFrame columns."""
    interest_cols = [c for c in df.columns if c.startswith("interest_")]
    numeric = [c for c in NUMERIC_BASE_FEATURES + interest_cols if c in df.columns]
    categorical = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    return numeric, categorical


def _build_preprocessor(numeric_features: list, categorical_features: list) -> ColumnTransformer:
    """
    Construct a ColumnTransformer that:
      • Imputes -> clips outliers -> scales  (numeric)
      • Imputes -> one-hot encodes          (categorical)
    """
    numeric_pipeline = Pipeline([
        ("imputer",  SimpleImputer(strategy="median")),
        ("iqr_clip", FunctionTransformer(_iqr_clip, validate=False)),
        ("scaler",   StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    return ColumnTransformer(transformers=[
        ("num", numeric_pipeline,      numeric_features),
        ("cat", categorical_pipeline,  categorical_features),
    ])


# ─── Regression — Trip Cost Prediction ──────────────────────────────────────

def build_regression_model(df: pd.DataFrame, alpha: float = 1.0, cv: int = 5) -> Pipeline:
    """
    Train a Ridge Regression model to predict ``total_cost``.

    Returns a fitted sklearn Pipeline.
    Reports cross-validated MAE to logger.
    """
    df = preprocess_trip_data(df)
    numeric_features, categorical_features = _get_feature_columns(df)

    X = df[numeric_features + categorical_features]
    y = df["total_cost"]

    preprocessor = _build_preprocessor(numeric_features, categorical_features)
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("model",      Ridge(alpha=alpha)),
    ])

    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="neg_mean_absolute_error")
    logger.info(
        "[Regression] %d-fold CV MAE: %.2f ± %.2f",
        cv, -scores.mean(), scores.std(),
    )

    pipeline.fit(X, y)
    logger.info("[Regression] Model trained on %d samples.", len(df))
    return pipeline


# ─── Classification — Affordability ──────────────────────────────────────────

def build_classification_model(
    df: pd.DataFrame, C: float = 1.0, max_iter: int = 2000, cv: int = 5
) -> Pipeline:
    """
    Train a Logistic Regression classifier to predict ``affordable`` (0/1).

    Returns a fitted sklearn Pipeline.
    Reports cross-validated accuracy + test-set classification report to logger.
    """
    df = preprocess_trip_data(df)
    numeric_features, categorical_features = _get_feature_columns(df)

    X = df[numeric_features + categorical_features]
    y = df["affordable"]

    preprocessor = _build_preprocessor(numeric_features, categorical_features)
    pipeline = Pipeline([
        ("preprocess", preprocessor),
        ("model",      LogisticRegression(C=C, max_iter=max_iter, class_weight="balanced")),
    ])

    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    logger.info(
        "[Classification] %d-fold CV Accuracy: %.3f ± %.3f",
        cv, scores.mean(), scores.std(),
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    report = classification_report(
        y_test, y_pred, target_names=["Not Affordable", "Affordable"]
    )
    logger.info("[Classification] Test report:\n%s", report)

    # Refit on full dataset for production use
    pipeline.fit(X, y)
    logger.info("[Classification] Model trained on %d samples.", len(df))
    return pipeline


# ─── Model Persistence ────────────────────────────────────────────────────────

def save_models(
    reg_model: Pipeline,
    clf_model: Pipeline,
    reg_path: str | Path,
    clf_path: str | Path,
) -> None:
    """Persist regression and classification pipelines to disk using joblib."""
    joblib.dump(reg_model, reg_path)
    joblib.dump(clf_model, clf_path)
    logger.info("Saved reg_model -> %s", reg_path)
    logger.info("Saved clf_model -> %s", clf_path)


def load_models(
    reg_path: str | Path,
    clf_path: str | Path,
) -> Tuple[Pipeline, Pipeline]:
    """Load persisted models from disk. Raises FileNotFoundError if missing."""
    reg_model = joblib.load(reg_path)
    clf_model = joblib.load(clf_path)
    logger.info("Loaded reg_model <- %s", reg_path)
    logger.info("Loaded clf_model <- %s", clf_path)
    return reg_model, clf_model
