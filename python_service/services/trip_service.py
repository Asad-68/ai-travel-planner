"""
services/trip_service.py
-------------------------
Business logic layer for trip planning.

Extracts the orchestration concern out of app.py, making it:
  • Unit-testable independently of Flask
  • Reusable (e.g. from a CLI or scheduler)
  • Easy to extend (e.g. caching, async, batching)

Main entry point: plan_trip(data)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import config
from models.genai import generate_itinerary_narrative
from models.route_planners import load_pois, split_route_by_days

logger = logging.getLogger(__name__)

# Required fields and their expected Python types for validation
_REQUIRED_FIELDS: Dict[str, type] = {
    "city":                 str,
    "budget":               (int, float),
    "num_days":             int,
    "distance_km":          (int, float),
    "avg_hotel_per_night":  (int, float),
    "avg_food_per_day":     (int, float),
    "trip_type":            str,
    "season":               str,
    "interest_nature":      (int, float),
    "interest_heritage":    (int, float),
}


# ─── Input Validation ────────────────────────────────────────────────────────

def validate_trip_input(data: dict) -> List[str]:
    """
    Validate the incoming request payload.

    Returns a list of human-readable error strings.
    An empty list means the payload is valid.
    """
    errors = []

    for field, expected_type in _REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"Missing required field: '{field}'.")
            continue
        val = data[field]
        if not isinstance(val, expected_type):
            errors.append(
                f"Field '{field}' must be {expected_type}, got {type(val).__name__}."
            )

    # Business-logic bounds
    if "budget" in data and isinstance(data["budget"], (int, float)):
        if data["budget"] <= 0:
            errors.append("'budget' must be a positive number.")

    if "num_days" in data and isinstance(data["num_days"], int):
        if not (1 <= data["num_days"] <= 30):
            errors.append("'num_days' must be between 1 and 30.")

    return errors


# ─── Cost Calculation ────────────────────────────────────────────────────────

def _calculate_cost(
    itinerary: dict,
    avg_hotel_per_night: float,
    avg_food_per_day: float,
    num_days: int,
) -> float:
    """Compute total estimated trip cost from component breakdown."""
    hotel_cost = avg_hotel_per_night * num_days
    food_cost  = avg_food_per_day * num_days
    poi_spend  = sum(
        poi.get("avg_spend", 0)
        for day_data in itinerary.values()
        for poi in day_data.get("pois", [])
    )
    return float(hotel_cost + food_cost + poi_spend)


# ─── Plan Trip Orchestration ──────────────────────────────────────────────────

def plan_trip(data: dict, registry=None) -> dict:
    """
    Full trip-planning orchestration.

    Parameters
    ----------
    data     : validated request payload (see _REQUIRED_FIELDS)
    registry : ModelRegistry instance (imported lazily to avoid circular imports)

    Returns a structured response dict:
    {
      "status":               "ok",
      "cluster_id":           int,
      "cluster_label":        str,
      "itinerary":            {day1: {...}, ...},
      "num_days":             int,
      "time_spent_hours":     float,
      "predicted_total_cost": float,
      "affordable":           bool,
      "cost_breakdown":       {...}
    }
    """
    # Lazy import to avoid circular dependency at module load
    if registry is None:
        from services.model_registry import registry as _registry
        registry = _registry

    city                = data["city"]
    budget              = float(data["budget"])
    num_days            = int(data["num_days"])
    avg_hotel_per_night = float(data["avg_hotel_per_night"])
    avg_food_per_day    = float(data["avg_food_per_day"])
    trip_type           = data["trip_type"]
    season              = data["season"]
    interest_nature     = int(data.get("interest_nature", 0))
    interest_heritage   = int(data.get("interest_heritage", 0))
    interest_nightlife  = int(data.get("interest_nightlife", 0))
    interest_adventure  = int(data.get("interest_adventure", 0))
    interest_food       = int(data.get("interest_food", 0))

    user_prefs = {
        "Nature":    interest_nature,
        "Heritage":  interest_heritage,
        "Nightlife": interest_nightlife,
        "Adventure": interest_adventure,
        "Food":      interest_food,
    }

    # ── Clustering ───────────────────────────────────────────────────────
    raw_user_features = data.get("user_features", {})
    # Merge top-level interest fields into user_features for clustering
    merged_features = {
        "interest_nature":    interest_nature,
        "interest_heritage":  interest_heritage,
        "interest_nightlife": interest_nightlife,
        "interest_adventure": interest_adventure,
        "interest_food":      interest_food,
        **raw_user_features,
    }
    cluster_id    = registry.assign_cluster(merged_features)
    cluster_label = registry.cluster_label(cluster_id)
    logger.info(
        "User assigned to cluster %d ('%s')", cluster_id, cluster_label
    )

    # ── POI Loading ──────────────────────────────────────────────────────
    pois = load_pois(city=city, path=str(config.POIS_CSV))
    if pois.empty:
        logger.warning("No POIs found for city='%s'.", city)
        return {
            "status": "ok",
            "cluster_id":    cluster_id,
            "cluster_label": cluster_label,
            "itinerary":     {},
            "num_days":      num_days,
            "time_spent_hours":     0.0,
            "predicted_total_cost": float(avg_hotel_per_night + avg_food_per_day) * num_days,
            "affordable":    False,
            "cost_breakdown": {
                "hotel": avg_hotel_per_night * num_days,
                "food":  avg_food_per_day * num_days,
                "pois":  0.0,
            },
        }

    # ── Route Planning ───────────────────────────────────────────────────
    day_routes = split_route_by_days(
        pois,
        num_days=num_days,
        max_daily_hours=config.MAX_DAILY_HOURS,
        avg_speed_kmh=config.DEFAULT_AVG_SPEED,
    )

    # ── Build Itinerary Dict ─────────────────────────────────────────────
    itinerary: dict[str, Any] = {}
    total_time = 0.0

    for day_num, (day_pois, time_spent) in enumerate(day_routes, start=1):
        if not day_pois:
            continue

        narrative = generate_itinerary_narrative(city, day_pois, user_prefs)

        itinerary[f"day{day_num}"] = {
            "narrative": narrative,
            "pois":      day_pois,
        }
        total_time += time_spent

    # ── Cost & Affordability ─────────────────────────────────────────────
    hotel_cost = avg_hotel_per_night * num_days
    food_cost  = avg_food_per_day * num_days
    poi_spend  = sum(
        p.get("avg_spend", 0)
        for day_data in itinerary.values()
        for p in day_data.get("pois", [])
    )
    total_cost = hotel_cost + food_cost + poi_spend
    affordable = total_cost <= budget

    logger.info(
        "Trip planned: %d days, %d POIs, cost=Rs.%.0f, affordable=%s",
        len(itinerary),
        sum(len(d["pois"]) for d in itinerary.values()),
        total_cost,
        affordable,
    )

    return {
        "status":               "ok",
        "cluster_id":           cluster_id,
        "cluster_label":        cluster_label,
        "itinerary":            itinerary,
        "num_days":             num_days,
        "time_spent_hours":     round(total_time, 2),
        "predicted_total_cost": round(total_cost, 2),
        "affordable":           affordable,
        "cost_breakdown": {
            "hotel": round(hotel_cost, 2),
            "food":  round(food_cost,  2),
            "pois":  round(poi_spend,  2),
        },
    }
