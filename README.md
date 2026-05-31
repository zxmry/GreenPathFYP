# 🌿 GreenPath — AI-Optimised Sustainable Last-Mile Delivery

A Flask-based web application for optimising last-mile delivery routes using a **Genetic Algorithm** (TSP solver). Built as a Final Year Project at the International Islamic University Malaysia (IIUM) for SME couriers and independent delivery operators in the Klang Valley region.

---

## 📁 Project Structure

```
GreenPathFYP/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── config.py                        # Centralised configuration
├── run.py                           # Flask entry point
├── migrate_to_sqlite.py             # One-time JSON → SQLite migration script
├── greenpath.db                     # SQLite database (auto-created on first run)
│
├── app/                             # Flask web application
│   ├── __init__.py                  # App factory — calls init_db() on startup
│   ├── auth.py                      # Login / signup / logout (SQLite-backed)
│   ├── api.py                       # All API endpoints
│   ├── database.py                  # SQLite connection helper + schema (init_db)
│   │
│   ├── core/                        # Business logic
│   │   ├── metrics.py               # Vehicle-aware time, CO₂ and fuel cost calculations
│   │   ├── routing.py               # Original route distance calculation
│   │   └── time_windows.py          # Stop time window validation and feasibility check
│   │
│   ├── graph/                       # Road network graph module
│   │   └── road_graph.py            # NetworkX graph construction and PNG visualisation
│   │
│   ├── services/                    # External API wrappers
│   │   ├── geo_service.py           # Geocoding (Nominatim) + OSRM distance matrix
│   │   ├── fuel_service.py          # Live Malaysian fuel prices from data.gov.my
│   │   └── history_service.py       # Route history save / retrieve / cumulative stats
│   │
│   └── solver/                      # Optimisation algorithms
│       └── genetic.py               # Genetic Algorithm TSP solver
│
├── rl/                              # Reinforcement Learning research package
│   ├── delivery_env.py              # Synthetic grid environment (kept for reference)
│   ├── real_delivery_env.py         # Real OSRM-based Gymnasium environment
│   └── train_real_dqn.py            # DQN training, evaluation and GA comparison
│
├── models/                          # Saved RL models and results
│   ├── env_config_real.json         # Serialised environment config
│   └── results_real.json            # Three-algorithm comparison results
│
├── static/                          # Frontend assets
│   ├── greenPath.css
│   └── greenPath.js
│
└── templates/                       # HTML templates
    ├── index.html                   # Main dashboard
    └── login.html                   # Login / signup page
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

RL training requires additional packages:

```bash
pip install stable-baselines3 gymnasium matplotlib networkx
```

### 2. Run the app

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

The SQLite database (`greenpath.db`) is created automatically on first run — no setup needed.

---

## 🗄️ Database

GreenPath uses **SQLite** for persistent storage. The database is managed entirely by `app/database.py` and is initialised automatically when the app starts.

### Schema

| Table | Purpose |
|-------|---------|
| `users` | Registered delivery operators (phone, name, password, vehicle) |
| `routes` | One row per completed optimisation run with all metrics |
| `route_addresses` | Original and optimised stop sequences (linked to routes) |
| `time_windows` | Per-stop arrival constraints (linked to routes) |

### Querying the database directly

```bash
# Open SQLite shell from the project root
sqlite3 greenpath.db

# See all tables
.tables

# See all users
SELECT * FROM users;

# See all routes with user names
SELECT r.id, u.name, r.vehicle_type, r.timestamp,
       r.dist_saved_km, r.co2_saved_kg, r.fuel_saved_rm
FROM routes r
JOIN users u ON r.phone = u.phone
ORDER BY r.timestamp DESC;

# Cumulative savings per user
SELECT u.name,
       COUNT(r.id)               AS total_routes,
       ROUND(SUM(r.co2_saved_kg),  2) AS total_co2_kg,
       ROUND(SUM(r.fuel_saved_rm),  2) AS total_fuel_rm
FROM users u
LEFT JOIN routes r ON u.phone = r.phone
GROUP BY u.phone;

