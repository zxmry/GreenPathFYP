"""
Route History Service for GreenPath (FYP2).

Persists completed route optimisations to routes.json so users can
review past deliveries, track cumulative CO₂ savings and see fuel
cost trends over time.

Storage format (routes.json)
-----------------------------
{
  "<phone_number>": [
    {
      "id":               "uuid4 string",
      "timestamp":        "2025-06-01T14:32:00",
      "addresses":        ["addr1", "addr2", ...],
      "optimized_route":  ["addr1", "addr3", "addr2", ...],
      "vehicle_type":     "car",
      "metrics": {
        "original_distance_km":   44.4,
        "optimized_distance_km":  40.2,
        "distance_saved_km":      4.2,
        "time_saved_minutes":     8.6,
        "co2_saved_kg":           0.51,
        "fuel_cost_saved_rm":     1.20,
        "original_travel_minutes": 121.3,
        "optimized_travel_minutes": 112.7
      },
      "time_windows": [          # optional — only present if user set them
        {"address": "addr2", "earliest": "09:00", "latest": "11:00"},
        {"address": "addr3", "earliest": "14:00", "latest": "16:00"}
      ]
    },
    ...
  ]
}
"""

import json
import os
import uuid
from datetime import datetime

from config import ROUTES_FILE


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load():
    if os.path.exists(ROUTES_FILE):
        with open(ROUTES_FILE, "r") as f:
            return json.load(f)
    return {}


def _save(data):
    with open(ROUTES_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Public API ────────────────────────────────────────────────────────────────

def save_route(phone, addresses, optimized_route, vehicle_type, metrics, time_windows=None):
    """
    Persist a completed route optimisation for the given user.

    Parameters
    ----------
    phone          : str   — user's phone number (primary key in users.json)
    addresses      : list  — original address list as submitted by user
    optimized_route: list  — addresses in optimised delivery order
    vehicle_type   : str
    metrics        : dict  — from calculate_time_metrics / calculate_fuel_cost_metrics
    time_windows   : list  — [{address, earliest, latest}, ...] or None

    Returns
    -------
    str — the new route id
    """
    data = _load()
    if phone not in data:
        data[phone] = []

    route_id = str(uuid.uuid4())[:8]   # short 8-char id for display

    record = {
        "id":              route_id,
        "timestamp":       datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "addresses":       addresses,
        "optimized_route": optimized_route,
        "vehicle_type":    vehicle_type,
        "metrics": {
            "original_distance_km":    metrics.get("original_distance_km",    0),
            "optimized_distance_km":   metrics.get("optimized_distance_km",   0),
            "distance_saved_km":       metrics.get("distance_savings_km",     0),
            "time_saved_minutes":      metrics.get("time_saved_minutes",      0),
            "co2_saved_kg":            metrics.get("co2_saved_kg",            0),
            "fuel_cost_saved_rm":      metrics.get("fuel_cost_saved_rm",      0),
            "original_travel_minutes": metrics.get("original_travel_minutes", 0),
            "optimized_travel_minutes":metrics.get("optimized_travel_minutes",0),
        },
    }

    if time_windows:
        record["time_windows"] = time_windows

    # Keep max 50 routes per user (newest first)
    data[phone].insert(0, record)
    data[phone] = data[phone][:50]

    _save(data)
    return route_id


def get_user_routes(phone, limit=20):
    """
    Return the most recent `limit` routes for the given user.

    Returns
    -------
    list of route dicts (newest first), empty list if none.
    """
    data = _load()
    return data.get(phone, [])[:limit]


def get_cumulative_stats(phone):
    """
    Compute cumulative sustainability stats across all saved routes.

    Returns
    -------
    dict with total_routes, total_co2_saved_kg, total_fuel_saved_rm,
              total_distance_saved_km, total_time_saved_min
    """
    routes = get_user_routes(phone, limit=50)
    if not routes:
        return {
            "total_routes": 0,
            "total_co2_saved_kg": 0,
            "total_fuel_saved_rm": 0,
            "total_distance_saved_km": 0,
            "total_time_saved_min": 0,
        }

    return {
        "total_routes":            len(routes),
        "total_co2_saved_kg":      round(sum(r["metrics"]["co2_saved_kg"]       for r in routes), 2),
        "total_fuel_saved_rm":     round(sum(r["metrics"]["fuel_cost_saved_rm"] for r in routes), 2),
        "total_distance_saved_km": round(sum(r["metrics"]["distance_saved_km"]  for r in routes), 2),
        "total_time_saved_min":    round(sum(r["metrics"]["time_saved_minutes"] for r in routes), 1),
    }


def delete_route(phone, route_id):
    """Delete a specific route record for the user."""
    data = _load()
    if phone in data:
        data[phone] = [r for r in data[phone] if r["id"] != route_id]
        _save(data)
        return True
    return False