# 🌿 GreenPath — AI-Optimised Sustainable Last-Mile Delivery

A Flask-based web application for optimising last-mile delivery routes using a **Genetic Algorithm** (TSP solver). Built as a Final Year Project at the International Islamic University Malaysia (IIUM) for small and medium enterprise (SME) couriers and independent delivery operators in the Klang Valley region.

FYP2 extends the FYP1 baseline with five major system enhancements and an empirical Reinforcement Learning research investigation.

---

## 📁 Project Structure

```
GreenPathFYP/
├── README.md                        # This file
├── requirements.txt                 # Python dependencies
├── config.py                        # Centralised configuration (VEHICLE_PARAMS, GA_DEFAULTS)
├── run.py                           # Flask entry point
├── users.json                       # User accounts (auto-created on first signup)
├── routes.json                      # Route history store (auto-created on first optimisation)
│
├── app/                             # Flask web application
│   ├── __init__.py                  # App factory
│   ├── auth.py                      # Login / signup / logout
│   ├── api.py                       # All API endpoints
│   │
│   ├── core/                        # Business logic
│   │   ├── metrics.py               # Vehicle-aware time, CO₂ and fuel cost calculations
│   │   ├── routing.py               # Original route distance calculation
│   │   └── time_windows.py          # Stop time window validation and feasibility check
│   │
│   ├── graph/                       # Road network graph module (FYP2)
│   │   ├── __init__.py
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
│   ├── delivery_env.py              # Original synthetic grid environment (FYP1, kept for reference)
│   ├── real_delivery_env.py         # Real OSRM-based environment (FYP2)
│   └── train_real_dqn.py            # DQN training, evaluation and GA comparison
│
├── models/                          # Saved RL models and results
│   ├── dqn_real_final.zip           # Trained DQN model
│   ├── env_config_real.json         # Serialised environment config
│   └── results_real.json            # Three-algorithm comparison results
│
├── static/                          # Frontend assets
│   ├── greenPath.css
│   └── greenPath.js
│
├── templates/                       # HTML templates
│   ├── index.html                   # Main dashboard
│   └── login.html                   # Login / signup page
│
└── logs/                            # RL training logs
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

RL training requires additional packages:

```bash
pip install stable-baselines3 gymnasium matplotlib networkx
```

### 2. Run the Flask App

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. Register an account, select your vehicle type and start optimising routes.

---

## 🧬 How the System Works

### Main Optimisation Pipeline (`/api/process-route`)

1. **Geocoding** — User-entered addresses are converted to coordinates via Nominatim (OpenStreetMap).
2. **Distance Matrix** — Real road distances between all stops are fetched from OSRM.
3. **Original Route** — The unoptimised distance (user's input order) is calculated as a baseline.
4. **Genetic Algorithm** — The stop sequence is optimised to minimise total travel distance using a custom GA with ordered crossover, swap mutation and elitism.
5. **Vehicle-Aware Metrics** — Time, CO₂ emissions and fuel cost are calculated using parameters specific to the user's registered vehicle type (motorcycle, car or van).
6. **Live Fuel Prices** — Fuel cost calculations use the current week's RON95/RON97/Diesel prices fetched from data.gov.my.
7. **Road Network Graph** — The delivery stops are modelled as a weighted directed graph and rendered as a PNG visualisation embedded in the response.
8. **Time Window Check** — If the user set earliest/latest arrival times per stop, the system simulates the route and reports feasibility.
9. **Route History** — The completed optimisation is saved to `routes.json` under the user's account for cumulative tracking.
10. **Visualisation** — Original and optimised routes are rendered on an interactive Leaflet.js map with metrics displayed on the dashboard.

---

## 🆕 FYP2 Enhancements

| Feature | Description |
|---------|-------------|
| **Vehicle-aware metrics** | Speed, traffic factor, stop time, CO₂ rate and fuel efficiency now differ per vehicle. Motorcycle: 45 km/h, 0.06 kg CO₂/km. Car: 35 km/h, 0.21 kg CO₂/km. Van: 28 km/h, 0.35 kg CO₂/km. |
| **Live fuel prices** | Weekly RON95, RON97 and Diesel prices from data.gov.my API. Van users billed at Diesel rate; motorcycle and car at RON95. Falls back to defaults if API is unavailable. |
| **Road network graph** | Delivery stops modelled as a weighted directed graph using NetworkX. Graph stats (density, connectivity, edge weights) and a PNG visualisation returned with every optimisation. Serves as the GNN input layer for future work. |
| **Stop time windows** | Users set optional earliest/latest arrival times per stop. System simulates the route from departure time and reports on-time, early-wait or violated status per stop. |
| **Route history** | Every completed optimisation saved to `routes.json` per user. `GET /api/route-history` returns full history and cumulative CO₂ / fuel cost savings. |

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

FYP2 includes an empirical investigation into DQN-based route optimisation. The RL component is a **research contribution**, not the production optimiser (the GA handles production routing).

### What was built

- `RealDeliveryEnv` — a Gymnasium environment built from a real OSRM distance matrix replacing the synthetic grid from FYP1. State space includes current position, visited flags, distances to all stops and a time-of-day traffic multiplier.
- `train_real_dqn.py` — trains a DQN agent and compares it against a random baseline and the GA on the same problem instance.

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

Outputs saved to `models/` and `logs/`. Training curve saved to `training_curve_real.png`.

### Key finding

The DQN agent (95.93 km average) underperformed both the random agent (89.66 km) and the GA (68.32 km) on route distance despite showing clear reward improvement during training. This is expected: DQN is designed for dynamic uncertain environments, not static small-scale TSP. The GA outperforms DQN on this class of problem because evolutionary search is purpose-built for combinatorial optimisation over a fixed distance matrix. See the FYP2 report Chapter 6 for the full analysis.

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
| `VEHICLE_PARAMS` | All vehicle-specific parameters in one table |
| `GA_DEFAULTS` | Population size, generations, mutation rate, elite size |
| `OSRM_BASE_URL` | OSRM server URL (defaults to public demo server) |
| `ROUTES_FILE` | Path to route history JSON store |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Flask (Python 3) |
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
| Muhammad Zamri bin Suhaimi | 2213125 | Frontend, Chapter 1, Conceptual Review, GA research |
| Nabil Amri bin Mohd Redzuan | 2212011 | Backend, Flask, OSRM, Genetic Algorithm, RL |

**Supervisor:** Asst. Prof. Dr. Raini binti Hassan
**Institution:** Kulliyyah of Information and Communication Technology, IIUM
**Project ID:** 1622 D

---

## 📄 License

Academic FYP project — for research and educational use only.