# Exit
.quit
```

For a visual interface, use [DB Browser for SQLite](https://sqlitebrowser.org) (free).

### Migrating from legacy JSON stores

If you have existing `users.json` or `routes.json` data from a previous version:

```bash
python migrate_to_sqlite.py
```

This is a one-time operation. After verifying the data in `greenpath.db`, the JSON files can be deleted.

---

## 🧬 How the System Works

### Main optimisation pipeline (`POST /api/process-route`)

1. **Geocoding** — Addresses converted to coordinates via Nominatim (OpenStreetMap).
2. **Distance matrix** — Real road distances fetched from OSRM for all stop pairs.
3. **Baseline route** — Unoptimised distance calculated in the user's input order.
4. **Genetic Algorithm** — Stop sequence optimised using ordered crossover (OX1), swap mutation and elitism over 50 generations with a population of 100.
5. **Vehicle-aware metrics** — Time, CO₂ and fuel cost calculated using parameters for the user's registered vehicle type.
6. **Live fuel prices** — Fuel costs use the current week's RON95/RON97/Diesel prices from data.gov.my.
7. **Road network graph** — Delivery stops modelled as a weighted directed graph using NetworkX and returned as a PNG visualisation.
8. **Time window check** — If per-stop arrival windows are set, the system simulates the route and reports on-time, early or violated status per stop.
9. **Route history** — The completed optimisation is saved to `greenpath.db` under the user's account for cumulative tracking.
10. **Visualisation** — Original and optimised routes rendered on an interactive Leaflet.js map.

---

## 🚗 Vehicle Parameters

| Parameter | Motorcycle | Car | Van |
|-----------|-----------|-----|-----|
| Speed (km/h) | 45 | 35 | 28 |
| Traffic factor | 1.05 | 1.20 | 1.35 |
| Stop time (min) | 3 | 5 | 8 |
| CO₂ rate (kg/km) | 0.06 | 0.21 | 0.35 |
| Fuel (L/100km) | 4.0 | 8.0 | 12.0 |
| Fuel type | RON95 | RON95 | Diesel |

---

## 🤖 Reinforcement Learning Research

The RL component is an **empirical research investigation**, not the production optimiser. The GA handles all production routing.

### Environment

`RealDeliveryEnv` is a Gymnasium-compatible environment built from a real OSRM distance matrix. State space includes current position, visited stop flags, distances to all unvisited stops and a simulated time-of-day traffic multiplier.

### Run RL training

```bash
python -m rl.train_real_dqn
```

Custom addresses:

```bash
python -m rl.train_real_dqn \
  --addresses "KLCC, Kuala Lumpur" "Bangsar, KL" "Shah Alam, Selangor" \
  --vehicle car \
  --timesteps 300000
```

Evaluate a saved model without retraining:

```bash
python -m rl.train_real_dqn --eval-only
```

Results saved to `models/` and `logs/`. Training curve saved to `training_curve_real.png`.

### Key finding

| Agent | Avg. distance |
|-------|--------------|
| Genetic Algorithm | 68.32 km |
| Random baseline | 89.66 km |
| DQN agent | 95.93 km |

The DQN underperformed the random agent on route distance despite clear reward improvement during training. This is expected: DQN is designed for dynamic uncertain environments, not static small-scale TSP. The GA outperforms DQN because evolutionary search is purpose-built for combinatorial optimisation over a fixed distance matrix.

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/process-route` | Main optimisation endpoint |
| `GET` | `/api/fuel-prices` | Latest Malaysian fuel prices |
| `GET` | `/api/route-history` | User's route history + cumulative stats |
| `DELETE` | `/api/route-history/<id>` | Delete a route record |

### `/api/process-route` request body

```json
{
  "addresses": ["KLCC, KL", "Bangsar, KL", "Shah Alam, Selangor"],
  "departure_time": "08:00",
  "time_windows": [
    { "address": "Bangsar, KL", "earliest": "09:00", "latest": "11:00" }
  ]
}
```

`time_windows` is optional. Leave `earliest` or `latest` as `null` for one-sided constraints.

---

## ⚙️ Configuration (`config.py`)

| Setting | Description |
|---------|-------------|
| `SECRET_KEY` | Flask session secret — change before deploying |
| `DB_PATH` | Path to SQLite database file (default: `greenpath.db` in project root) |
| `VEHICLE_PARAMS` | All vehicle-specific parameters in one table |
| `GA_DEFAULTS` | Population size, generations, mutation rate, elite size |
| `OSRM_BASE_URL` | OSRM server URL (defaults to public demo server) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask (Python 3) |
| Database | SQLite (via Python `sqlite3` — no extra dependencies) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Maps | Leaflet.js + OpenStreetMap tiles |
| Charts | Chart.js |
| Geocoding | Nominatim (OpenStreetMap) |
| Routing distances | OSRM (Open Source Routing Machine) |
| Route optimisation | Custom Genetic Algorithm |
| Graph modelling | NetworkX |
| RL training | Stable-Baselines3 (DQN) |
| Fuel prices | data.gov.my open data API |

---

## 👥 Project Team

| Name | Student ID | Role |
|------|-----------|------|
| Muhammad Zamri bin Suhaimi | 2213125 | Frontend, GA, documentation |
| Nabil Amri bin Mohd Redzuan | 2212011 | Backend, Flask, OSRM, Genetic Algorithm, RL Research |

**Supervisor:** Asst. Prof. Dr. Raini binti Hassan
**Institution:** Kulliyyah of Information and Communication Technology, IIUM
**Project ID:** 1622 D

---

## 📄 License

Academic FYP project — for research and educational use only.
