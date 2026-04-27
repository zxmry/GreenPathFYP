"""Centralized configuration for GreenPath application."""

import os

# ── Flask ────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "greenpath-secret-key-change-in-production-2024"
)

# ── File Paths ───────────────────────────────────────────────────
USERS_FILE = "users.json"
MODELS_DIR = "models"
LOGS_DIR = "logs"

# ── Vehicle Parameters (Malaysian fuel prices & efficiencies) ────
VEHICLE_FUEL_PARAMS = {
    "motorcycle": {"efficiency_l_per_100km": 4.0, "fuel_price_rm_per_l": 1.99},
    "car":        {"efficiency_l_per_100km": 8.0, "fuel_price_rm_per_l": 1.99},
    "van":        {"efficiency_l_per_100km": 12.0, "fuel_price_rm_per_l": 5.1},
    "truck":      {"efficiency_l_per_100km": 12.0, "fuel_price_rm_per_l": 5.1},
}

# ── Time / CO₂ Calculation Constants ─────────────────────────────
ROUTE_PARAMS = {
    "average_speed_kmh": 35,      # Realistic urban delivery speed
    "stop_time_minutes": 5,        # Average time per delivery stop
    "traffic_factor": 1.2,         # 20% time penalty for KL traffic
    "co2_per_km": 0.120,           # kg CO₂ per km (diesel delivery van)
}

# ── Genetic Algorithm Defaults ───────────────────────────────────
GA_DEFAULTS = {
    "pop_size": 100,
    "elite_size": 10,
    "mutation_rate": 0.01,
    "generations": 50,
}

# ── Geocoding ────────────────────────────────────────────────────
GEO_USER_AGENT = "greenpath_fyp_student_project"
GEO_TIMEOUT = 10

# ── OSRM ─────────────────────────────────────────────────────────
OSRM_BASE_URL = "http://router.project-osrm.org"
OSRM_TIMEOUT = 30

