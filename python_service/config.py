"""
config.py
---------
Central configuration for the AI Travel Planner Python service.
All tunable constants live here — never hardcode paths or hyper-parameters
in individual modules.
"""

import os
from pathlib import Path

# ─── Base Paths ──────────────────────────────────────────────────────────────

BASE_DIR        = Path(__file__).parent.resolve()
DATA_DIR        = BASE_DIR / "data"
SAVED_MODELS_DIR = BASE_DIR / "saved_models"

# Create saved_models directory on first import
SAVED_MODELS_DIR.mkdir(exist_ok=True)

# ─── Data Files ───────────────────────────────────────────────────────────────

TRIPS_CSV = DATA_DIR / "trips.csv"
USERS_CSV = DATA_DIR / "users.csv"
POIS_CSV  = DATA_DIR / "pois.csv"

# ─── Saved Model Paths ────────────────────────────────────────────────────────

REG_MODEL_PATH          = SAVED_MODELS_DIR / "reg_model.joblib"
CLF_MODEL_PATH          = SAVED_MODELS_DIR / "clf_model.joblib"
KMEANS_SCALER_PATH      = SAVED_MODELS_DIR / "kmeans_scaler.joblib"
KMEANS_MODEL_PATH       = SAVED_MODELS_DIR / "kmeans_model.joblib"
CLUSTER_FEATURE_COLS_PATH = SAVED_MODELS_DIR / "cluster_feature_cols.json"

# ─── ML Hyper-parameters ─────────────────────────────────────────────────────

# Regression
RIDGE_ALPHA        = 1.0
CV_FOLDS           = 5
TEST_SIZE          = 0.2
RANDOM_STATE       = 42

# Classification
LOGREG_C           = 1.0
LOGREG_MAX_ITER    = 2000

# Clustering
KMEANS_MAX_K       = 8          # Maximum clusters to evaluate
KMEANS_N_INIT      = 10
KMEANS_MIN_ROWS_PER_K = 3      # Need at least this many rows per cluster

# ─── Route Planning ──────────────────────────────────────────────────────────

MAX_DAILY_HOURS    = 8.0        # Max visiting hours per day
DEFAULT_AVG_SPEED  = 25.0       # km/h for intra-city travel (auto/cab)
TRAVEL_TIME_WEIGHT = 0.3        # Weight applied to travel-time penalty in scoring

# ─── API Settings ─────────────────────────────────────────────────────────────

FLASK_PORT         = 5001
FLASK_DEBUG        = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# ─── AI / Gemini Settings ─────────────────────────────────────────────────────

GEMINI_MODEL_NAME     = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
NARRATIVE_MAX_WORDS   = 120
CHAT_MEMORY_TURNS     = 6       # Number of (user, assistant) pairs to keep in memory

# ─── Logging ──────────────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = BASE_DIR / "app.log"
