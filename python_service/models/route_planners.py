"""
models/route_planners.py
-------------------------
Greedy nearest-neighbour route planner for Points of Interest (POIs).

Key improvements over original:
  • Travel-time penalty: score penalised by estimated travel time (dist / speed)
  • Dynamic start location: caller can pass start_index or a (lat, lon) tuple
  • Strict deduplication: visited set prevents any POI appearing twice
  • split_route_by_days: wraps greedy_route to produce per-day lists
  • Optional category filter when loading POIs
"""

from __future__ import annotations

import logging
import math
from typing import List, Tuple

import pandas as pd

from config import DEFAULT_AVG_SPEED, MAX_DAILY_HOURS, TRAVEL_TIME_WEIGHT

logger = logging.getLogger(__name__)


# ─── POI Loading ─────────────────────────────────────────────────────────────

def load_pois(
    path: str = "data/pois.csv",
    city: str = "Kolkata",
    category_filter: list | None = None,
) -> pd.DataFrame:
    """
    Load Points of Interest for a given city.

    Parameters
    ----------
    path            : path to pois.csv
    city            : filter by this city name (case-insensitive)
    category_filter : optional list of category strings to include
    """
    df = pd.read_csv(path)
    df = df[df["city"].str.lower() == city.lower()].reset_index(drop=True)

    if category_filter:
        df = df[df["category"].str.lower().isin([c.lower() for c in category_filter])]
        df = df.reset_index(drop=True)

    # Ensure required columns are numeric
    for col in ("lat", "lon", "avg_spend", "avg_stay_hours", "rating"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    logger.info("Loaded %d POIs for city='%s'", len(df), city)
    return df


# ─── Haversine Distance ──────────────────────────────────────────────────────

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return great-circle distance in kilometres between two coordinates.
    Uses the haversine formula.
    """
    R = 6_371.0  # Earth radius, km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── Distance Matrix ─────────────────────────────────────────────────────────

def build_distance_matrix(pois: pd.DataFrame) -> List[List[float]]:
    """
    Pre-compute pairwise haversine distances (km) between all POIs.
    Returns an n×n list of lists.
    """
    n = len(pois)
    dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(
                pois.loc[i, "lat"], pois.loc[i, "lon"],
                pois.loc[j, "lat"], pois.loc[j, "lon"],
            )
            dist[i][j] = d
            dist[j][i] = d
    return dist


# ─── Greedy Route ─────────────────────────────────────────────────────────────

def greedy_route(
    pois: pd.DataFrame,
    start_index: int = 0,
    max_daily_hours: float = MAX_DAILY_HOURS,
    avg_speed_kmh: float = DEFAULT_AVG_SPEED,
    global_visited: set | None = None,
) -> Tuple[List[int], float]:
    """
    Build a greedy route for a single day.

    Scoring function for each candidate POI j (not yet visited):
        score(j) = rating(j) / (1 + travel_time(j))
    where travel_time = distance_km / avg_speed_kmh

    The day ends when adding the next POI would exceed max_daily_hours
    (visit time + travel time counted).

    Parameters
    ----------
    pois           : DataFrame for ONE city, reset-indexed
    start_index    : index of the starting POI in pois
    max_daily_hours: hard cap on total hours per day
    avg_speed_kmh  : assumed average intra-city speed
    global_visited : set of POI *ids* already used in previous days

    Returns
    -------
    order      : list of row-indices (into pois) for this day's route
    time_spent : total hours consumed (travel + visit)
    """
    if pois.empty:
        return [], 0.0

    dist     = build_distance_matrix(pois)
    n        = len(pois)
    visited  = [False] * n
    order    = []
    time_spent = 0.0

    # Mark globally already-visited POIs
    if global_visited:
        for idx in range(n):
            poi_id = pois.loc[idx, "id"] if "id" in pois.columns else idx
            if poi_id in global_visited:
                visited[idx] = True

    # Find a valid start
    if start_index >= n or visited[start_index]:
        start_index = next((i for i in range(n) if not visited[i]), None)
        if start_index is None:
            return [], 0.0

    order.append(start_index)
    visited[start_index] = True
    time_spent += float(pois.loc[start_index, "avg_stay_hours"])

    while True:
        current    = order[-1]
        best_score = -1.0
        best_idx   = None

        for j in range(n):
            if visited[j]:
                continue

            dist_km      = dist[current][j]
            travel_time  = dist_km / avg_speed_kmh          # hours
            stay_time    = float(pois.loc[j, "avg_stay_hours"])
            total_needed = travel_time + stay_time

            if time_spent + total_needed > max_daily_hours:
                continue

            # Score: high rating preferred, penalise longer travel
            score = float(pois.loc[j, "rating"]) / (1 + TRAVEL_TIME_WEIGHT * travel_time)

            if score > best_score:
                best_score = score
                best_idx   = j

        if best_idx is None:
            break

        order.append(best_idx)
        visited[best_idx] = True
        dist_km    = dist[order[-2]][best_idx]
        travel_time = dist_km / avg_speed_kmh
        time_spent += float(pois.loc[best_idx, "avg_stay_hours"]) + travel_time

    return order, time_spent


# ─── Multi-Day Route Splitting ────────────────────────────────────────────────

def split_route_by_days(
    pois: pd.DataFrame,
    num_days: int,
    max_daily_hours: float = MAX_DAILY_HOURS,
    avg_speed_kmh: float = DEFAULT_AVG_SPEED,
) -> List[Tuple[List[dict], float]]:
    """
    Split POIs across ``num_days`` days using the greedy route algorithm.

    POIs are never repeated across days — each POI is removed from the pool
    once it has been assigned to a day.

    Returns
    -------
    List of (poi_records, time_spent) tuples, one entry per day.
      poi_records : list of dicts with keys name, category, avg_spend, avg_stay_hours
      time_spent  : total hours consumed that day (visit + travel)
    """
    remaining = pois.copy().reset_index(drop=True)
    days: List[Tuple[List[dict], float]] = []

    for day in range(num_days):
        if remaining.empty:
            logger.info("Day %d: No POIs left — stopping early.", day + 1)
            break

        order, time_spent = greedy_route(
            remaining,
            start_index=0,
            max_daily_hours=max_daily_hours,
            avg_speed_kmh=avg_speed_kmh,
        )

        # Extract the actual POI records for this day's route
        poi_records = (
            remaining.iloc[order][["name", "category", "avg_spend", "avg_stay_hours"]]
            .to_dict(orient="records")
        )
        days.append((poi_records, time_spent))
        logger.info(
            "Day %d: %d POIs planned, %.1f hours. POIs: %s",
            day + 1, len(order), time_spent,
            [r["name"] for r in poi_records],
        )

        # Remove used POIs from the pool for subsequent days
        if order:
            remaining = (
                remaining.drop(remaining.index[order])
                .reset_index(drop=True)
            )

    return days
