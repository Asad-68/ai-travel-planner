"""
app.py
------
Flask entry point for the AI Travel Planner Python service.

Responsibilities (thin layer only):
  • Configure structured logging
  • Initialise the ModelRegistry at startup
  • Define HTTP routes that delegate to service functions
  • Enforce consistent JSON response envelope
  • Handle errors with appropriate HTTP status codes

All business logic lives in services/trip_service.py.
All ML logic lives in models/.
"""

from __future__ import annotations

import logging
import logging.handlers
import time
from functools import wraps

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

import config
from models.genai import ConversationMemory, chat_with_ai
from services.model_registry import registry
from services.trip_service import plan_trip, validate_trip_input

# ─── Logging Setup ────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    """Set up console + rotating file logging."""
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        fh = logging.handlers.RotatingFileHandler(
            config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handlers.append(fh)
    except OSError:
        pass  # Don't crash if log file is not writable

    logging.basicConfig(level=log_level, format=fmt, datefmt=datefmt, handlers=handlers)

_configure_logging()
logger = logging.getLogger(__name__)

# ─── App Initialisation ───────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

_START_TIME = time.time()

# Initialise models (load from disk or train)
registry.load_or_train()

# Per-session chat memory store  {session_id: ConversationMemory}
_chat_sessions: dict[str, ConversationMemory] = {}


# ─── Response Helpers ─────────────────────────────────────────────────────────

def _ok(data: dict | list, message: str = "Success") -> tuple:
    """Return a 200 JSON response with consistent envelope."""
    return jsonify({"status": "ok", "message": message, "data": data}), 200


def _error(message: str, code: int = 400) -> tuple:
    """Return an error JSON response with consistent envelope."""
    logger.warning("HTTP %d: %s", code, message)
    return jsonify({"status": "error", "message": message, "data": None}), code


def _require_json(f):
    """Decorator — reject requests without a JSON body."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return _error("Request must have Content-Type: application/json.", 415)
        return f(*args, **kwargs)
    return wrapper


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Service health check — returns uptime and model status."""
    uptime = round(time.time() - _START_TIME, 1)
    return _ok({
        "uptime_seconds": uptime,
        "models_ready":   registry._ready,
        "kmeans_k":       registry.kmeans.n_clusters if registry.kmeans else None,
    }, "Service is healthy.")


@app.route("/api/cities", methods=["GET"])
def get_cities():
    """Return sorted list of cities available in the POI database."""
    try:
        df     = pd.read_csv(config.POIS_CSV)
        cities = sorted(df["city"].dropna().unique().tolist())
        return _ok(cities)
    except Exception as exc:
        logger.error("Failed to load cities: %s", exc)
        return _error("Could not retrieve city list.", 500)


@app.route("/api/plan-trip", methods=["POST"])
@_require_json
def plan_trip_route():
    """
    Plan a multi-day trip itinerary.

    Required JSON fields: see services/trip_service._REQUIRED_FIELDS
    Optional fields: interest_nightlife, interest_adventure, interest_food,
                     user_features (dict)
    """
    data = request.get_json(silent=True) or {}

    # Input validation
    errors = validate_trip_input(data)
    if errors:
        return _error(" | ".join(errors), 400)

    try:
        result = plan_trip(data, registry=registry)
        return _ok(result)
    except Exception as exc:
        logger.exception("plan_trip failed: %s", exc)
        return _error("Trip planning failed due to an internal error.", 500)


@app.route("/api/chat", methods=["POST"])
@_require_json
def chat():
    """
    Travel chatbot endpoint with per-session conversation memory.

    JSON body:
      message    : str  (required)
      itinerary  : dict (optional) — pass the /api/plan-trip response
      session_id : str  (optional) — unique ID to maintain conversation history
    """
    data = request.get_json(silent=True) or {}

    message = data.get("message", "").strip()
    if not message:
        return _error("'message' field is required and cannot be empty.", 400)

    itinerary  = data.get("itinerary")
    session_id = data.get("session_id", "default")

    # Retrieve or create conversation memory for this session
    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = ConversationMemory(
            max_turns=config.CHAT_MEMORY_TURNS
        )
    memory = _chat_sessions[session_id]

    try:
        reply = chat_with_ai(message, itinerary=itinerary, memory=memory)
        return _ok({"reply": reply, "session_id": session_id})
    except Exception as exc:
        logger.exception("Chat failed: %s", exc)
        return _error("Chat service encountered an error.", 500)


@app.route("/api/reset-chat", methods=["POST"])
@_require_json
def reset_chat():
    """Clear conversation memory for a given session."""
    data       = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "default")
    if session_id in _chat_sessions:
        _chat_sessions[session_id].clear()
    return _ok({"session_id": session_id}, "Conversation memory cleared.")


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return _error("The requested endpoint does not exist.", 404)


@app.errorhandler(405)
def method_not_allowed(_):
    return _error("HTTP method not allowed on this endpoint.", 405)


@app.errorhandler(500)
def internal_error(exc):
    logger.exception("Unhandled 500: %s", exc)
    return _error("An unexpected server error occurred.", 500)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting AI Travel Planner service on port %d", config.FLASK_PORT)
    app.run(port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
