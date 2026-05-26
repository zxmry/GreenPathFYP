"""Centralised configuration for GreenPath application."""

import os

# ── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "greenpath-secret-key-change-in-production-2024"
)

# ── File Paths ───────────────────────────────────────────────────────────────
USERS_FILE    = "users.json"
ROUTES_FILE   = "routes.json"      # FYP2: route history storage
MODELS_DIR    = "models"
LOGS_DIR      = "logs"

# ── Vehicle Parameters (FYP2: unified, vehicle-aware) ────────────────────────
#
# Each vehicle type now has its own:
#   • average_speed_kmh   — realistic urban delivery speed in KL
#   • traffic_factor      — congestion penalty (motorcycles lane-split → lower)
#   • stop_time_minutes   — avg time per delivery stop
#   • co2_per_km          — kg CO₂ emitted per km (IPCC / MoT Malaysia values)
#   • efficiency_l_per_100km — fuel consumption
#   • fuel_type           — which live price to use (ron95 / diesel)
#
VEHICLE_PARAMS = {
    "motorcycle": {
        "average_speed_kmh":      45,      # faster — can lane-split in KL
        "traffic_factor":         1.05,    # minimal congestion penalty
        "stop_time_minutes":      3,       # quicker stops (no loading)
        "co2_per_km":             0.06,    # kg CO₂/km — small engine
        "efficiency_l_per_100km": 4.0,     # L/100km
        "fuel_type":              "ron95",
    },
    "car": {
        "average_speed_kmh":      35,      # standard KL urban speed
        "traffic_factor":         1.20,    # 20% congestion penalty
        "stop_time_minutes":      5,
        "co2_per_km":             0.21,    # kg CO₂/km — petrol sedan
        "efficiency_l_per_100km": 8.0,
        "fuel_type":              "ron95",
    },
    "van": {
        "average_speed_kmh":      28,      # slower — heavier, restricted lanes
        "traffic_factor":         1.35,    # higher congestion penalty
        "stop_time_minutes":      8,       # loading/unloading takes longer
        "co2_per_km":             0.35,    # kg CO₂/km — diesel van
        "efficiency_l_per_100km": 12.0,
        "fuel_type":              "diesel",
    },
}

# Keep old name as alias so any code still referencing VEHICLE_FUEL_PARAMS works
VEHICLE_FUEL_PARAMS = {
    k: {"efficiency_l_per_100km": v["efficiency_l_per_100km"],
        "fuel_price_rm_per_l":   1.99}
    for k, v in VEHICLE_PARAMS.items()
}

# ── Legacy ROUTE_PARAMS (kept for backward compat — metrics.py no longer uses)
ROUTE_PARAMS = {
    "average_speed_kmh":  35,
    "stop_time_minutes":  5,
    "traffic_factor":     1.2,
    "co2_per_km":         0.21,
}

# ── Genetic Algorithm Defaults ───────────────────────────────────────────────
GA_DEFAULTS = {
    "pop_size":     100,
    "elite_size":   10,
    "mutation_rate": 0.01,
    "generations":  50,
}

# ── Geocoding ────────────────────────────────────────────────────────────────
GEO_USER_AGENT = "greenpath_fyp_student_project"
GEO_TIMEOUT    = 10

# ── OSRM ─────────────────────────────────────────────────────────────────────
OSRM_BASE_URL = "http://router.project-osrm.org"
OSRM_TIMEOUT  = 30